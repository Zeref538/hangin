"""
Hangin — full-year test: shipped models vs the same recipe retrained on newer data.

Test year = the last 12 months in data/unseen.parquet (run live_eval.py first).
Every season is in it, so no horizon gets flattered by an easy test window.

  shipped    saved models (trained on 2022..2024), untouched
  retrained  same hyperparameters (sklearn clone), trained on all hours before
             the test year, 3 seeds -> mean and spread
  naive      "air stays the same" persistence

Writes data/walkforward.json. Run: python ml/walkforward.py
"""
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.base import clone

import common as C

SEEDS = [0, 1, 2]


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def main():
    df = pd.concat([pd.read_parquet(C.DATA / "history.parquet"),
                    pd.read_parquet(C.DATA / "unseen.parquet")]).reset_index(drop=True)
    test_end = df["time"].max()
    test_start = test_end - pd.Timedelta(days=365)
    print(f"test year {test_start:%Y-%m-%d}..{test_end:%Y-%m-%d}")

    rows = []
    for h in C.HORIZONS:
        shipped = pickle.load(open(C.DATA / "models" / f"model_h{h}.pkl", "rb"))
        f = C.make_features(df, horizon=h).dropna(subset=["target", "pm2_5", "pm2_5_lag1"])
        # purge: a train row's target (t+h) must not land inside the test year
        tr = f[f["time"] + pd.Timedelta(hours=h) < test_start]
        te = f[f["time"] >= test_start]
        y = te["target"].values

        naive = mae(y, te["pm2_5"])
        ship = mae(y, np.clip(shipped.predict(te[C.FEATURES]), 0, None))
        seed_maes = []
        for s in SEEDS:
            m = clone(shipped).set_params(random_state=s)
            m.fit(tr[C.FEATURES], tr["target"])
            seed_maes.append(mae(y, np.clip(m.predict(te[C.FEATURES]), 0, None)))
            if s == SEEDS[0]:
                pickle.dump(m, open(C.DATA / "models" / f"retrained_h{h}.pkl", "wb"))
        r = {"horizon_h": h, "n_train": len(tr), "n_test": len(te),
             "naive_mae": round(naive, 3), "shipped_mae": round(ship, 3),
             "retrained_mae_mean": round(float(np.mean(seed_maes)), 3),
             "retrained_mae_std": round(float(np.std(seed_maes)), 3),
             "retrained_mae_seeds": [round(v, 3) for v in seed_maes]}
        r["shipped_lift_pct"] = round(100 * (naive - ship) / naive, 1)
        r["retrained_lift_pct"] = round(100 * (naive - r["retrained_mae_mean"]) / naive, 1)
        rows.append(r)
        print(f"  {h:>2}h naive {naive:.3f} | shipped {ship:.3f} ({r['shipped_lift_pct']:+.1f}%) | "
              f"retrained {r['retrained_mae_mean']:.3f} ± {r['retrained_mae_std']:.3f} "
              f"({r['retrained_lift_pct']:+.1f}%)")

    out = {"test_period": f"{test_start:%Y-%m-%d}..{test_end:%Y-%m-%d}", "seeds": SEEDS,
           "horizons": rows}
    tmp = C.DATA / "walkforward.json.tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, C.DATA / "walkforward.json")
    print("wrote data/walkforward.json")


if __name__ == "__main__":
    main()
