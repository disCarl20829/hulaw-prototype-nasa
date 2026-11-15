"""Download SMAP files from NASA on demand, in the background.

One SPL3SMP_E daily file is about 650 MB, so a request never waits for it.
The first request for a date queues the download and is answered with
status "pending"; the caller asks again later. When a file arrives, the
value for every point that asked for it is extracted and cached, so the
answer survives after the file is deleted to make room for the next one.

Off unless all three variables are set on the host:
    HULAW_SMAP_ON_DEMAND=1
    EARTHDATA_USERNAME, EARTHDATA_PASSWORD   (NASA Earthdata login)

Optional:
    HULAW_SMAP_MAX_FILES   files kept on disk (default 2, about 1.3 GB)
    HULAW_SMAP_MAX_QUEUE   dates waiting at once (default 7)
"""
import logging
import os
import threading
import time
from collections import deque
from datetime import date

logger = logging.getLogger(__name__)

PRODUCT = "SPL3SMP_E"
VERSION = "006"
FAILED_RETRY_SECONDS = 15 * 60

_lock = threading.Lock()
_queue: deque[date] = deque()
# date -> {"state", "points": set[(lat, lon)], "error", "at"}
_jobs: dict[date, dict] = {}
_worker: threading.Thread | None = None


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes"}


def _number(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, "")))
    except ValueError:
        return default


def enabled() -> bool:
    return bool(
        _flag("HULAW_SMAP_ON_DEMAND")
        and os.getenv("EARTHDATA_USERNAME")
        and os.getenv("EARTHDATA_PASSWORD")
    )


def request_file(observation_date: date, latitude: float, longitude: float) -> dict:
    """Make sure a download for this date is queued or running.

    Returns {"state": ..., "error": ...} where state is one of
    disabled, queued, downloading, unavailable, failed, busy.
    """
    global _worker

    if not enabled():
        return {"state": "disabled", "error": None}

    with _lock:
        job = _jobs.get(observation_date)

        if job is not None:
            retry = (
                job["state"] == "failed"
                and time.time() - job["at"] > FAILED_RETRY_SECONDS
            )

            if not retry:
                job["points"].add((latitude, longitude))
                return {"state": job["state"], "error": job["error"]}

        waiting = sum(
            1 for item in _jobs.values()
            if item["state"] in {"queued", "downloading"}
        )

        if waiting >= _number("HULAW_SMAP_MAX_QUEUE", 7):
            return {"state": "busy", "error": None}

        _jobs[observation_date] = {
            "state": "queued",
            "points": {(latitude, longitude)},
            "error": None,
            "at": time.time(),
        }
        _queue.append(observation_date)

        if _worker is None or not _worker.is_alive():
            _worker = threading.Thread(
                target=_run, name="smap-download", daemon=True
            )
            _worker.start()

    return {"state": "queued", "error": None}


def _finish(observation_date: date, state: str, error: str | None = None) -> set:
    with _lock:
        job = _jobs[observation_date]
        job.update(state=state, error=error, at=time.time())
        points = set(job["points"])

        # A finished download needs no record: the file or the cached
        # values answer the next request.
        if state == "done":
            del _jobs[observation_date]

    return points


def _run() -> None:
    while True:
        with _lock:
            if not _queue:
                return

            observation_date = _queue.popleft()
            _jobs[observation_date]["state"] = "downloading"

        try:
            state, error = _download(observation_date)
        except Exception as exc:  # a failed download must not kill the queue
            logger.exception("SMAP download failed for %s", observation_date)
            state, error = "failed", type(exc).__name__

        if state != "done":
            _finish(observation_date, state, error)
            continue

        # Extract for everyone who asked while the file was on its way.
        from app.services.smap_service import extract_soil_moisture

        with _lock:
            points = set(_jobs[observation_date]["points"])

        for latitude, longitude in points:
            try:
                extract_soil_moisture(latitude, longitude, observation_date)
            except Exception:
                logger.exception("SMAP extraction failed after download")

        _finish(observation_date, "done")


def _make_room(directory, keep: int) -> None:
    """Delete the oldest downloaded files so at most `keep` remain after
    the next download, and clear leftovers of interrupted downloads."""
    files = sorted(directory.glob("*.h5"), key=lambda p: p.stat().st_mtime)

    for path in files[:max(0, len(files) - (keep - 1))]:
        path.unlink(missing_ok=True)

    for path in directory.glob("partial_*"):
        path.unlink(missing_ok=True)


def _download(observation_date: date) -> tuple[str, str | None]:
    import earthaccess

    from app.services.smap_service import SMAP_DIR, find_smap_file

    started = time.perf_counter()
    auth = earthaccess.login(strategy="environment")

    if not getattr(auth, "authenticated", False):
        return "failed", "NASA Earthdata login was rejected"

    day = observation_date.isoformat()
    results = earthaccess.search_data(
        short_name=PRODUCT, version=VERSION, temporal=(day, day), count=1
    )

    if not results:
        return "unavailable", None

    SMAP_DIR.mkdir(parents=True, exist_ok=True)
    _make_room(SMAP_DIR, _number("HULAW_SMAP_MAX_FILES", 2))
    earthaccess.download(results, local_path=str(SMAP_DIR))

    if find_smap_file(observation_date) is None:
        return "failed", "the downloaded file is not for the requested date"

    logger.info(
        "SMAP %s downloaded in %.0f seconds",
        day, time.perf_counter() - started
    )

    return "done", None
