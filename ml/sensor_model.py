"""
Hangin: Manila forecaster trained on real ground sensors, not CAMS.

Truth = hourly median of outdoor OpenAQ sensors within 25 km of Manila
(ground_truth.py). Train on 2024-08..2025-09-19, test on the walk-forward year.

Contenders, all scored against the sensors:
  persist   latest sensor reading ("same as now")
  yday      sensor reading 24h before the target ("same as yesterday this hour")
  cams      CAMS value for the target hour (archive; stands in for Open-Meteo's forecast)
  model_a   HGB on what is known now: sensor history, weather now, CAMS now
  model_b   model_a + CAMS value for the target hour. OPTIMISTIC: the archive holds
            CAMS's settled value, which can be better than the forecast issued at the time.

Needs OPENAQ_API_KEY. Writes data/sensor_model.json. Run: python ml/sensor_model.py
"""
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.base import clone

import common as C
import ground_truth as G

TRAIN_START = "2024-08-01"
WX = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_direction_10m",
      "precipitation", "boundary_layer_height", "surface_pressure"]
LAGS = (1, 2, 3, 6, 12, 24, 48)


def sensor_hourly(start, end):
    raw = G.fetch(start, end)
    raw = raw[(raw["pm2_5"] >= 0) & (raw["pm2_5"] < 500)]
    raw["time"] = pd.to_datetime(raw["utc"]).dt.tz_convert("Asia/Manila").dt.tz_localize(None)
    per = raw.groupby("time").agg(g=("pm2_5", "median"), n=("sensor", "nunique"))
    return per.loc[per["n"] >= 3, "g"]


def frame():
    start, end = json.load(open(C.DATA / "walkforward.json"))["test_period"].split("..")
    g = pd.concat([sensor_hourly(TRAIN_START, start), sensor_hourly(start, end)])
    g = g[~g.index.duplicated()].sort_index()
    cams = pd.concat([pd.read_parquet(C.DATA / "history.parquet"),
                      pd.read_parquet(C.DATA / "unseen.parquet")])
    cams = cams[cams["city"] == "manila"].drop_duplicates("time").set_index("time")
    idx = pd.date_range(g.index.min(), g.index.max(), freq="h")
    df = pd.DataFrame(index=idx)
    df["g"] = g.reindex(idx)
    df["cams"] = cams["pm2_5"].reindex(idx)
    for c in WX:
        df[c] = cams[c].reindex(idx)
    return df, pd.Timestamp(start)


def features(df):
    f = pd.DataFrame(index=df.index)
    f["g_now"] = df["g"]
    for l in LAGS:
        f[f"g_lag{l}"] = df["g"].shift(l)
    f["g_roll6"] = df["g"].rolling(6, min_periods=3).mean()
    f["g_roll24"] = df["g"].rolling(24, min_periods=12).mean()
    f["g_std24"] = df["g"].rolling(24, min_periods=12).std()
    f["cams_now"] = df["cams"]
    f["cams_lag24"] = df["cams"].shift(24)
    for c in WX:
        f[c] = df[c]
    t = df.index
    for name, val, per in (("hour", t.hour, 24), ("dow", t.dayofweek, 7), ("month", t.month, 12)):
        f[f"{name}_sin"] = np.sin(2 * np.pi * val / per)
        f[f"{name}_cos"] = np.cos(2 * np.pi * val / per)
    return f


def mae(y, p):
    ok = ~(np.isnan(y) | np.isnan(p))
    return round(float(np.mean(np.abs(y[ok] - p[ok]))), 3), int(ok.sum())


def main():
    df, test_start = frame()
    print(f"sensor hours: {df['g'].notna().sum()} ({df.index.min():%Y-%m-%d}..{df.index.max():%Y-%m-%d}); "
          f"test from {test_start:%Y-%m-%d}")
    base = features(df)
    rows = []
    for h in C.HORIZONS:
        f = base.copy()
        f["target"] = df["g"].shift(-h)
        f["cams_target"] = df["cams"].shift(-h)
        f["yday"] = df["g"].shift(24 - h)  # value 24h before the target: known at t when h <= 24
        f = f[f["target"].notna() & f["g_now"].notna()]
        tr = f[f.index + pd.Timedelta(hours=h) < test_start]
        te = f[f.index >= test_start]
        cols_a = [c for c in base.columns]
        cols_b = cols_a + ["cams_target"]
        recipe = clone(pickle.load(open(C.DATA / "models" / f"model_h{h}.pkl", "rb"))).set_params(
            categorical_features=None, random_state=0)
        pa = clone(recipe).fit(tr[cols_a], tr["target"]).predict(te[cols_a])
        pb = clone(recipe).fit(tr[cols_b], tr["target"]).predict(te[cols_b])
        y = te["target"].values
        r = {"horizon_h": h, "n_train": len(tr), "n_test": len(te)}
        for name, p in (("persist", te["g_now"].values), ("yday", te["yday"].values),
                        ("cams", te["cams_target"].values), ("model_a", np.clip(pa, 0, None)),
                        ("model_b", np.clip(pb, 0, None))):
            r[f"{name}_mae"], r[f"{name}_n"] = mae(y, p)
        best = min(r["persist_mae"], r["yday_mae"], r["cams_mae"])
        r["model_a_vs_best_baseline_pct"] = round(100 * (best - r["model_a_mae"]) / best, 1)
        rows.append(r)
        print(f"  {h:>2}h n_test={len(te)}  persist {r['persist_mae']}  yday {r['yday_mae']}  "
              f"cams {r['cams_mae']}  | model_a {r['model_a_mae']}  model_b {r['model_b_mae']}  "
              f"(A vs best baseline {r['model_a_vs_best_baseline_pct']:+}%)")

    out = {"truth": "hourly median of >=3 outdoor OpenAQ sensors within 25 km of Manila",
           "train": f"{TRAIN_START}..{test_start:%Y-%m-%d}", "test_from": f"{test_start:%Y-%m-%d}",
           "note": "model_b and cams use CAMS archive values for the target hour: optimistic",
           "horizons": rows}
    tmp = C.DATA / "sensor_model.json.tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, C.DATA / "sensor_model.json")


if __name__ == "__main__":
    main()
