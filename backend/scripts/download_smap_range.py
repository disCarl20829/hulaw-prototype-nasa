from pathlib import Path
import earthaccess

BASE = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = BASE / "data" / "smap"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

START_DATE = "2024-01-17"
END_DATE = "2024-01-23"

def main():
    print("HULAW — SMAP MULTI-DAY DOWNLOAD")
    print("--------------------------------")

    earthaccess.login()

    print(f"Searching {START_DATE} to {END_DATE}...")

    results = earthaccess.search_data(
        short_name="SPL3SMP_E",
        version="006",
        temporal=(START_DATE, END_DATE),
        count=7
    )

    print(f"Found {len(results)} granules")

    if not results:
        print("No observations found.")
        return

    print("Downloading SMAP files...")

    paths = earthaccess.download(
        results,
        local_path=str(DOWNLOAD_DIR)
    )

    print("\nDownloaded files:")
    for path in paths:
        print(Path(path).name)

    print("\nDownload batch complete.")

if __name__ == "__main__":
    main()
