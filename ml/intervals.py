"""
Hangin — does an 80% forecast band actually catch reality 80% of the time?

Trains 10th- and 90th-percentile (quantile loss) models with the shipped
recipe on hours before the test year, then measures on the test year how often
the real value landed inside [q10, q90] ("coverage", target 80%) and how wide
the band is. Same split as walkforward.py.

Writes data/intervals.json. Run: python ml/intervals.py
"""
import json
import os
import pickle

import numpy as np
import pandas as pd
from sklearn.base import clone

import common as C

QS = (0.1, 0.9)


def main():
    df = pd.concat([pd.read_parquet(C.DATA / "history.parquet"),
                    pd.read_parquet(C.DATA / "unseen.parquet")]).reset_index(drop=True)
    test_end = df["time"].max()
    test_start = test_end - pd.Timedelta(days=365)

    rows = []
    for h in C.HORIZONS:
        base = pickle.load(open(C.DATA / "models" / f"model_h{h}.pkl", "rb"))
        f = C.make_features(df, horizon=h).dropna(subset=["target", "pm2_5", "pm2_5_lag1"])
        # calibration slice = the 90 days just before the test year (conformal step)
        cal_start = test_start - pd.Timedelta(days=90)
        tr = f[f["time"] + pd.Timedelta(hours=h) < cal_start]
        cal = f[(f["time"] >= cal_start) & (f["time"] + pd.Timedelta(hours=h) < test_start)]
        te = f[f["time"] >= test_start]
        qm = [clone(base).set_params(loss="quantile", quantile=q, random_state=0)
              .fit(tr[C.FEATURES], tr["target"]) for q in QS]
        # how far outside the raw band calibration hours fall; widen by the 80th pct of that
        clo, chi = (m.predict(cal[C.FEATURES]) for m in qm)
        miss = np.maximum(clo - cal["target"].values, cal["target"].values - chi)
        margin = float(np.quantile(miss, 0.8))
        raw_lo, raw_hi = (m.predict(te[C.FEATURES]) for m in qm)
        lo, hi = np.clip(raw_lo - margin, 0, None), raw_hi + margin
        y = te["target"].values
        raw_cov = round(100 * float(np.mean((y >= raw_lo) & (y <= raw_hi))), 1)
        r = {"horizon_h": h, "n_test": len(te),
             "raw_coverage_pct": raw_cov, "margin": round(margin, 3),
             "coverage_pct": round(100 * float(np.mean((y >= lo) & (y <= hi))), 1),
             "below_pct": round(100 * float(np.mean(y < lo)), 1),
             "above_pct": round(100 * float(np.mean(y > hi)), 1),
             "median_width": round(float(np.median(hi - lo)), 2)}
        rows.append(r)
        print(f"  {h:>2}h raw {raw_cov}% -> calibrated {r['coverage_pct']}% (below {r['below_pct']}%, "
              f"above {r['above_pct']}%), median width {r['median_width']} µg/m³")

    out = {"test_period": f"{test_start:%Y-%m-%d}..{test_end:%Y-%m-%d}",
           "band": "10th..90th percentile, conformally widened on the 90 days before the test year", "horizons": rows}
    tmp = C.DATA / "intervals.json.tmp"
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, C.DATA / "intervals.json")


if __name__ == "__main__":
    main()
