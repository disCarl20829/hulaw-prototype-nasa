import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np


BASE = Path(__file__).resolve().parents[1]
CACHE = BASE / "data" / "cache" / "smap_central_luzon.csv"

TARGET_MONTH = 1
BASELINE_START = 2019
BASELINE_END = 2023
TARGET_PERIOD = "PM"

REFERENCE_LAT = 15.6893568
REFERENCE_LON = 120.8558121

MAX_GRID_DISTANCE_KM = 10.0
MIN_DAYS_PER_YEAR = 5
MIN_YEARS = 3


def distance_km(lat, lon):
    dlat = np.radians(lat - REFERENCE_LAT)
    dlon = np.radians(lon - REFERENCE_LON)

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(REFERENCE_LAT))
        * np.cos(np.radians(lat))
        * np.sin(dlon / 2) ** 2
    )

    return float(
        6371.0 * 2 * np.arcsin(
            np.sqrt(np.clip(a, 0, 1))
        )
    )


def main():
    if not CACHE.exists():
        print("Run build_smap_cache.py first.")
        return

    yearly = defaultdict(list)

    with CACHE.open(
        newline="", encoding="utf-8"
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["status"] != "valid":
                continue

            if row["retrieval_period"] != TARGET_PERIOD:
                continue

            day = date.fromisoformat(row["date"])

            if day.month != TARGET_MONTH:
                continue

            if not BASELINE_START <= day.year <= BASELINE_END:
                continue

            if row["quality_flag"] not in ("0", "8"):
                continue

            if not all(
                row[field]
                for field in (
                    "soil_moisture",
                    "grid_latitude",
                    "grid_longitude"
                )
            ):
                continue

            grid_distance = distance_km(
                float(row["grid_latitude"]),
                float(row["grid_longitude"])
            )

            if grid_distance > MAX_GRID_DISTANCE_KM:
                print(
                    f"Excluded {row['date']}: "
                    f"grid distance {grid_distance:.2f} km "
                    f"exceeds {MAX_GRID_DISTANCE_KM} km"
                )
                continue

            yearly[day.year].append(
                float(row["soil_moisture"])
            )

    print("\nHULAW — SMAP BASELINE READINESS")
    print("-" * 40)

    annual_means = []

    for year in range(
        BASELINE_START,
        BASELINE_END + 1
    ):
        values = yearly.get(year, [])

        print(
            f"{year}: {len(values)} valid "
            f"January {TARGET_PERIOD} observations"
        )

        if len(values) >= MIN_DAYS_PER_YEAR:
            annual_means.append(
                sum(values) / len(values)
            )

    if len(annual_means) < MIN_YEARS:
        print("\nINSUFFICIENT HISTORICAL DATA")
        print("Baseline: unavailable")
        print("Anomaly: unavailable")
        print(
            "At least three qualifying historical "
            "years are required for this prototype."
        )
        return

    baseline = sum(annual_means) / len(annual_means)

    print("\nExploratory January baseline:")
    print(f"{baseline:.4f} m3/m3")
    print("Qualifying years:", len(annual_means))
    print(
        "This reference is not an official "
        "climatological normal."
    )


if __name__ == "__main__":
    main()
