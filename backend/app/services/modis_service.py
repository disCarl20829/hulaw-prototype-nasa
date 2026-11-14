from datetime import date, datetime, timedelta

import httpx
from fastapi import HTTPException


BASE_URL = "https://modis.ornl.gov/rst/api/v1"
PRODUCT = "MOD13Q1"

NDVI_BAND = "250m_16_days_NDVI"
EVI_BAND = "250m_16_days_EVI"
QA_BAND = "250m_16_days_VI_Quality"

SCALE_FACTOR = 0.0001


def modis_to_date(value: str) -> date:
    # MODIS dates use AYYYYDDD format.
    return datetime.strptime(
        value, "A%Y%j"
    ).date()


async def get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict | None = None
):
    try:
        response = await client.get(
            url,
            params=params,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        return response.json()

    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"NASA MODIS request failed: {type(exc).__name__}"
        ) from exc


def extract_center_pixel(data: dict):
    rows = int(data["nrows"])
    cols = int(data["ncols"])

    center_index = (rows // 2) * cols + (cols // 2)

    records = {}

    for item in data["subset"]:
        observation_date = item["modis_date"]
        band = item["band"]
        values = item["data"]

        if len(values) != rows * cols:
            continue

        records.setdefault(observation_date, {})
        records[observation_date][band] = values[center_index]

        if "version" in item:
            records[observation_date]["version"] = item["version"]

    observations = []

    for modis_date in sorted(records):
        bands = records[modis_date]

        raw_ndvi = bands.get(NDVI_BAND)
        raw_evi = bands.get(EVI_BAND)
        raw_qa = bands.get(QA_BAND)

        # MODLAND QA occupies the two lowest bits.
        # 00 means good quality.
        valid_qa = (
            isinstance(raw_qa, int)
                and not isinstance(raw_qa, bool)
                and (raw_qa & 3) == 0
                and ((raw_qa >> 2) & 15) <= 2
                and ((raw_qa >> 6) & 3) <= 1
                and ((raw_qa >> 8) & 1) == 0
                and ((raw_qa >> 10) & 1) == 0
                and ((raw_qa >> 11) & 7) == 1
                and ((raw_qa >> 14) & 1) == 0
                and ((raw_qa >> 15) & 1) == 0
        )

        def scale_index(raw):
            if (
                not valid_qa
                or not isinstance(raw, (int, float))
                or isinstance(raw, bool)
                or not -2000 <= raw <= 10000
            ):
                return None

            return round(raw * SCALE_FACTOR, 4)

        ndvi = scale_index(raw_ndvi)
        evi = scale_index(raw_evi)

        status = (
            "valid"
            if ndvi is not None and evi is not None
            else "no_data"
        )

        observations.append({
            "date": modis_to_date(modis_date).isoformat(),
            "modis_date": modis_date,
            "ndvi": ndvi,
            "evi": evi,
            "qa_value": raw_qa,
            "status": status,
            "product_version": bands.get("version")
        })

    return observations


async def get_vegetation_history(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date
):
    async with httpx.AsyncClient(timeout=90.0) as client:

        dates_response = await get_json(
            client,
            f"{BASE_URL}/{PRODUCT}/dates",
            {
                "latitude": latitude,
                "longitude": longitude
            }
        )

        if isinstance(dates_response, list):
            available_dates = dates_response
        elif isinstance(dates_response, dict):
            available_dates = dates_response.get("dates", [])
        else:
            raise HTTPException(
                status_code=502,
                detail="Unexpected MODIS dates response"
            )

        selected_dates = []

        for entry in available_dates:
            modis_date = entry.get("modis_date")

            if not modis_date:
                continue

            try:
                day = modis_to_date(modis_date)
            except ValueError:
                continue

            if start_date <= day <= end_date:
                selected_dates.append(modis_date)

        selected_dates = sorted(set(selected_dates))

        if not selected_dates:
            return {
                "source": "NASA ORNL DAAC",
                "dataset": PRODUCT,
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "temporal_resolution": "16-day composite",
                "spatial_resolution_m": 250,
                "observations": [],
                "count": 0,
                "note": "No MODIS composite dates found for the selected period."
            }

        # ORNL DAAC limits synchronous subset requests
        # to 10 composite dates.
        if len(selected_dates) > 10:
            raise HTTPException(
                status_code=400,
                detail="Select a shorter period (maximum 10 MODIS composites)"
            )

        subset = await get_json(
            client,
            f"{BASE_URL}/{PRODUCT}/subset",
            {
                "latitude": latitude,
                "longitude": longitude,
                "startDate": selected_dates[0],
                "endDate": selected_dates[-1],
                "kmAboveBelow": 0,
                "kmLeftRight": 0
            }
        )

    observations = extract_center_pixel(subset)

    # Keep only the selected composite dates.
    observations = [
        item for item in observations
        if item["modis_date"] in selected_dates
    ]

    return {
        "source": "NASA ORNL DAAC",
        "dataset": PRODUCT,
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "temporal_resolution": "16-day composite",
        "spatial_resolution_m": 250,
        "observations": observations,
        "count": len(observations),
        "note": (
            "NDVI/EVI are center-pixel vegetation indices "
            "scaled by 0.0001. Only basic MODLAND QA "
            "good-quality pixels are accepted. "
            "Vegetation changes do not establish drought causation."
        )
    }
