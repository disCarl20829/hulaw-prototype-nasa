from datetime import date, timedelta

from app.services.smap_service import (
    extract_soil_moisture
)


def generate_dates(start_date: date, end_date: date):
    current = start_date

    while current <= end_date:
        yield current
        current += timedelta(days=1)


def calculate_soil_moisture_history(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date
):
    observations = []

    for day in generate_dates(start_date, end_date):
        result = extract_soil_moisture(
            latitude=latitude,
            longitude=longitude,
            observation_date=day
        )

        observations.append(result)

    valid = [
        item for item in observations
        if item["status"] == "valid"
        and item["soil_moisture"] is not None
    ]

    missing_files = sum(
        1 for item in observations
        if item["filename"] is None
    )

    missing_retrievals = (
        len(observations)
        - len(valid)
        - missing_files
    )

    am_count = sum(
        1 for item in valid
        if item["retrieval_period"] == "AM"
    )

    pm_count = sum(
        1 for item in valid
        if item["retrieval_period"] == "PM"
    )

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "source": "NASA NSIDC",
        "dataset": "SMAP SPL3SMP_E",
        "version": "006",
        "unit": "m3/m3",
        "observations": observations,
        "summary": {
            "days_requested": len(observations),
            "days_valid": len(valid),
            "days_missing_file": missing_files,
            "days_missing_retrieval": missing_retrievals,
            "am_retrievals": am_count,
            "pm_retrievals": pm_count
        },
        "note": (
            "Observations are extracted from locally "
            "downloaded SMAP HDF5 files. Missing values "
            "are preserved. The nearest accepted AM or "
            "PM retrieval can differ between days. "
            "This series is not yet a historical anomaly "
            "or an official drought assessment."
        )
    }
