import csv
import re
import sys

from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from app.services.smap_service import (
    extract_soil_moisture
)

SMAP_DIR = BASE_DIR / "data" / "smap"
CACHE_DIR = BASE_DIR / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

TARGET_LAT = 15.7
TARGET_LON = 120.9

CACHE_FILE = CACHE_DIR / "smap_central_luzon.csv"

DATE_PATTERN = re.compile(
    r"^SMAP_L3_SM_P_E_(\d{8})_.*\.h5$",
    re.IGNORECASE
)


def main():
    files = sorted(SMAP_DIR.glob("*.h5"))
    dates = set()

    for path in files:
        match = DATE_PATTERN.match(path.name)

        if match:
            dates.add(
                datetime.strptime(
                    match.group(1), "%Y%m%d"
                ).date()
            )

    print("HULAW — SMAP CACHE BUILDER")
    print(f"Dates found: {len(dates)}")

    records = []

    for day in sorted(dates):
        result = extract_soil_moisture(
            latitude=TARGET_LAT,
            longitude=TARGET_LON,
            observation_date=day
        )

        grid = result["grid_location"] or {}

        records.append({
            "date": day.isoformat(),
            "latitude": TARGET_LAT,
            "longitude": TARGET_LON,
            "grid_latitude": grid.get("latitude"),
            "grid_longitude": grid.get("longitude"),
            "soil_moisture": result["soil_moisture"],
            "retrieval_period": result["retrieval_period"],
            "quality_flag": result["quality_flag"],
            "distance_km": result["distance_km"],
            "status": result["status"],
            "dataset": result["dataset"],
            "version": result["version"],
            "source": result["source"],
            "filename": result["filename"]
        })

        print(
            day,
            result["status"],
            result["soil_moisture"],
            result["retrieval_period"]
        )

    fields = [
        "date", "latitude", "longitude",
        "grid_latitude", "grid_longitude",
        "soil_moisture", "retrieval_period",
        "quality_flag", "distance_km",
        "status", "dataset", "version",
        "source", "filename"
    ]

    with CACHE_FILE.open(
        "w", newline="", encoding="utf-8"
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=fields
        )
        writer.writeheader()
        writer.writerows(records)

    valid = sum(
        row["status"] == "valid"
        for row in records
    )

    print("\nCache created:", CACHE_FILE)
    print("Dates processed:", len(records))
    print("Valid observations:", valid)
    print("Missing observations:", len(records) - valid)


if __name__ == "__main__":
    main()
