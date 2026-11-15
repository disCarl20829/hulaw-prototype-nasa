from datetime import date
from pathlib import Path
import re

from app.services import smap_fetch_service
from app.services.cache_service import cache_get, cache_set

BASE_DIR = Path(__file__).resolve().parents[2]
SMAP_DIR = BASE_DIR / "data" / "smap"

MAX_DISTANCE_KM = 20.0

def find_smap_file(observation_date: date):
    date_text = observation_date.strftime("%Y%m%d")

    pattern = re.compile(
        rf"^SMAP_L3_SM_P_E_{date_text}_.*\.h5$",
        re.IGNORECASE
    )

    matches = sorted(
        (
            path
            for path in SMAP_DIR.glob("*.h5")
            if pattern.match(path.name)
        ),
        reverse=True
    )

    return matches[0] if matches else None


PENDING_NOTE = (
    "The SMAP file for this date (about 650 MB) is being downloaded "
    "from NASA. This usually takes several minutes. Ask again shortly."
)


def extract_soil_moisture(
    latitude: float,
    longitude: float,
    observation_date: date
):
    """Soil moisture at one point on one day.

    With on-demand downloads enabled (see smap_fetch_service), a missing
    file is fetched in the background and the answer is "pending" until it
    arrives. Extracted values are cached, so they outlive the file.
    """
    filepath = find_smap_file(observation_date)
    cache_key = (
        f"smap-point:v1:{latitude:.4f}:{longitude:.4f}:"
        f"{observation_date.isoformat()}"
    )

    if filepath is None:
        if smap_fetch_service.enabled():
            cached = cache_get(cache_key)

            if cached is not None:
                return cached

        result = _extract_from_file(
            None, latitude, longitude, observation_date
        )
        job = smap_fetch_service.request_file(
            observation_date, latitude, longitude
        )

        if job["state"] in {"queued", "downloading"}:
            result["status"] = "pending"
            result["note"] = PENDING_NOTE
        elif job["state"] == "busy":
            result["note"] = (
                "Too many SMAP files are already being downloaded. "
                "Ask again in a few minutes."
            )
        elif job["state"] == "unavailable":
            result["note"] = (
                "NASA has no SMAP SPL3SMP_E version 006 file for this date."
            )
        elif job["state"] == "failed":
            result["note"] = (
                "The SMAP file for this date could not be downloaded "
                f"({job['error']}). It will be tried again later."
            )

        return result

    result = _extract_from_file(
        filepath, latitude, longitude, observation_date
    )

    if smap_fetch_service.enabled():
        cache_set(cache_key, result)

    return result


def _extract_from_file(
    filepath,
    latitude: float,
    longitude: float,
    observation_date: date
):

    result = {
        "source": "NASA NSIDC",
        "dataset": "SMAP SPL3SMP_E",
        "version": "006",
        "date": observation_date.isoformat(),
        "requested_location": {
            "latitude": latitude,
            "longitude": longitude
        },
        "grid_location": None,
        "soil_moisture": None,
        "unit": "m3/m3",
        "quality_flag": None,
        "distance_km": None,
        "retrieval_period": None,
        "status": "no_data",
        "filename": filepath.name if filepath else None,
        "note": ""
    }

    if filepath is None:
        result["note"] = (
            "No downloaded SMAP file exists for this date."
        )
        return result

    # Imported here, not at module level: these are large libraries and are
    # only needed when a SMAP file is actually present. A host without the
    # files (the deployed API) then starts faster and uses less memory.
    import h5py
    import numpy as np

    retrieval_groups = [
        ("AM", "Soil_Moisture_Retrieval_Data_AM", ""),
        ("PM", "Soil_Moisture_Retrieval_Data_PM", "_pm")
    ]

    best_distance = float("inf")
    best = None

    with h5py.File(filepath, "r") as f:

        for period, group_name, suffix in retrieval_groups:

            if group_name not in f:
                continue

            group = f[group_name]

            lat_name = f"latitude{suffix}"
            lon_name = f"longitude{suffix}"
            moisture_name = f"soil_moisture{suffix}"
            quality_name = f"retrieval_qual_flag{suffix}"

            required = [
                lat_name,
                lon_name,
                moisture_name,
                quality_name
            ]

            if not all(name in group for name in required):
                continue

            lat = group[lat_name]
            lon = group[lon_name]
            moisture = group[moisture_name]
            quality = group[quality_name]

            if not (
                lat.ndim == 2
                and lat.shape == lon.shape
                == moisture.shape == quality.shape
            ):
                continue

            # Read the data in batches
            for start in range(0, lat.shape[0], 128):
                stop = min(
                    start + 128,
                    lat.shape[0]
                )

                la = lat[start:stop, :]
                lo = lon[start:stop, :]
                sm = moisture[start:stop, :]
                qa = quality[start:stop, :]

                # Haversine distance calculation
                dlat = np.radians(la - latitude)

                dlon = np.radians(
                    (lo - longitude + 180) % 360 - 180
                )

                a = (
                    np.sin(dlat / 2) ** 2
                    + np.cos(np.radians(latitude))
                    * np.cos(np.radians(la))
                    * np.sin(dlon / 2) ** 2
                )

                distance = (
                    6371.0
                    * 2
                    * np.arcsin(
                        np.sqrt(np.clip(a, 0, 1))
                    )
                )

                valid = (
                    np.isfinite(la)
                    & np.isfinite(lo)
                    & np.isfinite(sm)
                    & (la >= -90)
                    & (la <= 90)
                    & (lo >= -180)
                    & (lo <= 180)
                    & (sm >= 0)
                    & (sm <= 1)
                    & np.isin(qa, [0, 8])
                    & (distance <= MAX_DISTANCE_KM)
                )

                candidates = np.where(
                    valid,
                    distance,
                    np.inf
                )

                index = np.unravel_index(
                    np.argmin(candidates),
                    candidates.shape
                )

                current_distance = float(
                    candidates[index]
                )

                if current_distance < best_distance:
                    row, col = index

                    best_distance = current_distance

                    best = {
                        "latitude": float(la[row, col]),
                        "longitude": float(lo[row, col]),
                        "moisture": float(sm[row, col]),
                        "quality": int(qa[row, col]),
                        "period": period
                    }

    if best is None:
        result["note"] = (
            "File found, but no quality-accepted "
            "soil moisture retrieval exists "
            "within 20 km of the requested location."
        )
        return result

    result.update({
        "grid_location": {
            "latitude": best["latitude"],
            "longitude": best["longitude"]
        },
        "soil_moisture": round(
            best["moisture"], 4
        ),
        "quality_flag": best["quality"],
        "distance_km": round(
            best_distance, 2
        ),
        "retrieval_period": best["period"],
        "status": "valid",
        "note": (
            f"SMAP {best['period']} retrieval with "
            f"quality flag {best['quality']} accepted. "
            "This represents gridded near-surface "
            "soil moisture, not individual farm conditions."
        )
    })

    return result