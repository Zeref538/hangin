"""
Hangin — Phase 1: PM2.5 24h-ahead forecaster (train + backtest).

Fetches ~3 years of hourly air-quality + weather history from Open-Meteo,
engineers lag/weather/time features, trains a HistGradientBoosting model to
predict PM2.5 24 hours ahead, and backtests it on a chronological holdout
against a naive persistence baseline (pm2_5[t] as the forecast for t+24h).

All data is free and unauthenticated. sklearn only — no xgboost/lightgbm wheels.
"""
import json
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

AQ_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
WX_URL = "https://archive-api.open-meteo.com/v1/archive"

CITY = {"name": "Manila", "lat": 14.6, "lon": 120.98}
START, END = "2022-01-01", "2024-12-31"
HORIZON = 24  # hours ahead
OUT = Path(__file__).resolve().parent.parent / "data"


def _get(url, params):
    for attempt in range(4):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 200:
            return r.json()
        time.sleep(2 * (attempt + 1))
    r.raise_for_status()


def fetch(lat, lon):
    aq = _get(AQ_URL, {
        "latitude": lat, "longitude": lon,
        "hourly": "pm2_5,pm10,carbon_monoxide,nitrogen_dioxide,ozone,sulphur_dioxide",
        "start_date": START, "end_date": END, "timezone": "Asia/Manila",
    })["hourly"]
    wx = _get(WX_URL, {
        "latitude": lat, "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,"
                  "wind_direction_10m,precipitation,surface_pressure,"
                  "boundary_layer_height",
        "start_date": START, "end_date": END, "timezone": "Asia/Manila",
    })["hourly"]
    a = pd.DataFrame(aq)
    w = pd.DataFrame(wx)
    df = a.merge(w, on="time", how="inner")
    df["time"] = pd.to_datetime(df["time"])
    return df.sort_values("time").reset_index(drop=True)


def make_features(df):
    df = df.copy()
    t = df["time"].dt
    # cyclical time encodings
    df["hour_sin"] = np.sin(2 * np.pi * t.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * t.hour / 24)
    df["dow_sin"] = np.sin(2 * np.pi * t.dayofweek / 7)
    df["dow_cos"] = np.cos(2 * np.pi * t.dayofweek / 7)
    df["month_sin"] = np.sin(2 * np.pi * t.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * t.month / 12)
    # pollutant + weather lags
    for lag in (1, 2, 3, 6, 12, 24, 48):
        df[f"pm2_5_lag{lag}"] = df["pm2_5"].shift(lag)
    for lag in (1, 24):
        df[f"pm10_lag{lag}"] = df["pm10"].shift(lag)
    # rolling stats
    df["pm2_5_roll6"] = df["pm2_5"].rolling(6).mean()
    df["pm2_5_roll24"] = df["pm2_5"].rolling(24).mean()
    df["pm2_5_std24"] = df["pm2_5"].rolling(24).std()
    # target: PM2.5 HORIZON hours in the future
    df["target"] = df["pm2_5"].shift(-HORIZON)
    return df


FEATURES = [
    "pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "ozone", "sulphur_dioxide",
    "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m",
    "precipitation", "surface_pressure", "boundary_layer_height",
    "hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos",
    "pm2_5_lag1", "pm2_5_lag2", "pm2_5_lag3", "pm2_5_lag6", "pm2_5_lag12",
    "pm2_5_lag24", "pm2_5_lag48", "pm10_lag1", "pm10_lag24",
    "pm2_5_roll6", "pm2_5_roll24", "pm2_5_std24",
]


def main():
    OUT.mkdir(exist_ok=True)
    print(f"Fetching {CITY['name']} {START}..{END} ...")
    raw = fetch(CITY["lat"], CITY["lon"])
    raw.to_parquet(OUT / "manila_raw.parquet")
    print(f"  {len(raw)} hourly rows")

    df = make_features(raw).dropna(subset=FEATURES + ["target"]).reset_index(drop=True)
    print(f"  {len(df)} usable rows after features")

    # chronological split: last 20% is the test set
    split = int(len(df) * 0.8)
    tr, te = df.iloc[:split], df.iloc[split:]
    Xtr, ytr = tr[FEATURES], tr["target"]
    Xte, yte = te[FEATURES], te["target"]

    model = HistGradientBoostingRegressor(
        max_iter=600, learning_rate=0.05, max_depth=8,
        l2_regularization=1.0, early_stopping=True, random_state=42,
    )
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)

    # baselines
    persistence = te["pm2_5"].values          # "PM2.5 won't change in 24h"
    clim = ytr.mean()                          # global mean

    def scores(name, yhat):
        return {
            "model": name,
            "mae": round(float(mean_absolute_error(yte, yhat)), 3),
            "r2": round(float(r2_score(yte, yhat)), 4),
        }

    results = [
        scores("HistGradientBoosting (ours)", pred),
        scores("persistence (naive t+24=t)", persistence),
        scores("climatology (train mean)", np.full(len(yte), clim)),
    ]

    print("\n=== 24h-ahead PM2.5 backtest (chronological holdout) ===")
    print(f"test window: {te['time'].iloc[0]} -> {te['time'].iloc[-1]}  ({len(te)} hrs)")
    for r in results:
        print(f"  {r['model']:32s}  MAE={r['mae']:6.3f}  R2={r['r2']:.4f}")

    lift = 100 * (results[1]["mae"] - results[0]["mae"]) / results[1]["mae"]
    print(f"\n  --> model beats persistence by {lift:.1f}% MAE")

    json.dump({"city": CITY["name"], "horizon_h": HORIZON, "results": results,
               "lift_vs_persistence_pct": round(lift, 1)},
              open(OUT / "backtest.json", "w"), indent=2)
    print(f"\nsaved -> {OUT/'backtest.json'}")


if __name__ == "__main__":
    main()
