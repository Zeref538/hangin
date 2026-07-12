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

# 5 PH metros — pooled into one model with location features (training set)
CITIES = [
    {"id": "manila",      "name": "Manila",      "lat": 14.60, "lon": 120.98},
    {"id": "quezon_city", "name": "Quezon City", "lat": 14.68, "lon": 121.05},
    {"id": "cebu",        "name": "Cebu City",   "lat": 10.32, "lon": 123.90},
    {"id": "davao",       "name": "Davao City",  "lat":  7.19, "lon": 125.46},
    {"id": "baguio",      "name": "Baguio",      "lat": 16.41, "lon": 120.60},
]

# More PH cities served at inference time. The pooled model generalizes via its
# lat/lon + weather features, but accuracy is only *verified* on the 5 above.
EXTRA_CITIES = [
    {"id": "angeles",         "name": "Angeles",         "lat": 15.15, "lon": 120.59},
    {"id": "bacolod",         "name": "Bacolod",         "lat": 10.68, "lon": 122.95},
    {"id": "batangas",        "name": "Batangas City",   "lat": 13.76, "lon": 121.06},
    {"id": "butuan",          "name": "Butuan",          "lat":  8.95, "lon": 125.54},
    {"id": "cagayan_de_oro",  "name": "Cagayan de Oro",  "lat":  8.48, "lon": 124.65},
    {"id": "cotabato",        "name": "Cotabato City",   "lat":  7.22, "lon": 124.25},
    {"id": "dagupan",         "name": "Dagupan",         "lat": 16.04, "lon": 120.33},
    {"id": "dumaguete",       "name": "Dumaguete",       "lat":  9.31, "lon": 123.31},
    {"id": "general_santos",  "name": "General Santos",  "lat":  6.11, "lon": 125.17},
    {"id": "iligan",          "name": "Iligan",          "lat":  8.23, "lon": 124.24},
    {"id": "iloilo",          "name": "Iloilo City",     "lat": 10.72, "lon": 122.56},
    {"id": "laoag",           "name": "Laoag",           "lat": 18.20, "lon": 120.59},
    {"id": "legazpi",         "name": "Legazpi",         "lat": 13.14, "lon": 123.74},
    {"id": "lucena",          "name": "Lucena",          "lat": 13.94, "lon": 121.62},
    {"id": "naga",            "name": "Naga",            "lat": 13.62, "lon": 123.19},
    {"id": "olongapo",        "name": "Olongapo",        "lat": 14.83, "lon": 120.28},
    {"id": "puerto_princesa", "name": "Puerto Princesa", "lat":  9.74, "lon": 118.74},
    {"id": "roxas",           "name": "Roxas",           "lat": 11.59, "lon": 122.75},
    {"id": "surigao",         "name": "Surigao",         "lat":  9.79, "lon": 125.49},
    {"id": "tacloban",        "name": "Tacloban",        "lat": 11.24, "lon": 125.00},
    {"id": "tagbilaran",      "name": "Tagbilaran",      "lat":  9.65, "lon": 123.85},
    {"id": "tuguegarao",      "name": "Tuguegarao",      "lat": 17.61, "lon": 121.73},
    {"id": "vigan",           "name": "Vigan",           "lat": 17.57, "lon": 120.39},
    {"id": "zamboanga",       "name": "Zamboanga",       "lat":  6.91, "lon": 122.08},
]

ALL_CITIES = CITIES + EXTRA_CITIES

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
    err = None
    for attempt in range(5):
        try:
            r = requests.get(url, params=params, timeout=60)
            if r.status_code == 200:
                return r.json()
            err = requests.HTTPError(f"{r.status_code} for {url}")
        except requests.RequestException as e:
            err = e
        time.sleep(2 * (attempt + 1))
    raise err


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
