from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    cpcb_path = ROOT / "data" / "interim" / "cpcb_daily.csv"
    if not cpcb_path.exists():
        raise SystemExit("Run scripts/03_prepare_cpcb.py first.")

    cpcb = pd.read_csv(cpcb_path)
    cpcb["date"] = pd.to_datetime(cpcb["date"])

    # This starter table keeps CPCB data ready for model training.
    # Add satellite and ERA5 nearest-pixel extraction here after raw files are downloaded.
    cpcb["month"] = cpcb["date"].dt.month
    cpcb["dayofyear"] = cpcb["date"].dt.dayofyear

    out_path = ROOT / "data" / "processed" / "station_training_table.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cpcb.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")
    print("Next implementation step: extract nearest S5P/INSAT/ERA5 pixels for each station-date.")


if __name__ == "__main__":
    main()
