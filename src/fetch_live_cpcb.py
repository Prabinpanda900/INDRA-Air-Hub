import os
import sys
import time
import re
from pathlib import Path
import pandas as pd
import requests
import numpy as np

# Clean cross-platform relative paths
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

# 🛠️ AUTHENTICATED SYSTEM ENDPOINTS
API_KEY = "579b464db66ec23bdd00000193a6b8488540443c6fc904398db177d2"
RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
GATEWAY_URL = f"https://api.data.gov.in/resource/{RESOURCE_ID}"

def clean_string(text):
    """Standardizes text strings by removing punctuation and extra whitespace."""
    s = str(text).lower()
    s = re.sub(r'[^a-z0-9\s]', ' ', s)
    s = s.replace("cpcb", "").replace("imd", "").replace("state", "").strip()
    return " ".join(s.split())

def download_live_india_feed():
    """
    Connects to the CPCB data gateway, paginates through live feeds,
    and maps station values using a hierarchical station-to-city coordinate resolver.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }

    all_records = []
    chunk_size = 200  
    current_offset = 0
    page_number = 1

    print("📡 Initializing Live Automated Nationwide Pagination Loop...")
    
    while True:
        params = {
            "api-key": API_KEY,
            "format": "json",
            "offset": current_offset,
            "limit": chunk_size
        }

        print(f"📥 Fetching Page {page_number} (Records {current_offset} onwards)...")
        try:
            response = requests.get(GATEWAY_URL, params=params, headers=headers, timeout=45)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            print(f"❌ Connection interrupted on Page {page_number}: {e}")
            break

        if "records" not in payload or not payload["records"]:
            print("🏁 Reached the end of the live active data stream cluster.")
            break

        page_records = payload["records"]
        all_records.extend(page_records)
        print(f"✔️ Captured {len(page_records)} rows from Page {page_number}.")

        if len(page_records) < chunk_size:
            print("🏁 Final records block successfully cached.")
            break

        current_offset += chunk_size
        page_number += 1
        time.sleep(0.2)

    if not all_records:
        print("⚠️ No records were extracted from the server.")
        return

    print(f"\n📦 Data Gathering Complete. Total Raw Records Retained: {len(all_records)}")
    df_raw = pd.DataFrame(all_records)
    
    # 🧠 SINGULAR COLUMN TARGET EXTRACTOR
    columns_map = {}
    cols_lower = {col: str(col).lower().replace("_", "").replace(" ", "").strip() for col in df_raw.columns}
    
    for col, cl in cols_lower.items():
        if "station" in cl: columns_map["station"] = col; break
    for col, cl in cols_lower.items():
        if "pollutantavg" in cl or "indexavg" in cl: columns_map["value"] = col; break
    if "value" not in columns_map:
        for col, cl in cols_lower.items():
            if "value" in cl or "avg" in cl: columns_map["value"] = col; break
    for col, cl in cols_lower.items():
        if "pollutantid" in cl: columns_map["pollutant"] = col; break
    if "pollutant" not in columns_map:
        for col, cl in cols_lower.items():
            if "pollutant" in cl and not any(x in cl for x in ["avg", "min", "max", "unit"]): columns_map["pollutant"] = col; break
    for col, cl in cols_lower.items():
        if "update" in cl or "timestamp" in cl or "time" in cl: columns_map["timestamp"] = col; break
    for col, cl in cols_lower.items():
        if "state" in cl: columns_map["state"] = col
        if "city" in cl: columns_map["city"] = col

    df_mapped = pd.DataFrame()
    for target_name, source_name in columns_map.items():
        df_mapped[target_name] = df_raw[source_name]

    # Convert values to safe 1D numeric arrays
    df_mapped["value"] = pd.to_numeric(df_mapped["value"], errors='coerce')
    df_mapped["latitude"] = np.nan
    df_mapped["longitude"] = np.nan

    # 🗺️ DUAL-LAYER SPATIAL RESOLVER
    registry_path = ROOT / "data" / "processed" / "stations_registry.csv"
    if registry_path.exists():
        print("🗺️ Loading station registry coordinates...")
        registry = pd.read_csv(registry_path)
        
        # Level 1: Station maps
        lat_map = {clean_string(row['station']): row['latitude'] for _, row in registry.iterrows()}
        lon_map = {clean_string(row['station']): row['longitude'] for _, row in registry.iterrows()}
        
        # Level 2: Dynamic City Center fallback map computed from your registry groups
        city_lat = {}
        city_lon = {}
        reg_cols_lower = {str(c).lower().strip(): c for c in registry.columns}
        city_field = reg_cols_lower.get("city") or reg_cols_lower.get("location")
        
        if city_field:
            grouped = registry.dropna(subset=["latitude", "longitude"]).groupby(city_field)
            for city_name, group in grouped:
                c_clean = clean_string(city_name)
                city_lat[c_clean] = group["latitude"].mean()
                city_lon[c_clean] = group["longitude"].mean()

        # Execute cascading lookups
        print("⚡ Resolving spatial coordinates sequentially...")
        for idx, row in df_mapped.iterrows():
            st_clean = clean_string(row["station"])
            matched = False
            
            # Pass 1: Try exact or partial station name match
            if st_clean in lat_map:
                df_mapped.at[idx, "latitude"] = lat_map[st_clean]
                df_mapped.at[idx, "longitude"] = lon_map[st_clean]
                matched = True
            else:
                for k in lat_map.keys():
                    if k in st_clean or st_clean in k:
                        df_mapped.at[idx, "latitude"] = lat_map[k]
                        df_mapped.at[idx, "longitude"] = lon_map[k]
                        matched = True
                        break
            
            # Pass 2: Fall back to City Center if station name matches failed
            if not matched and "city" in df_mapped.columns:
                ct_clean = clean_string(row["city"])
                if ct_clean in city_lat:
                    df_mapped.at[idx, "latitude"] = city_lat[ct_clean]
                    df_mapped.at[idx, "longitude"] = city_lon[ct_clean]
                    matched = True
    else:
        print("⚠️ Warning: stations_registry.csv missing at data/processed/.")

    # Core high-fidelity default coordinates for major cities as a final safety net
    default_cities = {
        "delhi": (28.6139, 77.2090), "mumbai": (19.0760, 72.8777), "kolkata": (22.5726, 88.3639),
        "chennai": (13.0827, 80.2707), "bengaluru": (12.9716, 77.5946), "hyderabad": (17.3850, 78.4867),
        "patna": (25.5941, 85.1376), "lucknow": (26.8467, 80.9462), "jaipur": (26.9124, 75.7873)
    }

    for idx, row in df_mapped.iterrows():
        if pd.isna(df_mapped.at[idx, "latitude"]) and "city" in df_mapped.columns:
            ct_clean = clean_string(row["city"])
            if ct_clean in default_cities:
                df_mapped.at[idx, "latitude"], df_mapped.at[idx, "longitude"] = default_cities[ct_clean]

    # Save data rows to local storage
    df_clean = df_mapped.dropna(subset=["latitude", "longitude", "value"]).copy()
    df_clean["aqi"] = df_clean["value"]

    storage_dir = ROOT / "data" / "live"
    storage_dir.mkdir(parents=True, exist_ok=True)
    
    csv_out = storage_dir / "station_aqi_live.csv"
    df_clean.to_csv(csv_out, index=False)

    print(f"✅ Compilation complete. Successfully saved {len(df_clean)} live tracking records to disk.")
    print(f"💾 File Location: {csv_out.relative_to(ROOT)}")

if __name__ == "__main__":
    download_live_india_feed()