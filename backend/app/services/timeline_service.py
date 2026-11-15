import asyncio
from calendar import monthrange

from app.services.nasa_service import get_precipitation


def aggregate_month(data: dict, year: int, month: int):
    """Calculate a complete monthly rainfall total."""
    days = monthrange(year, month)[1]

    daily = {
        item["date"]: item["precipitation_mm"]
        for item in data["observations"]
    }

    values = []

    for day in range(1, days + 1):
        key = f"{year}{month:02d}{day:02d}"
        value = daily.get(key)

        if value is not None:
            values.append(value)

    complete = len(values) == days

    return {
        "rainfall_mm": (
            round(sum(values), 2)
            if complete else None
        ),
        "observed_days": len(values),
        "expected_days": days,
        "complete": complete
    }


async def calculate_rainfall_timeline(
    latitude: float,
    longitude: float,
    year: int,
    start_month: int,
    end_month: int,
    baseline_start: int,
    baseline_end: int
):
    # Fetch the observation period and every baseline year at the same
    # time, a few requests at once, instead of one after another.
    semaphore = asyncio.Semaphore(4)

    async def fetch_year(target_year: int):
        async with semaphore:
            return await get_precipitation(
                latitude=latitude,
                longitude=longitude,
                start=f"{target_year}{start_month:02d}01",
                end=(
                    f"{target_year}{end_month:02d}"
                    f"{monthrange(target_year, end_month)[1]:02d}"
                )
            )

    baseline_range = list(range(baseline_start, baseline_end + 1))
    observed_data, *baseline_results = await asyncio.gather(
        fetch_year(year),
        *(fetch_year(item) for item in baseline_range)
    )
    historical_data = dict(zip(baseline_range, baseline_results))

    timeline = []

    for month in range(start_month, end_month + 1):
        observed = aggregate_month(
            observed_data, year, month
        )

        historical_totals = []

        for baseline_year, dataset in historical_data.items():
            result = aggregate_month(
                dataset, baseline_year, month
            )

            if result["rainfall_mm"] is not None:
                historical_totals.append(
                    result["rainfall_mm"]
                )

        # Minimum 3 complete historical years.
        sufficient = len(historical_totals) >= 3

        baseline = (
            sum(historical_totals) / len(historical_totals)
            if sufficient else None
        )

        observed_total = observed["rainfall_mm"]

        if observed_total is None or baseline is None:
            anomaly = None
            departure = None
            condition = "insufficient_data"
        else:
            anomaly = observed_total - baseline

            departure = (
                anomaly / baseline * 100
                if baseline > 0 else None
            )

            if anomaly < 0:
                condition = "below_baseline"
            elif anomaly > 0:
                condition = "above_baseline"
            else:
                condition = "equal_to_baseline"

        timeline.append({
            "date": f"{year}-{month:02d}",
            "observed_rainfall_mm": observed_total,
            "baseline_rainfall_mm": (
                round(baseline, 2)
                if baseline is not None else None
            ),
            "anomaly_mm": (
                round(anomaly, 2)
                if anomaly is not None else None
            ),
            "percent_departure": (
                round(departure, 2)
                if departure is not None else None
            ),
            "condition": condition,
            "observed_days": observed["observed_days"],
            "expected_days": observed["expected_days"],
            "valid_baseline_years": len(historical_totals)
        })

    available = [
        item for item in timeline
        if item["anomaly_mm"] is not None
    ]

    below = sum(
        1 for item in available
        if item["anomaly_mm"] < 0
    )

    above = sum(
        1 for item in available
        if item["anomaly_mm"] > 0
    )

    return {
        "location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "period": {
            "year": year,
            "start_month": start_month,
            "end_month": end_month
        },
        "baseline_period": {
            "start_year": baseline_start,
            "end_year": baseline_end
        },
        "source": observed_data["source"],
        "dataset": observed_data["dataset"],
        "parameter": observed_data["parameter"],
        "unit": "mm",
        "timeline": timeline,
        "summary": {
            "months_requested": len(timeline),
            "months_with_data": len(available),
            "months_below_baseline": below,
            "months_above_baseline": above
        },
        "note": (
            "Exploratory precipitation timeline. "
            "Below-baseline rainfall is not equivalent "
            "to an official drought classification. "
            "Historical baselines use at least three "
            "complete years and require further validation."
        )
    }
