"""
Hangin — live inference: predict PM2.5 1/6/12/24h ahead for the 5 metros.

For each city: fetch the recent hours, build features on the latest row,
run the 4 horizon models, map predictions to EPA AQI + advice, and emit
web/public/forecasts.json together with the last 48h of actuals and the
backtest metadata (the honest-evaluation panel on the dashboard).
"""
import json
import os
import pickle
from datetime import datetime, timezone, timedelta

import numpy as np
import pandas as pd
import requests

import common as C

MODELS_DIR = C.DATA / "models"
PH_TZ = timezone(timedelta(hours=8))
LOG = C.DATA / "forecast_log.csv"
LOG_KEEP_DAYS = 45
SCORE_DAYS = 30


def load_models():
    ld = lambda n: pickle.load(open(MODELS_DIR / f"{n}.pkl", "rb"))
    meta = json.load(open(MODELS_DIR / "meta.json"))
    return {h: {"mid": ld(f"model_h{h}"), "lo": ld(f"q10_h{h}"), "hi": ld(f"q90_h{h}"),
                "margin": meta["margins"][str(h)]} for h in C.HORIZONS}, meta


def city_payload(city, models, now_ph, log_rows, actuals):
    raw = C.fetch_recent(city, past_days=3)
    # Open-Meteo's own forecast for the coming hours, to score ours against
    om = raw[raw["time"] > now_ph].set_index("time")["pm2_5"]
    df = raw
    for t, v in raw[(raw["time"] <= now_ph) & raw["pm2_5"].notna()][["time", "pm2_5"]].values:
        actuals[(city["id"], pd.Timestamp(t))] = float(v)
    # keep only observed hours (fetch_recent also returns forecast rows)
    df = df[(df["time"] <= now_ph) & df["pm2_5"].notna()]
    feat = C.make_features(df)
    feat = feat[feat["pm2_5"].notna()]  # model tolerates NaN features, not a NaN "now"
    latest = feat.iloc[-1]

    forecast = []
    X = latest[C.FEATURES].to_frame().T.astype(float)
    now_pm = float(latest["pm2_5"])
    for h in C.HORIZONS:
        m = models[h]
        pm = max(0.0, float(m["mid"].predict(X)[0]))
        lo = max(0.0, float(m["lo"].predict(X)[0]) - m["margin"])
        hi = max(pm, float(m["hi"].predict(X)[0]) + m["margin"])
        lo = min(lo, pm)
        aqi = C.pm25_to_aqi(pm)
        forecast.append({"horizon_h": h, "pm2_5": round(pm, 1),
                         "low": round(lo, 1), "high": round(hi, 1), **aqi})
        if any(c["id"] == city["id"] for c in C.CITIES):
            target = latest["time"] + pd.Timedelta(hours=h)
            log_rows.append({"made_for": latest["time"], "city": city["id"], "horizon_h": h,
                             "target_time": target, "model": round(pm, 2),
                             "low": round(lo, 2), "high": round(hi, 2), "naive": round(now_pm, 2),
                             "openmeteo": round(float(om[target]), 2) if pd.notna(om.get(target)) else np.nan})
    hist = feat.tail(48)
    history = [{"time": t.strftime("%Y-%m-%dT%H:%M"), "pm2_5": round(float(v), 1)}
               for t, v in zip(hist["time"], hist["pm2_5"])]

    return {
        "id": city["id"], "name": city["name"],
        "lat": city["lat"], "lon": city["lon"],
        "featured": any(c["id"] == city["id"] for c in C.CITIES),
        "pollutants": {k: round(float(latest[k]), 1) for k in (
            "pm10", "nitrogen_dioxide", "ozone", "sulphur_dioxide",
            "carbon_monoxide") if pd.notna(latest[k])},
        "weather": {k: round(float(latest[k]), 1) for k in (
            "temperature_2m", "relative_humidity_2m", "wind_speed_10m",
            "precipitation") if pd.notna(latest[k])},
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


def update_log(new_rows, actuals):
    """Append this run's forecasts, fill in actuals that have arrived, trim, save."""
    cols = ["made_for", "city", "horizon_h", "target_time", "model", "low", "high",
            "naive", "openmeteo", "actual"]
    log = (pd.read_csv(LOG, parse_dates=["made_for", "target_time"]) if LOG.exists()
           else pd.DataFrame(columns=cols))
    log = pd.concat([log, pd.DataFrame(new_rows)], ignore_index=True)
    # the same hour can be forecast by several runs: keep the first issue (no hindsight)
    log = log.drop_duplicates(subset=["made_for", "city", "horizon_h"], keep="first")
    got = [actuals.get((c, t)) for c, t in zip(log["city"], log["target_time"])]
    log["actual"] = log["actual"].where(log["actual"].notna(), pd.Series(got, index=log.index, dtype=float))
    log = log[log["made_for"] >= log["made_for"].max() - pd.Timedelta(days=LOG_KEEP_DAYS)]
    tmp = LOG.with_suffix(".csv.tmp")
    log[cols].sort_values(["made_for", "city", "horizon_h"]).to_csv(tmp, index=False)
    os.replace(tmp, LOG)
    return log


def live_score(log):
    """Scorecard over forecasts whose real value is now known (last SCORE_DAYS)."""
    done = log[log["actual"].notna()]
    done = done[done["target_time"] >= done["target_time"].max() - pd.Timedelta(days=SCORE_DAYS)] if len(done) else done
    out = []
    for h in C.HORIZONS:
        d = done[done["horizon_h"] == h]
        if d.empty:
            continue
        err = lambda col: round(float((d[col] - d["actual"]).abs().mean()), 3)
        both = d[d["openmeteo"].notna()]
        out.append({"horizon_h": h, "n": len(d), "model_mae": err("model"), "naive_mae": err("naive"),
                    "openmeteo_mae": round(float((both["openmeteo"] - both["actual"]).abs().mean()), 3) if len(both) else None,
                    "openmeteo_n": len(both),
                    "band_coverage_pct": round(100 * float(((d["actual"] >= d["low"]) & (d["actual"] <= d["high"])).mean()), 1)})
    first = done["target_time"].min() if len(done) else None
    return {"since": first.strftime("%Y-%m-%dT%H:%M") if first is not None else None, "horizons": out}


def main():
    models, meta = load_models()
    backtest = json.load(open(C.DATA / "backtest.json"))
    now_ph = pd.Timestamp(datetime.now(PH_TZ).replace(tzinfo=None))

    path = C.WEB_PUBLIC / "forecasts.json"
    # last good run: one city's weather call timing out used to fail the refresh for all 29
    prev = json.load(open(path)) if path.exists() else {"cities": [], "grid": []}
    prev_city = {c["id"]: c for c in prev["cities"]}

    cities, log_rows, actuals, failed = [], [], {}, []
    for city in C.ALL_CITIES:
        print(f"forecasting {city['name']} ...")
        try:
            cities.append(city_payload(city, models, now_ph, log_rows, actuals))
        except requests.RequestException as e:  # the fetch is city_payload's first step, so nothing half-written
            print(f"  FAILED ({e}); keeping its last forecast")
            failed.append(city["id"])
            if city["id"] in prev_city:
                cities.append(prev_city[city["id"]])
    if len(failed) > len(C.ALL_CITIES) // 2:
        raise RuntimeError(f"{len(failed)} cities failed, Open-Meteo looks down: {failed}")
    live = live_score(update_log(log_rows, actuals))

    print("fetching PM2.5 grid for map overlay ...")
    try:
        grid = fetch_grid()
    except requests.RequestException as e:
        print(f"  grid FAILED ({e}); keeping the last one")
        grid = prev["grid"]

    out = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cities": cities,
        "grid": grid,
        "backtest": backtest,
        "model": {k: meta.get(k) for k in ("trained_through", "data_start", "n_rows", "band")},
        "live": live,
        # full-year out-of-sample test + band coverage (ml/walkforward.py, ml/intervals.py)
        "walkforward": json.load(open(C.DATA / "walkforward.json")),
        "intervals": json.load(open(C.DATA / "intervals.json")),
    }
    C.WEB_PUBLIC.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, path)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
