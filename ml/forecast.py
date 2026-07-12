"""
Hangin — live inference: predict PM2.5 1/6/12/24h ahead for the 5 metros.

For each city: fetch the recent hours, build features on the latest row,
run the 4 horizon models, map predictions to EPA AQI + advice, and emit
web/public/forecasts.json together with the last 48h of actuals and the
backtest metadata (the honest-evaluation panel on the dashboard).
"""
import json
import pickle
from datetime import datetime, timezone, timedelta

import pandas as pd

import common as C

MODELS_DIR = C.DATA / "models"
PH_TZ = timezone(timedelta(hours=8))


def load_models():
    return {h: pickle.load(open(MODELS_DIR / f"model_h{h}.pkl", "rb"))
            for h in C.HORIZONS}


def city_payload(city, models, now_ph):
    df = C.fetch_recent(city, past_days=3)
    # keep only observed hours (fetch_recent also returns forecast rows)
    df = df[(df["time"] <= now_ph) & df["pm2_5"].notna()]
    feat = C.make_features(df)
    latest = feat.dropna(subset=C.FEATURES).iloc[-1]

    forecast = []
    for h in C.HORIZONS:
        pm = max(0.0, float(models[h].predict(latest[C.FEATURES].to_frame().T)[0]))
        aqi = C.pm25_to_aqi(pm)
        forecast.append({"horizon_h": h, "pm2_5": round(pm, 1), **aqi})

    now_pm = float(latest["pm2_5"])
    hist = feat.tail(48)
    history = [{"time": t.strftime("%Y-%m-%dT%H:%M"), "pm2_5": round(float(v), 1)}
               for t, v in zip(hist["time"], hist["pm2_5"])]

    return {
        "id": city["id"], "name": city["name"],
        "lat": city["lat"], "lon": city["lon"],
        "featured": any(c["id"] == city["id"] for c in C.CITIES),
        "now": {"time": latest["time"].strftime("%Y-%m-%dT%H:%M"),
                "pm2_5": round(now_pm, 1), **C.pm25_to_aqi(now_pm)},
        "history": history,
        "forecast": forecast,
    }


def fetch_grid():
    """Current PM2.5 on a ~1° grid over the PH archipelago, for the map overlay."""
    lats, lons = [], []
    for la in range(40, 210, 10):        # 4.0 .. 20.0
        for lo in range(1160, 1280, 10):  # 116.0 .. 127.0
            lats.append(la / 10)
            lons.append(lo / 10)
    res = C._get(C.AQ_URL, {
        "latitude": ",".join(map(str, lats)), "longitude": ",".join(map(str, lons)),
        "current": "pm2_5", "timezone": "Asia/Manila"})
    if isinstance(res, dict):
        res = [res]
    return [{"lat": r["latitude"], "lon": r["longitude"],
             "pm2_5": round(r["current"]["pm2_5"], 1)}
            for r in res if r.get("current", {}).get("pm2_5") is not None]


def main():
    models = load_models()
    backtest = json.load(open(C.DATA / "backtest.json"))
    now_ph = pd.Timestamp(datetime.now(PH_TZ).replace(tzinfo=None))

    cities = []
    for city in C.ALL_CITIES:
        print(f"forecasting {city['name']} ...")
        cities.append(city_payload(city, models, now_ph))

    print("fetching PM2.5 grid for map overlay ...")
    grid = fetch_grid()

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cities": cities,
        "grid": grid,
        "backtest": backtest,
    }
    C.WEB_PUBLIC.mkdir(parents=True, exist_ok=True)
    path = C.WEB_PUBLIC / "forecasts.json"
    json.dump(out, open(path, "w"), indent=1)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
