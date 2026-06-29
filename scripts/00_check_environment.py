from pathlib import Path


REQUIRED_DIRS = [
    "config",
    "data/raw/cpcb",
    "data/raw/firms",
    "data/raw/insat3d",
    "data/raw/s5p",
    "data/raw/era5",
    "data/interim",
    "data/processed",
    "outputs/figures",
    "outputs/maps",
    "outputs/models",
    "outputs/tables",
    "scripts",
    "src/aqi_india",
]


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    for relative in REQUIRED_DIRS:
        path = root / relative
        path.mkdir(parents=True, exist_ok=True)
        print(f"OK: {path}")
    print("Environment folder check completed.")


if __name__ == "__main__":
    main()
