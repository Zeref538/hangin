"""
Hangin: monthly retrain with a ship gate.

Why: a model trained once goes stale (walkforward.py: the 2024 model's 1h lead
fell from +26% to +3% on the next year; the same recipe retrained got it back).

Per horizon, on history 2022-01-01 .. a week ago:
  gate window  = last 30 days      -> candidate must beat the live model here
  cal window   = 90 days before it -> conformal margin for the 80% band
  training     = everything before the window it is scored on (purged by h)
Ships models/model_h{h}.pkl, q10/q90 models and models/meta.json only if the
candidate beats the live model on average and no horizon is >2% worse. Exit code 3 = kept old.

Run: python ml/refit.py   (reads + writes data/models/)
"""
import json
import os
import pickle
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sklearn.base import clone

import common as C

MODELS = C.DATA / "models"
START = "2022-01-01"
END = str(date.today() - timedelta(days=7))  # weather archive lags ~5 days
GATE_DAYS, CAL_DAYS = 30, 90
QS = (0.1, 0.9)
TOLERANCE = 0.02  # a single horizon may be up to 2% worse


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def before(f, t, h):
    """Rows whose target (time + h) is known strictly before t, so no peeking."""
    return f[f["time"] + pd.Timedelta(hours=h) < t]


def main():
    df = pd.concat([C.fetch_history(c, START, END) for c in C.CITIES]).reset_index(drop=True)
    end = df["time"].max()
    gate_start = end - pd.Timedelta(days=GATE_DAYS)
    cal_start = gate_start - pd.Timedelta(days=CAL_DAYS)
    print(f"{len(df)} rows through {end:%Y-%m-%d}; gate from {gate_start:%Y-%m-%d}")

    new, report = {}, []
    for h in C.HORIZONS:
        live = pickle.load(open(MODELS / f"model_h{h}.pkl", "rb"))
        f = C.make_features(df, horizon=h).dropna(subset=["target", "pm2_5", "pm2_5_lag1"])
        gate = f[f["time"] >= gate_start]
        cal = before(f[f["time"] >= cal_start], gate_start, h)

        cand = clone(live).set_params(random_state=0).fit(
            before(f, gate_start, h)[C.FEATURES], before(f, gate_start, h)["target"])
        y = gate["target"].values
        c_mae = mae(y, np.clip(cand.predict(gate[C.FEATURES]), 0, None))
        l_mae = mae(y, np.clip(live.predict(gate[C.FEATURES]), 0, None))
        n_mae = mae(y, gate["pm2_5"])

        tr = before(f, cal_start, h)
        qm = [clone(live).set_params(loss="quantile", quantile=q, random_state=0)
              .fit(tr[C.FEATURES], tr["target"]) for q in QS]
        lo, hi = (m.predict(cal[C.FEATURES]) for m in qm)
        miss = np.maximum(lo - cal["target"].values, cal["target"].values - hi)
        margin = float(np.quantile(miss, 0.8))

        new[h] = (cand, *qm)
        report.append({"horizon_h": h, "gate_n": len(gate), "candidate_mae": round(c_mae, 3),
                       "live_mae": round(l_mae, 3), "naive_mae": round(n_mae, 3),
                       "band_margin": round(margin, 3)})
        print(f"  {h:>2}h candidate {c_mae:.3f} vs live {l_mae:.3f} (naive {n_mae:.3f}); "
              f"band margin {margin:.2f}")

    # ship if better on average and no horizon more than TOLERANCE worse; a strict
    # "no worse anywhere" rule blocks near-ties by noise and lets the model go stale
    worst = max(r["candidate_mae"] / r["live_mae"] for r in report)
    better = sum(r["candidate_mae"] for r in report) <= sum(r["live_mae"] for r in report)
    if not (better and worst <= 1 + TOLERANCE):
        print(f"gate failed (better on average: {better}, worst horizon ratio {worst:.3f}) -> keeping old models")
        sys.exit(3)

    # write everything to .tmp first, then swap in, so a crash never leaves a mixed set
    files = {}
    for h, (cand, q10, q90) in new.items():
        for name, m in ((f"model_h{h}", cand), (f"q10_h{h}", q10), (f"q90_h{h}", q90)):
            tmp = MODELS / f"{name}.pkl.tmp"
            pickle.dump(m, open(tmp, "wb"))
            files[tmp] = MODELS / f"{name}.pkl"
    meta = {"n_rows": len(df), "data_start": f"{df['time'].min():%Y-%m-%d}",
            "trained_through": f"{gate_start:%Y-%m-%d}", "data_end": f"{end:%Y-%m-%d}",
            "band": "10th..90th percentile + conformal margin (target 80% coverage)",
            "margins": {str(r["horizon_h"]): r["band_margin"] for r in report},
            "gate": report}
    tmp = MODELS / "meta.json.tmp"
    json.dump(meta, open(tmp, "w"), indent=1)
    files[tmp] = MODELS / "meta.json"
    for src, dst in files.items():
        os.replace(src, dst)
    print("shipped new models -> data/models/")


if __name__ == "__main__":
    main()
