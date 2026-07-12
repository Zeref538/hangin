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
# wind direction is delivered as raw degrees (0..360) which trees read as a
# discontinuous number (359 vs 1) — encoded instead as sin/cos + u/v components
BASE_COLS = [
    "pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "ozone", "sulphur_dioxide",
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
    "wind_dir_sin", "wind_dir_cos", "wind_u", "wind_v", "ventilation",
    "precipitation", "surface_pressure", "boundary_layer_height",
]
TIME_COLS = ["hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos",
             "is_weekend", "is_fireworks"]
LAG_COLS = [f"pm2_5_lag{l}" for l in (1, 2, 3, 6, 12, 24, 48)] + ["pm10_lag1", "pm10_lag24"]
ROLL_COLS = ["pm2_5_roll6", "pm2_5_roll24", "pm2_5_std24",
             "pm2_5_diff1", "pm2_5_diff24", "pm2_5_rel24"]
GEO_COLS = ["lat", "lon", "city_code"]
FEATURES = BASE_COLS + TIME_COLS + LAG_COLS + ROLL_COLS + GEO_COLS

# city as a native categorical for HistGradientBoosting (index into FEATURES);
# cities outside the training five get NaN -> treated as missing, which HGB handles
CITY_CODE = {c["id"]: i for i, c in enumerate(CITIES)}
CAT_IDX = [FEATURES.index("city_code")]

# physical sanity caps for cleaning (µg/m³)
_CAPS = {"pm2_5": 1000, "pm10": 2000, "nitrogen_dioxide": 1000, "ozone": 1000,
         "sulphur_dioxide": 2000, "carbon_monoxide": 50000}


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


def clean_city(g):
    """Per-city cleaning: dedupe, physical caps, hourly reindex so lags align
    across archive gaps, and interpolation of short (<=3h) holes."""
    g = g.sort_values("time").drop_duplicates(subset="time", keep="last")
    num_cols = [c for c in g.columns if c not in ("time", "city")]
    # negative concentrations are sensor/model noise; absurd spikes are glitches
    for col, cap in _CAPS.items():
        if col in g:
            g[col] = g[col].clip(lower=0, upper=cap)
    # reindex to a continuous hourly grid: gaps become explicit NaN rows so
    # shift(k) is always exactly k hours (previously gaps silently misaligned lags)
    g = g.set_index("time").reindex(
        pd.date_range(g["time"].min(), g["time"].max(), freq="h"))
    g.index.name = "time"
    # bridge short gaps only; long outages stay NaN (HGB handles missing natively)
    g[num_cols] = g[num_cols].interpolate(limit=3, limit_area="inside")
    for col in ("city", "lat", "lon"):
        if col in g:
            g[col] = g[col].ffill().bfill()
    return g.reset_index()


def make_features(df, horizon=None):
    """Clean + add time/lag/rolling/physics features. If horizon is set, add
    the shifted target. Operates per-city so lags never cross city boundaries."""
    out = []
    for _, g in df.groupby("city", sort=False):
        g = clean_city(g)
        t = g["time"].dt
        g["hour_sin"] = np.sin(2 * np.pi * t.hour / 24)
        g["hour_cos"] = np.cos(2 * np.pi * t.hour / 24)
        g["dow_sin"] = np.sin(2 * np.pi * t.dayofweek / 7)
        g["dow_cos"] = np.cos(2 * np.pi * t.dayofweek / 7)
        g["month_sin"] = np.sin(2 * np.pi * t.month / 12)
        g["month_cos"] = np.cos(2 * np.pi * t.month / 12)
        g["is_weekend"] = (t.dayofweek >= 5).astype(float)
        # PH New Year fireworks: the one predictable extreme-PM event of the year
        g["is_fireworks"] = (((t.month == 12) & (t.day == 31)) |
                             ((t.month == 1) & (t.day == 1))).astype(float)
        # cyclic + vector wind, and ventilation index (wind x mixing height):
        # the standard meteorological dispersion measure — low = smog traps
        wd = np.deg2rad(g["wind_direction_10m"])
        g["wind_dir_sin"] = np.sin(wd)
        g["wind_dir_cos"] = np.cos(wd)
        g["wind_u"] = g["wind_speed_10m"] * np.sin(wd)
        g["wind_v"] = g["wind_speed_10m"] * np.cos(wd)
        g["ventilation"] = g["wind_speed_10m"] * g["boundary_layer_height"]
        for lag in (1, 2, 3, 6, 12, 24, 48):
            g[f"pm2_5_lag{lag}"] = g["pm2_5"].shift(lag)
        for lag in (1, 24):
            g[f"pm10_lag{lag}"] = g["pm10"].shift(lag)
        g["pm2_5_roll6"] = g["pm2_5"].rolling(6, min_periods=3).mean()
        g["pm2_5_roll24"] = g["pm2_5"].rolling(24, min_periods=12).mean()
        g["pm2_5_std24"] = g["pm2_5"].rolling(24, min_periods=12).std()
        # short-term momentum and how elevated we are vs the 24h norm
        g["pm2_5_diff1"] = g["pm2_5"] - g["pm2_5_lag1"]
        g["pm2_5_diff24"] = g["pm2_5"] - g["pm2_5_lag24"]
        g["pm2_5_rel24"] = g["pm2_5"] / (g["pm2_5_roll24"] + 1.0)
        g["city_code"] = float(CITY_CODE.get(g["city"].iloc[0], np.nan))
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
