from pathlib import Path

import earthaccess

BASE = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = BASE / "data" / "smap"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

YEARS = range(2019, 2024)

PRODUCT = "SPL3SMP_E"
VERSION = "006"
MAX_GRANULES_PER_YEAR = 1


def main():
    print("HULAW - HISTORICAL SMAP DOWNLOAD")
    print("-" * 45)

    auth = earthaccess.login()

    if not auth.authenticated:
        raise RuntimeError(
            "NASA Earthdata authentication failed"
        )

    total_found = 0
    total_downloaded = 0

    for year in YEARS:
        start = f"{year}-01-15"
        end = f"{year}-01-20"

        print(f"\nSearching {start} to {end}...")

        try:
            results = earthaccess.search_data(
                short_name=PRODUCT,
                version=VERSION,
                temporal=(start, end),
                count=MAX_GRANULES_PER_YEAR
            )

            print(f"Granules found: {len(results)}")
            total_found += len(results)

            if not results:
                print(
                    "No Version 006 data returned. "
                    "Check historical product availability."
                )
                continue

            print("Downloading...")

            paths = earthaccess.download(
                results,
                local_path=str(DOWNLOAD_DIR)
            )

            for path in paths:
                print("File:", Path(path).name)

            total_downloaded += len(paths)

        except Exception as error:
            print(f"Error for {year}: {error}")
            print("Skipping this year.")

    print("\n" + "-" * 45)
    print("Historical download completed")
    print("Granules found:", total_found)
    print("Files returned:", total_downloaded)
    print("Directory:", DOWNLOAD_DIR)


if __name__ == "__main__":
    main()
