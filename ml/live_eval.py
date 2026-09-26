"""
Hangin — out-of-sample check on data the model has never seen.

The shipped models were trained and tuned on 2022..2024. Everything from
2025-01-01 up to a week ago is new to them, so replaying the saved models over
that window is an honest "does it still work after launch?" test.

Writes data/live_eval.json. Run: python ml/live_eval.py  (add --refetch to
re-download; otherwise the fetched hours are cached in data/unseen.parquet).
"""
import json
import os
import pickle
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

import common as C

START = "2025-01-01"
END = str(date.today() - timedelta(days=7))  # weather archive lags ~5 days
CACHE = C.DATA / "unseen.parquet"


def load():
    if CACHE.exists() and "--refetch" not in sys.argv:
        return pd.read_parquet(CACHE)
    frames = []
    for city in C.CITIES:
        print(f"  fetching {city['name']} {START}..{END} ...")
        frames.append(C.fetch_history(city, START, END))
    df = pd.concat(frames).reset_index(drop=True)
    df.to_parquet(CACHE)
    return df


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def lift(model_mae, naive_mae):
    return round(100 * (naive_mae - model_mae) / naive_mae, 1)


def main():
    df = load()
    period = f"{df['time'].min():%Y-%m-%d}..{df['time'].max():%Y-%m-%d}"
    print(f"{len(df)} rows, {period}")
    names = {c["id"]: c["name"] for c in C.CITIES}

    horizons, by_city, by_month = [], [], []
    for h in C.HORIZONS:
        model = pickle.load(open(C.DATA / "models" / f"model_h{h}.pkl", "rb"))
        f = C.make_features(df, horizon=h).dropna(subset=["target", "pm2_5", "pm2_5_lag1"])
        f = f.assign(pred=np.clip(model.predict(f[C.FEATURES]), 0, None))
        m, n = mae(f["target"], f["pred"]), mae(f["target"], f["pm2_5"])
        horizons.append({"horizon_h": h, "n": len(f), "model_mae": round(m, 3),
                         "persistence_mae": round(n, 3), "lift_pct": lift(m, n)})
        print(f"  {h:>2}h  model {m:.3f}  naive {n:.3f}  lift {lift(m, n):+.1f}%  (n={len(f)})")
        for cid, g in f.groupby("city"):
            m, n = mae(g["target"], g["pred"]), mae(g["target"], g["pm2_5"])
            by_city.append({"horizon_h": h, "city": names[cid], "model_mae": round(m, 3),
                            "persistence_mae": round(n, 3), "lift_pct": lift(m, n)})
        for mon, g in f.groupby(f["time"].dt.strftime("%Y-%m")):
            m, n = mae(g["target"], g["pred"]), mae(g["target"], g["pm2_5"])
            by_month.append({"horizon_h": h, "month": mon, "n": len(g),
                             "lift_pct": lift(m, n)})

    out = {"period": period, "note": "saved models replayed on hours after training ended",
           "horizons": horizons, "by_city": by_city, "by_month": by_month}
    tmp = C.DATA / "live_eval.json.tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, C.DATA / "live_eval.json")
    print("wrote data/live_eval.json")


if __name__ == "__main__":
    main()
