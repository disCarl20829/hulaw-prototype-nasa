from datetime import date, timedelta

from app.services.nasa_service import get_precipitation

async def calculate_monthly_rainfall(
    latitude: float,
    longitude: float,
    year: int,
    month: int
):
    # First day of the selected month
    start_date = date(year, month, 1)

    # First day of the next month
    if month == 12:
        next_month = date(year + 1, 1, 1)
    else:
        next_month = date(year, month + 1, 1)

    # Last day of the selected month
    end_date = next_month - timedelta(days=1)

    # Retrieve actual NASA precipitation observations
    nasa_data = await get_precipitation(
        latitude=latitude,
        longitude=longitude,
        start=start_date.strftime("%Y%m%d"),
        end=end_date.strftime("%Y%m%d")
    )

    observations = nasa_data["observations"]

    # Exclude missing values from the calculation
    valid_values = [
        item["precipitation_mm"]
        for item in observations
        if item["precipitation_mm"] is not None
    ]

    expected_days = end_date.day
    observed_days = len(valid_values)
    complete = observed_days == expected_days

    # A monthly total is only valid with complete coverage
    total_rainfall = (
        round(sum(valid_values), 2)
        if complete else None
    )

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "period": {
            "year": year,
            "month": month
        },
        "source": nasa_data["source"],
        "dataset": nasa_data["dataset"],
        "parameter": nasa_data["parameter"],
        "unit": "mm",
        "monthly_rainfall_mm": total_rainfall,
        "observed_days": observed_days,
        "expected_days": expected_days,
        "complete": complete,
        "daily_observations": observations
    }
