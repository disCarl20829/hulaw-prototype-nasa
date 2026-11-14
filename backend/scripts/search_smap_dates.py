from pathlib import Path
from datetime import datetime

import h5py
import numpy as np

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data" / "smap"

TARGET_LAT = 15.7
TARGET_LON = 120.9
MAX_DISTANCE_KM = 20


def check_file(path):
    results = []

    with h5py.File(path, "r") as f:
        for period, suffix in [("AM", ""), ("PM", "_pm")]:
            name = f"Soil_Moisture_Retrieval_Data_{period}"

            if name not in f:
                continue

            g = f[name]

            fields = [
                f"latitude{suffix}",
                f"longitude{suffix}",
                f"soil_moisture{suffix}",
                f"retrieval_qual_flag{suffix}"
            ]

            if not all(field in g for field in fields):
                continue

            # Evaluate rows in chunks to limit memory use.
            lat_ds, lon_ds, sm_ds, qa_ds = (
                g[field] for field in fields
            )

            best = None

            for start in range(0, lat_ds.shape[0], 128):
                stop = min(start + 128, lat_ds.shape[0])

                lat = lat_ds[start:stop, :]
                lon = lon_ds[start:stop, :]
                sm = sm_ds[start:stop, :]
                qa = qa_ds[start:stop, :]

                valid = (
                    np.isfinite(lat)
                    & np.isfinite(lon)
                    & (lat >= -90)
                    & (lat <= 90)
                    & (lon >= -180)
                    & (lon <= 180)
                    & np.isfinite(sm)
                    & (sm >= 0)
                    & (sm <= 1)
                    & np.isin(qa, [0, 8])
                )

                # Haversine distance
                dlat = np.radians(lat - TARGET_LAT)
                dlon = np.radians(
                    (lon - TARGET_LON + 180) % 360 - 180
                )

                a = (
                    np.sin(dlat / 2) ** 2
                    + np.cos(np.radians(TARGET_LAT))
                    * np.cos(np.radians(lat))
                    * np.sin(dlon / 2) ** 2
                )

                distance = 6371 * 2 * np.arcsin(
                    np.sqrt(np.clip(a, 0, 1))
                )

                candidates = np.where(
                    valid, distance, np.inf
                )

                index = np.unravel_index(
                    np.argmin(candidates),
                    candidates.shape
                )

                km = float(candidates[index])

                if np.isfinite(km):
                    if best is None or km < best["distance"]:
                        best = {
                            "distance": km,
                            "moisture": float(sm[index]),
                            "latitude": float(lat[index]),
                            "longitude": float(lon[index])
                        }

            if best and best["distance"] <= MAX_DISTANCE_KM:
                results.append((period, best))

    return results


files = sorted(DATA_DIR.glob("*.h5"))

print(f"Checking {len(files)} downloaded SMAP files...")

if not files:
    print("Download additional observation dates first.")

found = False

for path in files:
    results = check_file(path)

    for period, result in results:
        found = True
        print(f"\nFile: {path.name}")
        print(f"Period: {period}")
        print(f"Distance: {result['distance']:.2f} km")
        print(f"Soil moisture: {result['moisture']:.4f} m3/m3")
        print(
            "Grid location:",
            result["latitude"],
            result["longitude"]
        )

if not found:
    print("\nNo quality-accepted nearby observations")
    print("were found in the downloaded files.")
