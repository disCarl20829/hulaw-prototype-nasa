
from pathlib import Path
import h5py
import numpy as np

BASE = Path(__file__).resolve().parents[1]
DATA_DIR = BASE / "data" / "smap"

LAT = 15.7
LON = 120.9

files = sorted(DATA_DIR.glob("*20240116*.h5"))

if not files:
    raise SystemExit("SMAP file not found")

def inspect_group(f, name, suffix):
    if name not in f:
        print(f"{name}: Not available")
        return

    g = f[name]

    fields = {
        "lat": f"latitude{suffix}",
        "lon": f"longitude{suffix}",
        "sm": f"soil_moisture{suffix}",
        "qa": f"retrieval_qual_flag{suffix}"
    }

    print(f"\nGROUP: {name}")

    missing = [
        field for field in fields.values()
        if field not in g
    ]

    if missing:
        print("Missing fields:", missing)
        print("Available:", list(g.keys())[:30])
        return

    lat = g[fields["lat"]][:]
    lon = g[fields["lon"]][:]
    sm = g[fields["sm"]][:]
    qa = g[fields["qa"]][:]

    valid_geo = (
        np.isfinite(lat)
        & np.isfinite(lon)
        & (lat >= -90)
        & (lat <= 90)
        & (lon >= -180)
        & (lon <= 180)
    )

    dlat = np.radians(lat - LAT)
    dlon = np.radians(
        (lon - LON + 180) % 360 - 180
    )

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(np.radians(LAT))
        * np.cos(np.radians(lat))
        * np.sin(dlon / 2) ** 2
    )

    distance = 6371 * 2 * np.arcsin(
        np.sqrt(np.clip(a, 0, 1))
    )

    distance = np.where(
        valid_geo, distance, np.inf
    )

    valid_sm = (
        valid_geo
        & np.isfinite(sm)
        & (sm >= 0)
        & (sm <= 1)
    )

    valid_quality = valid_sm & (qa == 0)

    print("Cells with valid coordinates:", int(valid_geo.sum()))
    print("Cells with numeric moisture:", int(valid_sm.sum()))
    print("Cells with quality flag 0:", int(valid_quality.sum()))

    for title, mask in [
        ("Nearest coordinate", valid_geo),
        ("Nearest numeric moisture", valid_sm),
        ("Nearest quality-accepted moisture", valid_quality)
    ]:
        if not np.any(mask):
            print(title, ": none")
            continue

        candidate = np.where(mask, distance, np.inf)

        idx = np.unravel_index(
            np.argmin(candidate),
            candidate.shape
        )

        print(f"\n{title}:")
        print("Latitude:", float(lat[idx]))
        print("Longitude:", float(lon[idx]))
        print("Distance km:", round(float(distance[idx]), 2))
        print("Soil moisture:", float(sm[idx]))
        print("Quality flag:", int(qa[idx]))


with h5py.File(files[0], "r") as f:
    inspect_group(
        f,
        "Soil_Moisture_Retrieval_Data_AM",
        ""
    )

    inspect_group(
        f,
        "Soil_Moisture_Retrieval_Data_PM",
        "_pm"
    )