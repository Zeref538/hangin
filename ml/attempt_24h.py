"""
Hangin: the pre-registered attempt in docs/ATTEMPT_NEXT.md. Run once.

Arms (same test year, purge and hyperparameters as walkforward.py):
  base   current features
  a1     + forecast wind and rain at the target hour, as issued about a day earlier
         (Open-Meteo Previous Runs API, *_previous_day1). Never observed weather.
  a2     + mean PM2.5 at the target's hour of day over the previous 7 days
  a12    both
Seeds 0, 1, 2. Decision rule is applied in code, exactly as written in the doc.

Writes data/attempt_24h.json. Run: python ml/attempt_24h.py
"""
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.base import clone

import common as C

SEEDS = [0, 1, 2]
PREV = "https://previous-runs-api.open-meteo.com/v1/forecast"
PREV_VARS = ["precipitation_previous_day1", "wind_speed_10m_previous_day1",
             "wind_direction_10m_previous_day1"]
CACHE = C.DATA / "prevday_weather.parquet"
A1 = ["fc_precip_t", "fc_wind_t", "fc_wind_u_t", "fc_wind_v_t"]
A2 = ["pm2_5_samehour_7d"]


def prevday_weather(start, end):
    if CACHE.exists():
        return pd.read_parquet(CACHE)
    frames = []
    for c in C.CITIES:
        h = C._get(PREV, {"latitude": c["lat"], "longitude": c["lon"], "start_date": start,
                          "end_date": end, "hourly": ",".join(PREV_VARS),
                          "timezone": "Asia/Manila"})["hourly"]
        frames.append(pd.DataFrame(h).assign(city=c["id"]))
    w = pd.concat(frames)
    w["time"] = pd.to_datetime(w["time"])
    w.to_parquet(CACHE)
    return w


def add_features(f, w, h):
    # the day-ahead forecast FOR hour T was issued ~24 h before T; with h <= 24 that is
    # at or before the issue time t = T - h, so shifting it back by h leaks nothing
    f = f.merge(w, on=["city", "time"], how="left")
    g = f.groupby("city", sort=False)
    wd = np.deg2rad(f["wind_direction_10m_previous_day1"])
    f["_u"] = f["wind_speed_10m_previous_day1"] * np.sin(wd)
    f["_v"] = f["wind_speed_10m_previous_day1"] * np.cos(wd)
    g = f.groupby("city", sort=False)
    for src, dst in (("precipitation_previous_day1", "fc_precip_t"),
                     ("wind_speed_10m_previous_day1", "fc_wind_t"),
                     ("_u", "fc_wind_u_t"), ("_v", "fc_wind_v_t")):
        f[dst] = g[src].shift(-h)
    # value at T - 24k for k = 1..7 is pm2_5 shifted by 24k - h (always >= 0 for h <= 24)
    f["pm2_5_samehour_7d"] = pd.concat(
        [g["pm2_5"].shift(24 * k - h) for k in range(1, 8)], axis=1).mean(axis=1)
    return f


def mae(y, p):
    return float(np.mean(np.abs(y - np.clip(p, 0, None))))


def main():
    df = pd.concat([pd.read_parquet(C.DATA / "history.parquet"),
                    pd.read_parquet(C.DATA / "unseen.parquet")]).reset_index(drop=True)
    test_end = df["time"].max()
    test_start = test_end - pd.Timedelta(days=365)
    w = prevday_weather(f"{df['time'].min():%Y-%m-%d}", f"{test_end:%Y-%m-%d}")
    arms = {"base": C.FEATURES, "a1": C.FEATURES + A1, "a2": C.FEATURES + A2,
            "a12": C.FEATURES + A1 + A2}
    res = {a: {} for a in arms}
    for h in C.HORIZONS:
        recipe = pickle.load(open(C.DATA / "models" / f"model_h{h}.pkl", "rb"))
        f = add_features(C.make_features(df, horizon=h), w, h)
        f = f.dropna(subset=["target", "pm2_5", "pm2_5_lag1"])
        tr = f[f["time"] + pd.Timedelta(hours=h) < test_start]
        te = f[f["time"] >= test_start]
        y = te["target"].values
        naive = mae(y, te["pm2_5"].values)
        cover = float(te["fc_wind_t"].notna().mean())
        for arm, cols in arms.items():
            maes = [mae(y, clone(recipe).set_params(random_state=s)
                        .fit(tr[cols], tr["target"]).predict(te[cols])) for s in SEEDS]
            m = float(np.mean(maes))
            res[arm][h] = {"seeds": [round(v, 4) for v in maes], "mean": round(m, 4),
                           "min": round(min(maes), 4), "max": round(max(maes), 4),
                           "naive": round(naive, 4),
                           "lift_pct": round(100 * (naive - m) / naive, 2)}
            print(f"  {h:>2}h {arm:<4} {m:.4f} [{min(maes):.4f}..{max(maes):.4f}] "
                  f"lift {res[arm][h]['lift_pct']:+.2f}%  (test fc coverage {cover:.1%})", flush=True)

    # decision rule, exactly as pre-registered
    b = res["base"]
    brange24 = b[24]["max"] - b[24]["min"]
    decisions = {}
    for arm in ("a1", "a2", "a12"):
        r = res[arm]
        gain = b[24]["mean"] - r[24]["mean"]
        noise = 3 * max(brange24, r[24]["max"] - r[24]["min"])
        wins24 = gain >= 0.02 * b[24]["mean"] and gain > noise
        worst_drop = max(b[h]["lift_pct"] - r[h]["lift_pct"] for h in (1, 6, 12))
        decisions[arm] = {"gain_24h": round(gain, 4), "needed_2pct": round(0.02 * b[24]["mean"], 4),
                          "needed_3x_noise": round(noise, 4), "wins_24h": bool(wins24),
                          "worst_other_drop_pts": round(worst_drop, 2),
                          "passes": bool(wins24 and worst_drop <= 2.0)}
    winners = [a for a, d in decisions.items() if d["passes"]]
    ship = min(winners, key=lambda a: res[a][24]["mean"]) if winners else None
    out = {"plan": "docs/ATTEMPT_NEXT.md", "test_period": f"{test_start:%Y-%m-%d}..{test_end:%Y-%m-%d}",
           "seeds": SEEDS, "results": {a: {str(h): v for h, v in r.items()} for a, r in res.items()},
           "decisions": decisions, "ship": ship}
    tmp = C.DATA / "attempt_24h.json.tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, C.DATA / "attempt_24h.json")
    print(json.dumps(decisions, indent=1))
    print("SHIP:", ship)


if __name__ == "__main__":
    main()
