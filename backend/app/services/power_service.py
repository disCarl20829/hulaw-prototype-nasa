"""NASA POWER daily point data for several parameters in one request."""
import httpx
from fastapi import HTTPException

from app.services.nasa_service import NASA_POWER_URL


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

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(NASA_POWER_URL, params=params)
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

    return result
