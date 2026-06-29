import os
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "cpcb"
OUT = ROOT / "data" / "interim" / "cpcb_daily.csv"

POLLUTANT_ALIASES = {
    "PM2.5": "PM2.5",
    "PM10": "PM10",
    "NO2": "NO2",
    "SO2": "SO2",
    "CO": "CO",
    "OZONE": "O3",
    "O3": "O3",
}

def read_any_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    try:
        return pd.read_csv(path, encoding="utf-8")
    except Exception:
        return pd.read_csv(path, encoding="cp1252")

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    renamed = {}
    used_canonicals = set()
    
    for col in df.columns:
        col_str = str(col).strip()
        upper = col_str.upper().replace(" ", "")
        
        if ("DATE" in upper or "TIME" in upper or "TIMESTAMP" in upper) and "datetime" not in used_canonicals:
            renamed[col] = "datetime"
            used_canonicals.add("datetime")
        elif "STATION" in upper and "station" not in used_canonicals:
            renamed[col] = "station"
            used_canonicals.add("station")
        elif "CITY" in upper and "city" not in used_cannicals:
            renamed[col] = "city"
            used_canonicals.add("city")
        elif "LAT" in upper and "latitude" not in used_canonicals:
            renamed[col] = "latitude"
            used_canonicals.add("latitude")
        elif ("LON" in upper or "LONG" in upper) and "longitude" not in used_canonicals:
            renamed[col] = "longitude"
            used_canonicals.add("longitude")
        else:
            for alias, canonical in POLLUTANT_ALIASES.items():
                alias_clean = alias.replace(" ", "").upper()
                if alias_clean in upper and canonical not in used_canonicals:
                    renamed[col] = canonical
                    used_canonicals.add(canonical)
                    break
                    
    return df.rename(columns=renamed)

def main() -> None:
    frames = []
    for path in sorted(RAW_DIR.glob("*")):
        if path.suffix.lower() not in {".csv", ".xlsx", ".xls"}:
            continue
            
        print(f"Processing raw CPCB file: {path.name}")
        raw_df = read_any_table(path)
        df = normalize_columns(raw_df)
        
        if "datetime" not in df.columns:
            print(f"Skipping {path.name}: no datetime-like column found.")
            continue
            
        df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
        df = df.dropna(subset=["datetime"])
        df["date"] = df["datetime"].dt.date
        
        if "station" not in df.columns:
            df["station"] = path.stem
            
        pollutant_cols = [col for col in POLLUTANT_ALIASES.values() if col in df.columns]
        
        # FIX: Force clean numeric conversion immediately on the single dataframe BEFORE appending
        for col in pollutant_cols:
            # .squeeze() handles it if there are accidental duplicate columns inside the same file
            s = df[col]
            if isinstance(s, pd.DataFrame):
                s = s.iloc[:, 0]
            df[col] = pd.to_numeric(s, errors="coerce")
            
        keep = ["date", "station", "city", "latitude", "longitude"] + pollutant_cols
        keep = [col for col in keep if col in df.columns]
        
        # Ensure we drop duplicate columns if they exist before appending
        cleaned_df = df[keep]
        cleaned_df = cleaned_df.loc[:, ~cleaned_df.columns.duplicated()].copy()
        frames.append(cleaned_df)

    if not frames:
        raise SystemExit(f"No CPCB CSV/XLSX files found in {RAW_DIR}")

    all_data = pd.concat(frames, ignore_index=True)
    
    pollutant_cols = [c for c in POLLUTANT_ALIASES.values() if c in all_data.columns]
    group_cols = [col for col in ["date", "station", "city", "latitude", "longitude"] if col in all_data.columns]
    
    daily = all_data.groupby(group_cols, dropna=False)[pollutant_cols].mean().reset_index()
    
    OUT.parent.mkdir(parents=True, exist_ok=True)
    daily.to_csv(OUT, index=False)
    print(f"Successfully processed and wrote {OUT}")

if __name__ == "__main__":
    main()