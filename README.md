# Surface AQI and HCHO Hotspot Mapping Over India

This project builds two linked pipelines:

1. Surface AQI over India from satellite, CPCB ground data, and meteorology.
2. HCHO hotspot detection and biomass-burning influence analysis using Sentinel-5P, FIRMS fire data, and winds.

The project is intentionally built step by step. Run the scripts in numeric order.

## 0. Folder Structure

```text
ISRO 2/
  config/
    project_config.yaml
  data/
    raw/
      cpcb/
      firms/
      insat3d/
      s5p/
      era5/
    interim/
    processed/
  outputs/
    figures/
    maps/
    models/
    tables/
  scripts/
  src/
    aqi_india/
```

## 1. Install Software

Install these first:

1. Python 3.10 or 3.11.
2. Git.
3. Google Earth Engine account.
4. Google Cloud project linked to Earth Engine.
5. CDS account for ERA5.
6. FIRMS MAP_KEY from NASA FIRMS.
7. MOSDAC account for INSAT-3D data.

## 2. Create Python Environment

Open PowerShell in this folder:

```powershell
cd "C:\Users\prave\OneDrive\Documents\ISRO 2"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Check the environment:

```powershell
python scripts\00_check_environment.py
```

## 3. Configure Secrets

Copy `.env.example` to `.env`:

```powershell
Copy-Item .env.example .env
```

Open `.env` and fill:

```text
GEE_PROJECT=your-google-cloud-project-id
FIRMS_MAP_KEY=your-firms-map-key
CDSAPI_URL=https://cds.climate.copernicus.eu/api
CDSAPI_KEY=your-cds-api-key
```

Never commit `.env`.

## 4. Google Earth Engine Setup

Install Earth Engine API using `requirements.txt`, then authenticate:

```powershell
earthengine authenticate
```

When the browser opens:

1. Sign in with the Google account registered for Earth Engine.
2. Allow access.
3. Copy the authorization code if asked.
4. Return to PowerShell and finish authentication.

Test:

```powershell
python scripts\01_test_gee.py
```

Expected output:

```text
Earth Engine initialized successfully.
```

## 5. Download Sentinel-5P Data

Sentinel-5P data is downloaded through Google Earth Engine.

Datasets used:

| Pollutant | Earth Engine collection | Main band |
|---|---|---|
| HCHO | COPERNICUS/S5P/OFFL/L3_HCHO | tropospheric_HCHO_column_number_density |
| NO2 | COPERNICUS/S5P/OFFL/L3_NO2 | tropospheric_NO2_column_number_density |
| SO2 | COPERNICUS/S5P/OFFL/L3_SO2 | SO2_column_number_density |
| CO | COPERNICUS/S5P/OFFL/L3_CO | CO_column_number_density |
| O3 | COPERNICUS/S5P/OFFL/L3_O3 | O3_column_number_density |

Edit `config/project_config.yaml`:

```yaml
date_range:
  start: "2023-10-01"
  end: "2023-11-30"
```

Run:

```powershell
python scripts\02_export_s5p_from_gee.py
```

This creates Earth Engine export tasks to Google Drive. After the tasks finish:

1. Open Google Drive.
2. Download the exported GeoTIFF files.
3. Place them in:

```text
data/raw/s5p/
```

Recommended first test window:

```text
2023-10-01 to 2023-10-07
```

Only expand to months or years after the one-week test works.

## 6. Download INSAT-3D AOD From MOSDAC

Manual download is safest because MOSDAC requires account login.

Steps:

1. Open https://www.mosdac.gov.in.
2. Create an account or log in.
3. Go to Data Access -> Order Data.
4. Select satellite or mission: INSAT-3D or INSAT-3DR.
5. Select product category: Imager L2 or L3 geophysical products.
6. Select Aerosol or AOD product if available for your chosen date.
7. Select India region.
8. Select date range matching `config/project_config.yaml`.
9. Choose HDF/HDF5/NetCDF format if options are given.
10. Submit order.
11. Download files when MOSDAC prepares them.
12. Place files in:

```text
data/raw/insat3d/
```

For first prototype, if INSAT-3D AOD access is delayed, use MERRA-2 or MODIS AOD as a temporary proxy and clearly label it as proxy data.

## 7. Download CPCB Ground Data

Manual download is recommended because the CPCB portal is dynamic.

Steps:

1. Open https://airquality.cpcb.gov.in/ccr/#/caaqm-dashboard-all/caaqm-landing/caaqm-data-repository.
2. Select parameter type: Raw data.
3. Select station or city.
4. Select parameters:
   - PM2.5
   - PM10
   - NO2
   - SO2
   - CO
   - Ozone
5. Select start and end dates matching the satellite period.
6. Select frequency: 1 hour if available.
7. Download CSV or Excel.
8. Save each file in:

```text
data/raw/cpcb/
```

Use filenames like:

```text
Delhi_AnandVihar_2023-10-01_2023-11-30.csv
Lucknow_Lalbagh_2023-10-01_2023-11-30.csv
```

Then normalize files:

```powershell
python scripts\03_prepare_cpcb.py
```

Output:

```text
data/interim/cpcb_daily.csv
```

## 8. Download FIRMS Fire Count Data

Get a free FIRMS MAP_KEY:

1. Open https://firms.modaps.eosdis.nasa.gov/api/area/.
2. Click Get MAP_KEY.
3. Register email.
4. Put the key in `.env`.

Run:

```powershell
python scripts\04_download_firms.py
```

Output:

```text
data/raw/firms/firms_viirs_snpp.csv
data/interim/fire_daily_grid.csv
```

India bounding box used by default:

```text
west=67, south=6, east=98, north=38
```

## 9. Download ERA5 Meteorology

Create a CDS account:

1. Open https://cds.climate.copernicus.eu.
2. Register or log in.
3. Open your profile.
4. Copy your CDS API key.
5. Put it in `.env`.

Run:

```powershell
python scripts\05_download_era5.py
```

Variables requested:

```text
2m_temperature
2m_dewpoint_temperature
10m_u_component_of_wind
10m_v_component_of_wind
surface_pressure
boundary_layer_height
total_precipitation
```

Output:

```text
data/raw/era5/era5_single_levels.nc
```

## 10. Build Training Table

This joins CPCB daily pollution data with nearest satellite pixels, AOD, and meteorology.

```powershell
python scripts\06_build_training_table.py
```

Output:

```text
data/processed/station_training_table.csv
```

Each row should represent:

```text
station_id + date + surface pollutant + satellite columns + AOD + weather + location + time features
```

## 11. Train Surface Pollutant Model

Start with a baseline model before CNN-LSTM.

```powershell
python scripts\07_train_baseline_model.py
```

Output:

```text
outputs/models/baseline_pollutant_model.joblib
outputs/tables/validation_metrics.csv
```

Metrics:

```text
RMSE
MAE
R2
Pearson R
Bias
```

Only after this baseline works, implement CNN-LSTM.

## 12. Compute AQI

The Indian AQI method calculates a sub-index for each pollutant and takes the maximum.

```powershell
python scripts\08_compute_aqi.py
```

Output:

```text
data/processed/station_aqi_daily.csv
```

## 13. Detect HCHO Hotspots

Run:

```powershell
python scripts\09_detect_hcho_hotspots.py
```

Methods implemented:

1. 95th percentile threshold.
2. Z-score anomaly.
3. Fire proximity join.

Output:

```text
data/processed/hcho_hotspots.csv
outputs/tables/fire_hcho_lag_correlation.csv
```

## 14. Create Maps

Run:

```powershell
python scripts\10_make_maps.py
```

Output:

```text
outputs/maps/
outputs/figures/
```

Required final visuals:

1. India daily AQI map.
2. Pollutant surface concentration maps.
3. HCHO mean map.
4. HCHO anomaly map.
5. HCHO hotspot map.
6. Fire count density map.
7. Wind vector overlay map.
8. Fire-HCHO lag correlation plot.

## 15. Recommended First Milestone

Do not start with the whole country for multiple years. First build this small working case:

```text
Region: North India
Dates: 2023-10-01 to 2023-10-31
Pollutants: PM2.5, NO2, CO, O3, HCHO
Fire product: VIIRS_SNPP_NRT
Model: Random Forest baseline
```

After this works, expand to all India and add CNN-LSTM.

## 16. Final Deliverables

Submit:

1. Methodology flowchart.
2. Data preprocessing explanation.
3. Model training and validation table.
4. AQI maps.
5. HCHO hotspot maps.
6. Fire-HCHO correlation analysis.
7. Transport interpretation using winds.
8. Source region ranking.
9. GitHub repository or zipped project folder.

