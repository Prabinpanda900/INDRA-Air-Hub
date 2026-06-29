from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    hcho_csv = ROOT / "data" / "interim" / "hcho_daily_grid.csv"
    fire_csv = ROOT / "data" / "interim" / "fire_daily_grid.csv"

    if not hcho_csv.exists():
        raise SystemExit(
            "Create data/interim/hcho_daily_grid.csv with columns date, lat_bin, lon_bin, hcho first."
        )

    hcho = pd.read_csv(hcho_csv)
    hcho["date"] = pd.to_datetime(hcho["date"])
    threshold = hcho["hcho"].quantile(0.95)
    mean = hcho["hcho"].mean()
    std = hcho["hcho"].std()
    hcho["hcho_z"] = (hcho["hcho"] - mean) / std
    hcho["hotspot_p95"] = hcho["hcho"] >= threshold
    hcho["hotspot_z2"] = hcho["hcho_z"] >= 2

    if fire_csv.exists():
        fire = pd.read_csv(fire_csv)
        fire["date"] = pd.to_datetime(fire["date"])
        hcho = hcho.merge(fire, on=["date", "lat_bin", "lon_bin"], how="left")
        hcho["fire_count"] = hcho["fire_count"].fillna(0)

        corr_rows = []
        for lag in range(0, 4):
            shifted = fire.copy()
            shifted["date"] = shifted["date"] + pd.to_timedelta(lag, unit="D")
            joined = hcho.merge(
                shifted,
                on=["date", "lat_bin", "lon_bin"],
                how="inner",
                suffixes=("", f"_lag{lag}"),
            )
            if len(joined) > 2:
                corr = joined["hcho"].corr(joined[f"fire_count_lag{lag}"])
                corr_rows.append({"lag_days": lag, "correlation": corr, "n": len(joined)})

        corr_path = ROOT / "outputs" / "tables" / "fire_hcho_lag_correlation.csv"
        corr_path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(corr_rows).to_csv(corr_path, index=False)
        print(f"Wrote {corr_path}")

    out_path = ROOT / "data" / "processed" / "hcho_hotspots.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    hcho.to_csv(out_path, index=False)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
