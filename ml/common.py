"""Shared config, data fetching, and feature engineering for Hangin."""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
WX_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
WEB_PUBLIC = ROOT / "web" / "public"

# 5 PH metros — pooled into one model with location features
CITIES = [
    {"id": "manila",      "name": "Manila",      "lat": 14.60, "lon": 120.98},
    {"id": "quezon_city", "name": "Quezon City", "lat": 14.68, "lon": 121.05},
    {"id": "cebu",        "name": "Cebu City",   "lat": 10.32, "lon": 123.90},
    {"id": "davao",       "name": "Davao City",  "lat":  7.19, "lon": 125.46},
    {"id": "baguio",      "name": "Baguio",      "lat": 16.41, "lon": 120.60},
]

HORIZONS = [1, 6, 12, 24]  # hours ahead

AQ_VARS = "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,ozone,sulphur_dioxide"
WX_VARS = ("temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m,"
           "precipitation,surface_pressure,boundary_layer_height")

# feature columns fed to the model (built by make_features)
BASE_COLS = [
    "pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "ozone", "sulphur_dioxide",
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m",
    "precipitation", "surface_pressure", "boundary_layer_height",
]
TIME_COLS = ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos"]
LAG_COLS = [f"pm2_5_lag{l}" for l in (1, 2, 3, 6, 12, 24, 48)] + ["pm10_lag1", "pm10_lag24"]
ROLL_COLS = ["pm2_5_roll6", "pm2_5_roll24", "pm2_5_std24"]
GEO_COLS = ["lat", "lon"]
FEATURES = BASE_COLS + TIME_COLS + LAG_COLS + ROLL_COLS + GEO_COLS


def _get(url, params):
    for attempt in range(5):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        time.sleep(2 * (attempt + 1))
    r.raise_for_status()


def fetch_history(city, start, end):
    aq = _get(AQ_URL, {"latitude": city["lat"], "longitude": city["lon"],
                       "hourly": AQ_VARS, "start_date": start, "end_date": end,
                       "timezone": "Asia/Manila"})["hourly"]
    wx = _get(WX_ARCHIVE_URL, {"latitude": city["lat"], "longitude": city["lon"],
                               "hourly": WX_VARS, "start_date": start, "end_date": end,
                               "timezone": "Asia/Manila"})["hourly"]
    df = pd.DataFrame(aq).merge(pd.DataFrame(wx), on="time", how="inner")
    df["time"] = pd.to_datetime(df["time"])
    df["city"] = city["id"]
    df["lat"] = city["lat"]
    df["lon"] = city["lon"]
    return df.sort_values("time").reset_index(drop=True)


def fetch_recent(city, past_days=3):
    """Latest hours for live inference (air quality + weather, past_days back)."""
    aq = _get(AQ_URL, {"latitude": city["lat"], "longitude": city["lon"],
                       "hourly": AQ_VARS, "past_days": past_days, "forecast_days": 1,
                       "timezone": "Asia/Manila"})["hourly"]
    wx = _get(WX_FORECAST_URL, {"latitude": city["lat"], "longitude": city["lon"],
                                "hourly": WX_VARS, "past_days": past_days, "forecast_days": 1,
                                "timezone": "Asia/Manila"})["hourly"]
    df = pd.DataFrame(aq).merge(pd.DataFrame(wx), on="time", how="inner")
    df["time"] = pd.to_datetime(df["time"])
    df["city"] = city["id"]
    df["lat"] = city["lat"]
    df["lon"] = city["lon"]
    return df.sort_values("time").reset_index(drop=True)


def make_features(df, horizon=None):
    """Add time/lag/rolling features. If horizon is set, add the shifted target.
    Operates per-city so lags never cross city boundaries."""
    out = []
    for _, g in df.groupby("city", sort=False):
        g = g.sort_values("time").copy()
        t = g["time"].dt
        g["hour_sin"] = np.sin(2 * np.pi * t.hour / 24)
        g["hour_cos"] = np.cos(2 * np.pi * t.hour / 24)
        g["dow_sin"] = np.sin(2 * np.pi * t.dayofweek / 7)
        g["dow_cos"] = np.cos(2 * np.pi * t.dayofweek / 7)
        g["month_sin"] = np.sin(2 * np.pi * t.month / 12)
        g["month_cos"] = np.cos(2 * np.pi * t.month / 12)
        for lag in (1, 2, 3, 6, 12, 24, 48):
            g[f"pm2_5_lag{lag}"] = g["pm2_5"].shift(lag)
        for lag in (1, 24):
            g[f"pm10_lag{lag}"] = g["pm10"].shift(lag)
        g["pm2_5_roll6"] = g["pm2_5"].rolling(6).mean()
        g["pm2_5_roll24"] = g["pm2_5"].rolling(24).mean()
        g["pm2_5_std24"] = g["pm2_5"].rolling(24).std()
        if horizon is not None:
            g["target"] = g["pm2_5"].shift(-horizon)
        out.append(g)
    return pd.concat(out).sort_values(["time", "city"]).reset_index(drop=True)


# US EPA PM2.5 AQI breakpoints: (Clow, Chigh, Ilow, Ihigh, category, advice)
AQI_BP = [
    (0.0,  12.0,   0,  50,  "Good",
     "Air quality is good — enjoy outdoor activity."),
    (12.1, 35.4,  51, 100,  "Moderate",
     "Acceptable. Unusually sensitive people should watch for symptoms."),
    (35.5, 55.4, 101, 150,  "Unhealthy for Sensitive Groups",
     "Sensitive groups (asthma, elderly, children, outdoor workers) should limit prolonged exertion."),
    (55.5, 150.4, 151, 200, "Unhealthy",
     "Everyone may feel effects; sensitive groups should avoid outdoor exertion."),
    (150.5, 250.4, 201, 300, "Very Unhealthy",
     "Health alert — avoid outdoor activity; wear a mask if you must go out."),
    (250.5, 500.4, 301, 500, "Hazardous",
     "Emergency conditions — stay indoors with filtered air."),
]


def pm25_to_aqi(pm):
    if pm is None or (isinstance(pm, float) and np.isnan(pm)):
        return None
    pm = max(0.0, float(pm))
    for clow, chigh, ilow, ihigh, cat, advice in AQI_BP:
        if pm <= chigh:
            aqi = (ihigh - ilow) / (chigh - clow) * (pm - clow) + ilow
            return {"aqi": round(aqi), "category": cat, "advice": advice}
    clow, chigh, ilow, ihigh, cat, advice = AQI_BP[-1]
    return {"aqi": ihigh, "category": cat, "advice": advice}
