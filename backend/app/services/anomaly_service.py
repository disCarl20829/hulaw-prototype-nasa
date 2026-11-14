from app.services.rainfall_analysis_service import (
    calculate_monthly_rainfall
)

from app.services.baseline_service import (
    calculate_rainfall_baseline
)

async def calculate_rainfall_anomaly(
    latitude: float,
    longitude: float,
    year: int,
    month: int,
    baseline_start: int,
    baseline_end: int
):
    # Get observed rainfall for the selected month
    observed_data = await calculate_monthly_rainfall(
        latitude=latitude,
        longitude=longitude,
        year=year,
        month=month
    )

    # Calculate the historical average for the same month
    baseline_data = await calculate_rainfall_baseline(
        latitude=latitude,
        longitude=longitude,
        month=month,
        start_year=baseline_start,
        end_year=baseline_end
    )

    observed = observed_data["monthly_rainfall_mm"]
    baseline = baseline_data["baseline_rainfall_mm"]

    # Handle missing or incomplete observations
    if observed is None or baseline is None:
        anomaly = None
        percent_departure = None
        condition = "insufficient_data"

    else:
        anomaly = round(observed - baseline, 2)

        # Avoid division by zero
        percent_departure = (
            round((observed - baseline) / baseline * 100, 2)
            if baseline > 0 else None
        )

        if anomaly < 0:
            condition = "below_normal"
        elif anomaly > 0:
            condition = "above_normal"
        else:
            condition = "near_normal"

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "period": {
            "year": year,
            "month": month
        },
        "baseline_period": {
            "start_year": baseline_start,
            "end_year": baseline_end
        },
        "observed_rainfall_mm": observed,
        "baseline_rainfall_mm": baseline,
        "rainfall_anomaly_mm": anomaly,
        "percent_departure": percent_departure,
        "condition": condition,
        "source": observed_data["source"],
        "dataset": observed_data["dataset"],
        "parameter": observed_data["parameter"],
        "unit": "mm",
        "observed_days": observed_data["observed_days"],
        "expected_days": observed_data["expected_days"],
        "valid_baseline_years": baseline_data["valid_years"],
        "note": (
            "Rainfall anomalies describe departures from a "
            "historical reference. They are not official "
            "drought classifications."
        )
    }
