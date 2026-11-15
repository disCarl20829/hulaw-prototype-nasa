"""Two-tier cache for slow upstream NASA requests.

1. Memory: small values (overview results, map series, MODIS blocks) are
   kept as JSON text in a bounded LRU, so a warm request never touches disk.
2. Disk: every value is also written as a JSON file, so it survives a
   process restart for as long as the folder survives.

The folder defaults to backend/data/cache/api/ (ignored by git). On a host
with an ephemeral filesystem (Render without a disk), set HULAW_CACHE_DIR to
a mounted persistent disk, otherwise the cache is lost on every restart.
Delete the folder to force everything to be fetched again.

single_flight() makes concurrent identical requests share one upstream call.
"""
import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from collections import OrderedDict
from pathlib import Path
from typing import Any, Awaitable, Callable

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = Path(
    os.getenv("HULAW_CACHE_DIR") or BASE_DIR / "data" / "cache" / "api"
)

MEMORY_MAX_ENTRIES = 512
# Larger values (20 years of raw daily POWER data) stay on disk only, so the
# memory tier cannot outgrow a small instance.
MEMORY_MAX_CHARS = 100_000

# (cache dir, key) -> (saved_at, JSON text of the value)
_memory: "OrderedDict[tuple[str, str], tuple[float, str]]" = OrderedDict()
_inflight: dict[str, asyncio.Future] = {}


def _path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return CACHE_DIR / f"{digest}.json"


def _remember(key: str, saved_at: float, text: str) -> None:
    if len(text) > MEMORY_MAX_CHARS:
        return

    slot = (str(CACHE_DIR), key)
    _memory[slot] = (saved_at, text)
    _memory.move_to_end(slot)

    while len(_memory) > MEMORY_MAX_ENTRIES:
        _memory.popitem(last=False)


def _fresh(saved_at: Any, max_age_seconds: float | None) -> bool:
    if max_age_seconds is None:
        return True

    return (
        isinstance(saved_at, (int, float))
        and time.time() - saved_at <= max_age_seconds
    )


def cache_get(key: str, max_age_seconds: float | None = None) -> Any | None:
    """Return the cached value, or None when missing, expired or unreadable.

    Every call returns its own copy, so callers may modify the result.
    """
    slot = (str(CACHE_DIR), key)
    hit = _memory.get(slot)

    if hit is not None:
        if _fresh(hit[0], max_age_seconds):
            _memory.move_to_end(slot)
            return json.loads(hit[1])

        return None  # the file cannot be newer than the memory copy

    path = _path(key)

    try:
        with path.open("r", encoding="utf-8") as handle:
            entry = json.load(handle)
    except (OSError, ValueError):
        return None

    if not isinstance(entry, dict) or entry.get("key") != key:
        return None

    saved_at = entry.get("saved_at")

    if not _fresh(saved_at, max_age_seconds):
        return None

    value = entry.get("value")

    try:
        if isinstance(saved_at, (int, float)) and (
            path.stat().st_size <= MEMORY_MAX_CHARS
        ):
            _remember(key, saved_at, json.dumps(value))
    except (OSError, TypeError, ValueError):
        pass

    return value


def cache_set(key: str, value: Any) -> None:
    """Store a JSON-serialisable value. Failures are logged, never raised."""
    saved_at = time.time()

    try:
        text = json.dumps(value)
    except (TypeError, ValueError):
        logger.warning("Unable to serialise cache entry", exc_info=True)
        return

    _remember(key, saved_at, text)
    path = _path(key)
    # Unique name: two writers of the same key must not share a temp file.
    temporary = path.with_name(f"{path.stem}.{uuid.uuid4().hex}.tmp")

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(
                f'{{"key": {json.dumps(key)}, "saved_at": {saved_at!r}, '
                f'"value": {text}}}'
            )

        temporary.replace(path)
    except OSError:
        logger.warning("Unable to write cache entry", exc_info=True)

        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def cache_prune(max_age_seconds: float = 90 * 24 * 3600) -> int:
    """Delete cache files not written for max_age_seconds, and temporary
    files left behind by an interrupted write. Returns how many were removed.
    Called once at start-up so the folder cannot grow without limit."""
    removed = 0
    now = time.time()

    try:
        files = list(CACHE_DIR.iterdir())
    except OSError:
        return 0

    for path in files:
        try:
            age = now - path.stat().st_mtime
            stale_temp = path.suffix == ".tmp" and age > 3600

            if path.suffix == ".json" and age > max_age_seconds or stale_temp:
                path.unlink()
                removed += 1
        except OSError:
            continue

    return removed


async def single_flight(key: str, factory: Callable[[], Awaitable[Any]]) -> Any:
    """Run factory() once for all concurrent callers that use the same key.

    The work continues even if the caller that started it goes away, so the
    result still reaches the cache. Callers share one result object and must
    not modify it.
    """
    task = _inflight.get(key)

    if task is None or task.get_loop() is not asyncio.get_running_loop():
        task = asyncio.ensure_future(factory())
        _inflight[key] = task

        def _done(finished: asyncio.Future, key: str = key) -> None:
            if _inflight.get(key) is finished:
                del _inflight[key]

            if not finished.cancelled():
                finished.exception()  # mark as retrieved; waiters re-raise it

        task.add_done_callback(_done)

    return await asyncio.shield(task)
