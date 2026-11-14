from app.services.rainfall_analysis_service import (
    calculate_monthly_rainfall
)

async def calculate_rainfall_baseline(
    latitude: float,
    longitude: float,
    month: int,
    start_year: int,
    end_year: int
):
    historical_data = []
    valid_totals = []

    for year in range(start_year, end_year + 1):

        result = await calculate_monthly_rainfall(
            latitude=latitude,
            longitude=longitude,
            year=year,
            month=month
        )

        rainfall = result["monthly_rainfall_mm"]

        historical_data.append({
            "year": year,
            "month": month,
            "rainfall_mm": rainfall,
            "complete": result["complete"]
        })

        if rainfall is not None:
            valid_totals.append(rainfall)

    # Require at least 3 complete years
    sufficient_data = len(valid_totals) >= 3

    baseline = (
        round(sum(valid_totals) / len(valid_totals), 2)
        if sufficient_data else None
    )

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "month": month,
        "baseline_period": {
            "start_year": start_year,
            "end_year": end_year
        },
        "baseline_rainfall_mm": baseline,
        "unit": "mm",
        "source": "NASA POWER",
        "parameter": "PRECTOTCORR",
        "valid_years": len(valid_totals),
        "requested_years": end_year - start_year + 1,
        "sufficient_data": sufficient_data,
        "historical_data": historical_data,
        "note": (
            "Exploratory historical mean, not an official "
            "climatological normal or drought classification."
        )
    }
