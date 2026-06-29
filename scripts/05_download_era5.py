import os
import sys
from pathlib import Path

import cdsapi

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from aqi_india.config import load_config, load_environment  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    load_environment()
    cfg = load_config()
    cds_url = os.getenv("CDSAPI_URL")
    cds_key = os.getenv("CDSAPI_KEY")
    if not cds_key:
        raise SystemExit("Missing CDSAPI_KEY in .env")

    start = cfg["date_range"]["start"]
    end = cfg["date_range"]["end"]
    dates = [str(date.date()) for date in __import__("pandas").date_range(start, end)]
    years = sorted({date[:4] for date in dates})
    months = sorted({date[5:7] for date in dates})
    days = sorted({date[8:10] for date in dates})
    region = cfg["region"]

    out_path = ROOT / "data" / "raw" / "era5" / "era5_single_levels.nc"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    request = {
        "product_type": ["reanalysis"],
        "variable": [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "surface_pressure",
            "boundary_layer_height",
            "total_precipitation",
        ],
        "year": years,
        "month": months,
        "day": days,
        "time": [f"{hour:02d}:00" for hour in range(24)],
        "data_format": "netcdf",
        "download_format": "unarchived",
        "area": [region["north"], region["west"], region["south"], region["east"]],
    }

    client = cdsapi.Client(url=cds_url, key=cds_key)
    client.retrieve("reanalysis-era5-single-levels", request, str(out_path))
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
