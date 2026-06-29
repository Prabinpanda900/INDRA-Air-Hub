import os
import sys
from pathlib import Path

import pandas as pd
import requests

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from aqi_india.config import load_config, load_environment  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_environment()
    cfg = load_config()
    map_key = os.getenv("FIRMS_MAP_KEY")
    if not map_key:
        raise SystemExit("Missing FIRMS_MAP_KEY in .env")

    region = cfg["region"]
    bbox = f"{region['west']},{region['south']},{region['east']},{region['north']}"
    source = cfg["firms"]["source"]
    day_range = cfg["firms"]["day_range"]
    start_date = cfg["date_range"]["start"]

    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/{source}/{bbox}/{day_range}/{start_date}"
    print(f"Downloading FIRMS data from: {url}")
    response = requests.get(url, timeout=120)
    response.raise_for_status()

    raw_path = ROOT / "data" / "raw" / "firms" / "firms_viirs_snpp.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(response.text, encoding="utf-8")
    print(f"Wrote {raw_path}")

    df = pd.read_csv(raw_path)
    
    # Safe data check using the globally imported 'os' module
    if df.empty or len(df) == 0:
        print("No fires detected for this date range. Creating an empty gridded file to prevent pipeline crashes.")
        os.makedirs("data/interim", exist_ok=True)
        pd.DataFrame(columns=["date", "lat_bin", "lon_bin", "fire_count"]).to_csv("data/interim/fire_daily_grid.csv", index=False)
        return

    if "acq_date" not in df.columns:
        raise SystemExit("FIRMS response does not contain acq_date. Check MAP_KEY/source/date.")

    df["date"] = pd.to_datetime(df["acq_date"]).dt.date
    df["lat_bin"] = (df["latitude"] / cfg["grid"]["resolution_degrees"]).round() * cfg["grid"]["resolution_degrees"]
    df["lon_bin"] = (df["longitude"] / cfg["grid"]["resolution_degrees"]).round() * cfg["grid"]["resolution_degrees"]
    daily = df.groupby(["date", "lat_bin", "lon_bin"]).size().reset_index(name="fire_count")

    out_path = ROOT / "data" / "interim" / "fire_daily_grid.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()