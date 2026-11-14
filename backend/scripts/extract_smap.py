
from pathlib import Path
import numpy as np
import h5py

BASE_DIR = Path(__file__).resolve().parents[1]
SMAP_DIR = BASE_DIR / "data" / "smap"

TARGET_LAT = 14.5995
TARGET_LON = 120.9842
MAX_DISTANCE_KM = 20.0

def extract_smap(filepath):
    with h5py.File(filepath, "r") as f:
        group_name = "Soil_Moisture_Retrieval_Data_AM"

        if group_name not in f:
            print("AM data group not found.")
            print("Available groups:", list(f.keys()))
            return

        group = f[group_name]

        required = [
            "latitude",
            "longitude",
            "soil_moisture",
            "retrieval_qual_flag"
        ]

        for field in required:
            if field not in group:
                print(f"Missing field: {field}")
                print("Available fields:", list(group.keys()))
                return

        lat = group["latitude"]
        lon = group["longitude"]
        moisture = group["soil_moisture"]
        quality = group["retrieval_qual_flag"]

        if not (
            lat.ndim == 2
            and lat.shape == lon.shape
            == moisture.shape == quality.shape
        ):
            print("Unexpected SMAP array dimensions.")
            return

        best = None
        best_distance = float("inf")

        # Scan rows in batches to avoid loading
        # the entire global grid into memory.
        for start in range(0, lat.shape[0], 128):
            stop = min(start + 128, lat.shape[0])

            la = lat[start:stop, :]
            lo = lon[start:stop, :]
            sm = moisture[start:stop, :]
            qa = quality[start:stop, :]

            # Approximate local distance in kilometers.
            dy = (la - TARGET_LAT) * 111.2
            dx = (
                (lo - TARGET_LON)
                * 111.2
                * np.cos(np.radians(TARGET_LAT))
            )

            distance = np.sqrt(dx**2 + dy**2)

            # Conservative first-pass quality filtering.
            valid = (
                np.isfinite(la)
                & np.isfinite(lo)
                & np.isfinite(sm)
                & (sm >= 0)
                & (sm <= 1)
                & (qa == 0)
                & (distance <= MAX_DISTANCE_KM)
            )

            if not np.any(valid):
                continue

            candidates = np.where(valid, distance, np.inf)
            local_index = np.unravel_index(
                np.argmin(candidates),
                candidates.shape
            )

            current_distance = float(
                candidates[local_index]
            )

            if current_distance < best_distance:
                row, col = local_index
                best_distance = current_distance

                best = {
                    "latitude": float(la[row, col]),
                    "longitude": float(lo[row, col]),
                    "soil_moisture": float(sm[row, col]),
                    "quality_flag": int(qa[row, col]),
                    "distance_km": current_distance
                }

        print("\nHULAW — SMAP SOIL MOISTURE")
        print("-" * 40)
        print("File:", filepath.name)
        print("Product: SPL3SMP_E Version 006")
        print("Target:", TARGET_LAT, TARGET_LON)

        if best is None:
            print("No suitable quality-filtered cell")
            print("within 20 km of the target.")
            return

        print("Cell latitude:", best["latitude"])
        print("Cell longitude:", best["longitude"])
        print(
            "Distance (km):",
            round(best["distance_km"], 2)
        )
        print(
            "Soil moisture (m3/m3):",
            round(best["soil_moisture"], 4)
        )
        print("Quality flag:", best["quality_flag"])
        print("Status: Valid first-pass retrieval")


def main():
    files = sorted(SMAP_DIR.glob("*.h5"))

    if not files:
        print("No SMAP HDF5 files found in:")
        print(SMAP_DIR)
        return

    print(f"Found {len(files)} HDF5 file(s).")
    extract_smap(files[0])


if __name__ == "__main__":
    main()