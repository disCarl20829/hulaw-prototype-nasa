
"""NASA POWER daily point data with persistent caching and timing logs."""
import logging
import time

import httpx
from fastapi import HTTPException

from app.services.cache_service import cache_get, cache_set, single_flight
from app.services.http_client import get_client
from app.services.nasa_service import NASA_POWER_URL

logger = logging.getLogger(__name__)

POWER_CACHE_TTL = 30 * 24 * 60 * 60  # 30 days


async def get_power_daily(
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    parameters: list[str]
) -> dict[str, dict[str, float | None]]:
    """Return {parameter: {YYYYMMDD: value or None}}.

    NASA POWER marks missing days with a negative sentinel (-999).
    Those days are returned as None, never as zero.
    """

    cache_key = (
        f"power-daily:v1:{latitude:.4f}:{longitude:.4f}:"
        f"{start}:{end}:{','.join(sorted(parameters))}"
    )

    cached = cache_get(cache_key, POWER_CACHE_TTL)

    if cached is not None:
        logger.info(
            "POWER cache HIT: %s to %s, %s",
            start, end, parameters
        )
        return cached

    logger.info(
        "POWER cache MISS: %s to %s, %s",
        start, end, parameters
    )

    # Concurrent requests for the same point share one NASA call.
    return await single_flight(
        cache_key,
        lambda: _fetch_power_daily(
            cache_key, latitude, longitude, start, end, parameters
        ),
    )


async def _fetch_power_daily(
    cache_key: str,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    parameters: list[str]
) -> dict[str, dict[str, float | None]]:
    params = {
        "parameters": ",".join(parameters),
        "community": "AG",
        "latitude": latitude,
        "longitude": longitude,
        "start": start,
        "end": end,
        "format": "JSON",
        "time-standard": "UTC"
    }

    started = time.perf_counter()

    try:
        response = await get_client().get(
            NASA_POWER_URL, params=params, timeout=120.0
        )
        response.raise_for_status()
        data = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"NASA POWER returned HTTP {exc.response.status_code}"
        ) from exc

    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve valid NASA POWER data"
        ) from exc

    elapsed = time.perf_counter() - started

    logger.info(
        "POWER API completed in %.2f seconds (%s to %s)",
        elapsed, start, end
    )

    try:
        block = data["properties"]["parameter"]
    except (KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="NASA POWER response has an unexpected format"
        ) from exc

    result: dict[str, dict[str, float | None]] = {}

    for name in parameters:
        values = block.get(name) if isinstance(block, dict) else None

        if not isinstance(values, dict):
            raise HTTPException(
                status_code=502,
                detail=f"NASA POWER response does not contain {name}"
            )

        result[name] = {
            day: (
                value
                if isinstance(value, (int, float))
                and not isinstance(value, bool)
                and value >= 0
                else None
            )
            for day, value in values.items()
        }

    cache_set(cache_key, result)

    return result
