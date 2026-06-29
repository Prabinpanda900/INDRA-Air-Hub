from __future__ import annotations

import numpy as np
import pandas as pd


# Indian AQI breakpoints. Units:
# PM2.5, PM10, NO2, SO2, O3: microgram/m3
# CO: mg/m3
BREAKPOINTS = {
    "PM2.5": [
        (0, 30, 0, 50),
        (31, 60, 51, 100),
        (61, 90, 101, 200),
        (91, 120, 201, 300),
        (121, 250, 301, 400),
        (251, 500, 401, 500),
    ],
    "PM10": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 250, 101, 200),
        (251, 350, 201, 300),
        (351, 430, 301, 400),
        (431, 600, 401, 500),
    ],
    "NO2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 180, 101, 200),
        (181, 280, 201, 300),
        (281, 400, 301, 400),
        (401, 1000, 401, 500),
    ],
    "SO2": [
        (0, 40, 0, 50),
        (41, 80, 51, 100),
        (81, 380, 101, 200),
        (381, 800, 201, 300),
        (801, 1600, 301, 400),
        (1601, 2000, 401, 500),
    ],
    "CO": [
        (0, 1.0, 0, 50),
        (1.1, 2.0, 51, 100),
        (2.1, 10.0, 101, 200),
        (10.1, 17.0, 201, 300),
        (17.1, 34.0, 301, 400),
        (34.1, 50.0, 401, 500),
    ],
    "O3": [
        (0, 50, 0, 50),
        (51, 100, 51, 100),
        (101, 168, 101, 200),
        (169, 208, 201, 300),
        (209, 748, 301, 400),
        (749, 1000, 401, 500),
    ],
}


def pollutant_sub_index(pollutant: str, concentration: float) -> float:
    if pd.isna(concentration):
        return np.nan

    for c_low, c_high, i_low, i_high in BREAKPOINTS[pollutant]:
        if c_low <= concentration <= c_high:
            return ((i_high - i_low) / (c_high - c_low)) * (concentration - c_low) + i_low

    return 500.0 if concentration > BREAKPOINTS[pollutant][-1][1] else np.nan


def category(aqi: float) -> str:
    if pd.isna(aqi):
        return "Unknown"
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


def add_aqi_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    sub_cols = []
    for pollutant in BREAKPOINTS:
        if pollutant in result.columns:
            col = f"{pollutant}_sub_index"
            result[col] = result[pollutant].apply(lambda value: pollutant_sub_index(pollutant, value))
            sub_cols.append(col)
    result["AQI"] = result[sub_cols].max(axis=1)
    result["AQI_category"] = result["AQI"].apply(category)
    return result
