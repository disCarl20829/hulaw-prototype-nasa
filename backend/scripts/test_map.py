from pathlib import Path

import earthaccess
import h5py

BASE_DIR = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = BASE_DIR / "data" / "smap"

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def main():
    print("HULAW — NASA SMAP DATA TEST")
    print("-" * 40)

    # Step 1: Authenticate with NASA Earthdata.
    print("Authenticating with NASA Earthdata...")
    earthaccess.login()

    # Step 2: Search for an actual SMAP observation.
    print("Searching for SMAP satellite data...")

    results = earthaccess.search_data(
        short_name="SPL3SMP_E",
        version="006",
        temporal=("2024-01-16", "2024-01-16"),
        point=(120.9842, 14.5995),
        count=1
    )

    if not results:
        print("No SMAP granules found for this date.")
        return

    print(f"Found {len(results)} SMAP granule(s).")

    # Step 3: Download one real NASA file.
    print("Downloading SMAP data...")

    files = earthaccess.download(
        results,
        local_path=str(DOWNLOAD_DIR)
    )

    if not files:
        print("Download returned no files.")
        return

    for filepath in files:
        path = Path(filepath)
        print(f"Downloaded: {path}")

        # Step 4: Inspect the HDF5 file structure.
        if path.suffix.lower() not in (".h5", ".hdf5"):
            continue

        with h5py.File(path, "r") as dataset:
            print("\nAvailable HDF5 groups:")
            for group_name in dataset.keys():
                print(f" - {group_name}")

    print("\nSMAP discovery and download test complete.")


if __name__ == "__main__":
    main()