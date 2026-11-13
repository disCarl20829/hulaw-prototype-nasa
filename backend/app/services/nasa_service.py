import httpx
from fastapi import HTTPException

NASA_POWER_URL = (
    "https://power.larc.nasa.gov/"
    "api/temporal/daily/point"
)

async def get_precipitation(
    latitude: float,
    longitude: float,
    start: str,
    end: str
):
    params = {
        "parameters": "PRECTOTCORR",
        "community": "AG",
        "latitude": latitude,
        "longitude": longitude,
        "start": start,
        "end": end,
        "format": "JSON",
        "time-standard": "UTC"
    }

    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.get(
                NASA_POWER_URL,
                params=params
            )
            response.raise_for_status()
            data = response.json()

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"NASA API returned HTTP {exc.response.status_code}"
        ) from exc

    except (httpx.RequestError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail="Unable to retrieve valid NASA data"
        ) from exc

    try:
        values = data["properties"]["parameter"]["PRECTOTCORR"]
    except (KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=502,
            detail="NASA response does not contain expected PRECTOT data"
        ) from exc

    observations = []

    for date, value in sorted(values.items()):
        # NASA POWER uses negative sentinel values for missing data.
        valid = (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and value >= 0
        )

        observations.append({
            "date": date,
            "precipitation_mm": value if valid else None
        })

    return {
        "source": "NASA POWER",
        "dataset": "NASA POWER daily precipitation",
        "parameter": "PRECTOTCORR",
        "latitude": latitude,
        "longitude": longitude,
        "unit": "mm/day",
        "time_standard": "UTC",
        "observations": observations
    }
