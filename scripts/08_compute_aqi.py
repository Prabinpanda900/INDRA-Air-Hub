import sys
from pathlib import Path

import pandas as pd

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from aqi_india.breakpoints import add_aqi_columns  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    input_path = ROOT / "data" / "processed" / "station_training_table.csv"
    if not input_path.exists():
        raise SystemExit("Run scripts/06_build_training_table.py first.")

    df = pd.read_csv(input_path)
    result = add_aqi_columns(df)

    out_path = ROOT / "data" / "processed" / "station_aqi_daily.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
