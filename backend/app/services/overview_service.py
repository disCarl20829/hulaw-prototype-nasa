"""Point-based drought overview: the latest 12 completed months of
rainfall, surface soil wetness and vegetation greenness, each compared
with its own baseline, plus an experimental combined index.

Sources
- Rainfall: NASA POWER PRECTOTCORR (daily, summed per month).
- Soil: NASA POWER GWETTOP surface soil wetness (model-based estimate,
  0-1 fraction). This is NOT a SMAP satellite retrieval.
- Vegetation: MODIS MOD13Q1 NDVI through the ORNL DAAC subset API.

Missing values stay None end to end; nothing is filled with zero.
"""
import asyncio
import logging
from calendar import monthrange
from datetime import date, datetime, timezone

import httpx
from fastapi import HTTPException

from app.services.cache_service import cache_get, cache_set
from app.services.modis_service import (
    BASE_URL as MODIS_URL,
    PRODUCT as MODIS_PRODUCT,
    extract_center_pixel,
    get_json,
    modis_to_date,
)
from app.services.power_service import get_power_daily

logger = logging.getLogger(__name__)

MONTHS = 12
BASELINE_YEARS = 5           # rainfall and vegetation baseline
SOIL_REFERENCE_YEARS = 20    # a percentile needs a longer record
MIN_BASELINE_YEARS = 3
MAX_BASELINE_YEARS = 10
EARLIEST_BASELINE_YEAR = 2001        # first full MODIS year
EARLIEST_END_MONTH = (2007, 1)       # keeps the default baselines in range
MIN_SOIL_REFERENCE_YEARS = 10
MIN_SOIL_DAYS = 20

MODIS_CHUNK = 10             # ORNL limit per synchronous subset request
MODIS_CONCURRENCY = 3

HOUR = 3600
OVERVIEW_TTL = 12 * HOUR
AREA_TTL = 7 * 24 * HOUR     # completed months do not change
AREA_GRID_DEGREES = 0.25     # finer than the source grid, coarse enough to share
AREA_CONCURRENCY = 4
MODIS_RECENT_TTL = 24 * HOUR
MODIS_SETTLED_DAYS = 120     # older composites are cached permanently

# Same rules the frontend uses (src/utils/analysis.ts).
THRESHOLDS = {
    "precip": "below baseline if anomaly < -30 mm; above if > +30 mm",
    "soil": "below normal if percentile < 25; above if > 75",
    "ndvi": "below baseline if NDVI anomaly < -0.05; above if > +0.05",
    "combined": (
        "mean of the available signed scores: rainfall = -anomaly/90, "
        "soil = (50 - percentile)/40, vegetation = -anomaly/0.2, "
        "each clipped to -1..+1 (positive = drier)"
    ),
}


# ---------------------------------------------------------------- helpers

def _clip(value: float) -> float:
    return max(-1.0, min(1.0, value))


def _mean(values: list[float]) -> float:
    return sum(values) / len(values)


def completed_months(today: date, count: int = MONTHS) -> list[tuple[int, int]]:
    """The `count` most recent fully completed calendar months."""
    year, month = today.year, today.month
    result = []

    for _ in range(count):
        month -= 1

        if month == 0:
            year, month = year - 1, 12

        result.append((year, month))

    return list(reversed(result))


def resolve_window(
    today: date,
    end_month: str | None = None,
    baseline_start: int | None = None,
    baseline_end: int | None = None,
) -> dict:
    """Work out the 12-month window and its baselines, validating any
    values chosen in the frontend's period controls."""
    latest = completed_months(today, 1)[0]

    if end_month:
        try:
            year, month = (int(part) for part in end_month.split("-"))
            date(year, month, 1)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status_code=400, detail="end_month must be YYYY-MM"
            ) from exc

        if (year, month) > latest:
            raise HTTPException(
                status_code=400,
                detail=(
                    "end_month must be a completed month "
                    f"({latest[0]}-{latest[1]:02d} or earlier)"
                ),
            )

        if (year, month) < EARLIEST_END_MONTH:
            raise HTTPException(
                status_code=400,
                detail=(
                    "end_month must be "
                    f"{EARLIEST_END_MONTH[0]}-{EARLIEST_END_MONTH[1]:02d} or later"
                ),
            )

        # Reuse completed_months by pretending "today" is the month after.
        anchor = date(year + (month == 12), month % 12 + 1, 1)
        months = completed_months(anchor)
    else:
        months = completed_months(today)

    first_year = months[0][0]

    if (baseline_start is None) != (baseline_end is None):
        raise HTTPException(
            status_code=400,
            detail="Provide both baseline_start and baseline_end, or neither",
        )

    if baseline_start is None:
        baseline_end = first_year - 1
        baseline_start = baseline_end - BASELINE_YEARS + 1
    else:
        count = baseline_end - baseline_start + 1

        if count < MIN_BASELINE_YEARS or count > MAX_BASELINE_YEARS:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Use between {MIN_BASELINE_YEARS} and "
                    f"{MAX_BASELINE_YEARS} baseline years"
                ),
            )

        if baseline_start < EARLIEST_BASELINE_YEAR:
            raise HTTPException(
                status_code=400,
                detail=f"Baseline cannot start before {EARLIEST_BASELINE_YEAR}",
            )

        if baseline_end >= first_year:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Baseline must end before the first observed year "
                    f"({first_year})"
                ),
            )

    # The soil percentile always uses the 20 years before the window.
    soil_end = first_year - 1
    soil_start = soil_end - SOIL_REFERENCE_YEARS + 1

    return {
        "months": months,
        "baseline_start": baseline_start,
        "baseline_end": baseline_end,
        "soil_start": soil_start,
        "soil_end": soil_end,
        "tag": (
            f"{months[-1][0]}-{months[-1][1]:02d}:"
            f"{baseline_start}-{baseline_end}"
        ),
    }


def status_from(value: float | None, low: float, high: float) -> str:
    if value is None:
        return "no_data"

    return "below" if value < low else "above" if value > high else "normal"


def index_label(index: float | None) -> str:
    if index is None:
        return "Insufficient data"
    if index > 0.66:
        return "Extreme dryness signal"
    if index > 0.33:
        return "Severe dryness signal"
    if index > 0.1:
        return "Moderate dryness signal"
    if index >= -0.1:
        return "Near normal"
    return "Wetter than normal"


def mood_from(index: float | None) -> str:
    """Mascot mood for the chat button, driven by the combined index."""
    if index is None:
        return "default"
    if index > 0.33:
        return "negative"
    if index > 0.1:
        return "moderate"
    return "happy"


def percentile_of(value: float, reference: list[float]) -> float:
    """Empirical percentile rank (0-100) of value within reference."""
    below = sum(1 for item in reference if item < value)
    equal = sum(1 for item in reference if item == value)

    return round((below + 0.5 * equal) / len(reference) * 100, 1)


# ----------------------------------------------------- monthly aggregation

def month_values(
    daily: dict[str, float | None], year: int, month: int
) -> tuple[list[float], int]:
    days = monthrange(year, month)[1]
    values = []

    for day in range(1, days + 1):
        value = daily.get(f"{year}{month:02d}{day:02d}")

        if value is not None:
            values.append(value)

    return values, days


def monthly_rain(daily: dict, year: int, month: int) -> dict:
    values, days = month_values(daily, year, month)
    complete = len(values) == days

    return {
        "total": round(sum(values), 2) if complete else None,
        "observed_days": len(values),
        "expected_days": days,
    }


def monthly_soil(daily: dict, year: int, month: int) -> dict:
    values, days = month_values(daily, year, month)
    enough = len(values) >= MIN_SOIL_DAYS

    return {
        "mean": round(_mean(values), 4) if enough else None,
        "valid_days": len(values),
        "expected_days": days,
    }


# ------------------------------------------------------------------ MODIS

async def modis_get(client, url: str, params: dict, attempts: int = 2):
    """get_json with one retry. Returns (data, None) or (None, reason)."""
    reason = "unknown error"

    for attempt in range(attempts):
        try:
            return await get_json(client, url, params), None
        except HTTPException as exc:
            reason = str(exc.detail)

            if attempt + 1 < attempts:
                await asyncio.sleep(1.5)

    return None, reason


def plan_modis_chunks(
    available: list[str], wanted: set[str]
) -> list[list[str]]:
    """Group wanted composite dates into runs that are consecutive in the
    provider's date list and at most MODIS_CHUNK long, so each subset
    request stays inside the ORNL limit."""
    chunks: list[list[str]] = []
    current: list[str] = []
    previous_index = None

    for index, modis_date in enumerate(available):
        if modis_date not in wanted:
            continue

        consecutive = previous_index is not None and index == previous_index + 1

        if current and (not consecutive or len(current) >= MODIS_CHUNK):
            chunks.append(current)
            current = []

        current.append(modis_date)
        previous_index = index

    if current:
        chunks.append(current)

    return chunks


async def fetch_ndvi_composites(
    latitude: float,
    longitude: float,
    wanted_months: set[tuple[int, int]],
    today: date,
    refresh: bool,
) -> tuple[dict[tuple[int, int], dict], list[str]]:
    """Return ({(year, month): {"values": [...], "total": n}}, warnings)."""
    warnings: list[str] = []
    point = f"{latitude:.4f}_{longitude:.4f}"
    by_month: dict[tuple[int, int], dict] = {}

    async with httpx.AsyncClient(timeout=90.0) as client:
        dates_key = f"modis-dates:{MODIS_PRODUCT}:{point}"
        dates_response = (
            None if refresh else cache_get(dates_key, MODIS_RECENT_TTL)
        )

        if dates_response is None:
            dates_response, reason = await modis_get(
                client,
                f"{MODIS_URL}/{MODIS_PRODUCT}/dates",
                {"latitude": latitude, "longitude": longitude},
            )

            if dates_response is None:
                logger.warning("MODIS date list failed: %s", reason)
                return {}, [
                    "Vegetation: the MODIS date list could not be retrieved "
                    f"({reason}); NDVI is shown as no data."
                ]

            cache_set(dates_key, dates_response)

        entries = (
            dates_response.get("dates", [])
            if isinstance(dates_response, dict)
            else dates_response if isinstance(dates_response, list) else []
        )

        available: list[str] = []

        for entry in entries:
            modis_date = entry.get("modis_date") if isinstance(entry, dict) else None

            if not modis_date:
                continue

            try:
                modis_to_date(modis_date)
            except ValueError:
                continue

            available.append(modis_date)

        available = sorted(set(available))
        wanted = {
            item for item in available
            if (modis_to_date(item).year, modis_to_date(item).month)
            in wanted_months
        }

        if not wanted:
            return {}, [
                f"Vegetation: {MODIS_PRODUCT} has no composites for the "
                "requested months at this location."
            ]

        semaphore = asyncio.Semaphore(MODIS_CONCURRENCY)

        async def load_chunk(chunk: list[str]) -> list[dict] | None:
            key = f"modis-subset:{MODIS_PRODUCT}:{point}:{chunk[0]}:{chunk[-1]}"
            settled = (today - modis_to_date(chunk[-1])).days > MODIS_SETTLED_DAYS
            cached = (
                None if refresh
                else cache_get(key, None if settled else MODIS_RECENT_TTL)
            )

            if cached is not None:
                return cached

            async with semaphore:
                subset, reason = await modis_get(
                    client,
                    f"{MODIS_URL}/{MODIS_PRODUCT}/subset",
                    {
                        "latitude": latitude,
                        "longitude": longitude,
                        "startDate": chunk[0],
                        "endDate": chunk[-1],
                        "kmAboveBelow": 0,
                        "kmLeftRight": 0,
                    },
                )

                try:
                    if subset is None:
                        raise ValueError(reason)

                    observations = extract_center_pixel(subset)
                except (KeyError, TypeError, ValueError) as exc:
                    logger.warning(
                        "MODIS subset %s..%s failed: %s",
                        chunk[0], chunk[-1], exc
                    )
                    return None

            observations = [
                {"modis_date": item["modis_date"], "ndvi": item["ndvi"]}
                for item in observations
                if item["modis_date"] in chunk
            ]
            cache_set(key, observations)

            return observations

        chunks = plan_modis_chunks(available, wanted)
        results = await asyncio.gather(*(load_chunk(chunk) for chunk in chunks))

    failed = sum(1 for result in results if result is None)

    if failed:
        warnings.append(
            f"Vegetation: {failed} of {len(chunks)} MODIS requests failed; "
            "the affected composites are treated as missing. Reload to retry."
        )

    for result in results:
        for item in result or []:
            day = modis_to_date(item["modis_date"])
            bucket = by_month.setdefault(
                (day.year, day.month), {"values": [], "total": 0}
            )
            bucket["total"] += 1

            if item["ndvi"] is not None:
                bucket["values"].append(item["ndvi"])

    return by_month, warnings


# ------------------------------------------------- rainfall + soil per month

def power_month(
    rain_daily: dict, soil_daily: dict, year: int, month: int,
    baseline_years: range, soil_years: range,
) -> dict:
    """Rainfall and soil wetness for one month against their baselines."""
    rain = monthly_rain(rain_daily, year, month)
    rain_history = [
        value for value in (
            monthly_rain(rain_daily, item, month)["total"]
            for item in baseline_years
        ) if value is not None
    ]
    rain_baseline = (
        round(_mean(rain_history), 2)
        if len(rain_history) >= MIN_BASELINE_YEARS else None
    )
    rain_anomaly = (
        round(rain["total"] - rain_baseline, 2)
        if rain["total"] is not None and rain_baseline is not None
        else None
    )
    rain_percent = (
        round(rain_anomaly / rain_baseline * 100, 1)
        if rain_anomaly is not None and rain_baseline > 0 else None
    )

    soil = monthly_soil(soil_daily, year, month)
    soil_history = [
        value for value in (
            monthly_soil(soil_daily, item, month)["mean"]
            for item in soil_years
        ) if value is not None
    ]
    soil_ready = len(soil_history) >= MIN_SOIL_REFERENCE_YEARS
    soil_percentile = (
        percentile_of(soil["mean"], soil_history)
        if soil["mean"] is not None and soil_ready else None
    )

    return {
        "rainfall": {
            "observed_mm": rain["total"],
            "baseline_mm": rain_baseline,
            "anomaly_mm": rain_anomaly,
            "percent_departure": rain_percent,
            "observed_days": rain["observed_days"],
            "expected_days": rain["expected_days"],
            "valid_baseline_years": len(rain_history),
            "status": status_from(rain_anomaly, -30, 30),
        },
        "soil": {
            "wetness": soil["mean"],
            "baseline_wetness": (
                round(_mean(soil_history), 4) if soil_ready else None
            ),
            "percentile": soil_percentile,
            "valid_days": soil["valid_days"],
            "expected_days": soil["expected_days"],
            "valid_reference_years": len(soil_history),
            "status": status_from(soil_percentile, 25, 75),
        },
    }


def power_range(window: dict) -> tuple[str, str]:
    last_year, last_month = window["months"][-1]
    first = min(window["soil_start"], window["baseline_start"])

    return (
        f"{first}0101",
        f"{last_year}{last_month:02d}{monthrange(last_year, last_month)[1]:02d}",
    )


# --------------------------------------------------------------- overview

def build_sources(
    baseline_start: int, baseline_end: int, soil_start: int, soil_end: int
) -> dict:
    baseline = f"{baseline_start}-{baseline_end}, same calendar month"

    return {
        "precip": {
            "dataset": "NASA POWER daily precipitation (PRECTOTCORR)",
            "variable": "Monthly rainfall total minus baseline mean",
            "unit": "mm",
            "baseline_period": baseline,
            "native_resolution": "about 0.5 x 0.625 degree grid cell",
            "limitation": (
                "Model/satellite merged estimate at one point, not GPM IMERG "
                "and not rain-gauge data. The baseline is a short exploratory "
                "comparison, not an official climatological normal."
            ),
        },
        "soil": {
            "dataset": "NASA POWER surface soil wetness (GWETTOP)",
            "variable": "Percentile of the monthly mean surface soil wetness",
            "unit": "percentile (wetness is a 0-1 fraction)",
            "baseline_period": (
                f"{soil_start}-{soil_end}, same calendar month"
            ),
            "native_resolution": "about 0.5 x 0.625 degree grid cell",
            "limitation": (
                "Model-based estimate of the top soil layer, not a SMAP "
                "satellite retrieval and not a field measurement. Recent "
                "months can be unavailable because the source lags."
            ),
        },
        "ndvi": {
            "dataset": f"NASA MODIS {MODIS_PRODUCT} NDVI (ORNL DAAC)",
            "variable": "Monthly mean NDVI minus baseline mean",
            "unit": "index",
            "baseline_period": baseline,
            "native_resolution": "250 m pixel, 16-day composites",
            "limitation": (
                "Single centre pixel with strict quality filtering, so cloudy "
                "months are often missing. Also changes with crop cycles, "
                "harvest and land use; a decline alone does not show drought."
            ),
        },
    }


async def build_overview(
    latitude: float,
    longitude: float,
    refresh: bool = False,
    today: date | None = None,
    end_month: str | None = None,
    baseline_start: int | None = None,
    baseline_end: int | None = None,
) -> dict:
    today = today or date.today()
    window = resolve_window(today, end_month, baseline_start, baseline_end)
    months = window["months"]
    first_year, first_month = months[0]
    last_year, last_month = months[-1]
    baseline_start = window["baseline_start"]
    baseline_end = window["baseline_end"]
    soil_start = window["soil_start"]
    baseline_years = range(baseline_start, baseline_end + 1)
    soil_years = range(soil_start, window["soil_end"] + 1)

    cache_key = f"overview:v2:{latitude:.3f}:{longitude:.3f}:{window['tag']}"

    if not refresh:
        cached = cache_get(cache_key, OVERVIEW_TTL)

        if cached is not None:
            cached["cached"] = True
            return cached

    wanted_ndvi_months = set(months) | {
        (year, month)
        for year in baseline_years
        for month in {item[1] for item in months}
    }

    start, end = power_range(window)
    power_task = get_power_daily(
        latitude=latitude,
        longitude=longitude,
        start=start,
        end=end,
        parameters=["PRECTOTCORR", "GWETTOP"],
    )
    ndvi_task = fetch_ndvi_composites(
        latitude, longitude, wanted_ndvi_months, today, refresh
    )

    # Rainfall and soil are required; a POWER failure is a 502.
    power, (ndvi_months, warnings) = await asyncio.gather(power_task, ndvi_task)
    rain_daily = power["PRECTOTCORR"]
    soil_daily = power["GWETTOP"]

    records = []

    for year, month in months:
        parts = power_month(
            rain_daily, soil_daily, year, month, baseline_years, soil_years
        )
        rain_anomaly = parts["rainfall"]["anomaly_mm"]
        soil_percentile = parts["soil"]["percentile"]

        # Vegetation
        bucket = ndvi_months.get((year, month), {"values": [], "total": 0})
        ndvi = round(_mean(bucket["values"]), 4) if bucket["values"] else None
        ndvi_history = [
            _mean(ndvi_months[(item, month)]["values"])
            for item in baseline_years
            if ndvi_months.get((item, month), {}).get("values")
        ]
        ndvi_baseline = (
            round(_mean(ndvi_history), 4)
            if len(ndvi_history) >= MIN_BASELINE_YEARS else None
        )
        ndvi_anomaly = (
            round(ndvi - ndvi_baseline, 4)
            if ndvi is not None and ndvi_baseline is not None else None
        )

        # Experimental combined index
        scores = {}

        if rain_anomaly is not None:
            scores["rainfall"] = _clip(-rain_anomaly / 90)
        if soil_percentile is not None:
            scores["soil"] = _clip((50 - soil_percentile) / 40)
        if ndvi_anomaly is not None:
            scores["vegetation"] = _clip(-ndvi_anomaly / 0.2)

        combined = round(_mean(list(scores.values())), 3) if scores else None

        records.append({
            "month": f"{year}-{month:02d}",
            "rainfall": parts["rainfall"],
            "soil": parts["soil"],
            "vegetation": {
                "ndvi": ndvi,
                "baseline_ndvi": ndvi_baseline,
                "anomaly": ndvi_anomaly,
                "composites_valid": len(bucket["values"]),
                "composites_total": bucket["total"],
                "valid_baseline_years": len(ndvi_history),
                "status": status_from(ndvi_anomaly, -0.05, 0.05),
            },
            "combined": {
                "index": combined,
                "label": index_label(combined),
                "indicators_used": list(scores),
            },
        })

    for name, key, field in (
        ("Rainfall", "rainfall", "anomaly_mm"),
        ("Soil wetness", "soil", "percentile"),
        ("Vegetation", "vegetation", "anomaly"),
    ):
        missing = [r["month"] for r in records if r[key][field] is None]

        if len(missing) == len(records):
            warnings.append(f"{name}: no usable value for any of the {len(records)} months.")
        elif missing:
            warnings.append(
                f"{name}: no usable value for {len(missing)} of "
                f"{len(records)} months ({', '.join(missing)})."
            )

    latest_record = next(
        (r for r in reversed(records) if r["combined"]["index"] is not None),
        None,
    )
    latest_index = latest_record["combined"]["index"] if latest_record else None

    result = {
        "location": {"latitude": latitude, "longitude": longitude},
        "period": {
            "start_month": f"{first_year}-{first_month:02d}",
            "end_month": f"{last_year}-{last_month:02d}",
            "months": len(months),
        },
        "baseline_period": {
            "start_year": baseline_start, "end_year": baseline_end
        },
        "soil_reference_period": {
            "start_year": soil_start, "end_year": window["soil_end"]
        },
        "records": records,
        "latest": {
            "month": latest_record["month"] if latest_record else None,
            "combined_index": latest_index,
            "label": index_label(latest_index),
            "mood": mood_from(latest_index),
        },
        "sources": build_sources(
            baseline_start, baseline_end, soil_start, window["soil_end"]
        ),
        "thresholds": THRESHOLDS,
        "warnings": warnings,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cached": False,
        "experimental": True,
        "note": (
            "Values describe one point, not an area average. The combined "
            "index is experimental and is not an official drought "
            "classification or warning."
        ),
    }

    # Do not keep a result that is incomplete only because a request failed.
    if not any("failed" in item or "could not" in item for item in warnings):
        cache_set(cache_key, result)

    return result


# ------------------------------------------------------- map colours by area

def snap(value: float) -> float:
    """Snap a coordinate to the map grid so nearby areas share one request."""
    return round(round(value / AREA_GRID_DEGREES) * AREA_GRID_DEGREES, 4)


async def build_area_series(
    points: list[dict],
    refresh: bool = False,
    today: date | None = None,
    end_month: str | None = None,
    baseline_start: int | None = None,
    baseline_end: int | None = None,
) -> dict:
    """Rainfall anomaly and soil percentile per month for many areas at once,
    used to colour each boundary on the map. Vegetation is left out because
    it needs many slow requests per point."""
    today = today or date.today()
    window = resolve_window(today, end_month, baseline_start, baseline_end)
    months = window["months"]
    baseline_years = range(window["baseline_start"], window["baseline_end"] + 1)
    soil_years = range(window["soil_start"], window["soil_end"] + 1)
    start, end = power_range(window)
    semaphore = asyncio.Semaphore(AREA_CONCURRENCY)

    async def load_cell(cell: tuple[float, float]) -> dict | None:
        key = f"area-series:v1:{cell[0]:.2f}:{cell[1]:.2f}:{window['tag']}"
        cached = None if refresh else cache_get(key, AREA_TTL)

        if cached is not None:
            return cached

        async with semaphore:
            try:
                power = await get_power_daily(
                    latitude=cell[0],
                    longitude=cell[1],
                    start=start,
                    end=end,
                    parameters=["PRECTOTCORR", "GWETTOP"],
                )
            except HTTPException as exc:
                logger.warning("POWER failed for %s: %s", cell, exc.detail)
                return None

        series = {"rainfall_anomaly_mm": [], "soil_percentile": []}

        for year, month in months:
            parts = power_month(
                power["PRECTOTCORR"], power["GWETTOP"],
                year, month, baseline_years, soil_years,
            )
            series["rainfall_anomaly_mm"].append(parts["rainfall"]["anomaly_mm"])
            series["soil_percentile"].append(parts["soil"]["percentile"])

        cache_set(key, series)

        return series

    cells = sorted({(snap(p["latitude"]), snap(p["longitude"])) for p in points})
    loaded = dict(zip(cells, await asyncio.gather(*(load_cell(c) for c in cells))))
    empty = [None] * len(months)
    areas = []

    for point in points:
        cell = (snap(point["latitude"]), snap(point["longitude"]))
        series = loaded.get(cell)
        areas.append({
            "id": point["id"],
            "latitude": cell[0],
            "longitude": cell[1],
            "status": "ok" if series else "error",
            "rainfall_anomaly_mm": series["rainfall_anomaly_mm"] if series else empty,
            "soil_percentile": series["soil_percentile"] if series else empty,
        })

    return {
        "months": [f"{year}-{month:02d}" for year, month in months],
        "baseline_period": {
            "start_year": window["baseline_start"],
            "end_year": window["baseline_end"],
        },
        "soil_reference_period": {
            "start_year": window["soil_start"], "end_year": window["soil_end"]
        },
        "grid_degrees": AREA_GRID_DEGREES,
        "indicators": ["rainfall", "soil"],
        "areas": areas,
        "failed": sum(1 for area in areas if area["status"] == "error"),
        "note": (
            "Each area is read at its centre point snapped to a "
            f"{AREA_GRID_DEGREES} degree grid. Rainfall and soil wetness only; "
            "vegetation is not included. Experimental, not an official "
            "drought classification."
        ),
    }
