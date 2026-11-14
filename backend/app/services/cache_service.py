"""Small JSON file cache for slow upstream NASA requests.

Files live in backend/data/cache/api/, which is ignored by git.
Delete that folder to force everything to be fetched again.
"""
import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
CACHE_DIR = BASE_DIR / "data" / "cache" / "api"


def _path(key: str) -> Path:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
    return CACHE_DIR / f"{digest}.json"


def cache_get(key: str, max_age_seconds: float | None = None) -> Any | None:
    """Return the cached value, or None when missing, expired or unreadable."""
    path = _path(key)

    try:
        with path.open("r", encoding="utf-8") as handle:
            entry = json.load(handle)
    except (OSError, ValueError):
        return None

    if not isinstance(entry, dict) or entry.get("key") != key:
        return None

    if max_age_seconds is not None:
        saved_at = entry.get("saved_at")

        if (
            not isinstance(saved_at, (int, float))
            or time.time() - saved_at > max_age_seconds
        ):
            return None

    return entry.get("value")


def cache_set(key: str, value: Any) -> None:
    """Store a JSON-serialisable value. Failures are logged, never raised."""
    path = _path(key)

    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")

        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(
                {"key": key, "saved_at": time.time(), "value": value},
                handle
            )

        temporary.replace(path)
    except (OSError, TypeError, ValueError):
        logger.warning("Unable to write cache entry", exc_info=True)
