"""
Hangin — long-running hyperparameter search for the PM2.5 forecasters.

For each horizon (1/6/12/24h):
  - chronological split: 60% train / 20% validation / 20% final test
  - random search over HistGradientBoostingRegressor space, scored on val MAE
  - best config refit on train+val, scored once on the untouched test tail
  - the production model in data/models/ is replaced ONLY if the tuned model
    beats the current backtest MAE on that same test tail

Progress is printed per trial; full log saved to data/tuning.json.
Run: python ml/tune.py  (expect 1.5–3 hours)
"""
import json
import pickle
import random
import time

import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

import common as C

N_TRIALS = 40
SEED = 42
MODELS_DIR = C.DATA / "models"

SPACE = {
    "learning_rate": [0.02, 0.03, 0.05, 0.08, 0.12],
    "max_iter": [400, 800, 1200, 2000],
    "max_depth": [None, 6, 8, 10, 12],
    "max_leaf_nodes": [31, 63, 127, 255],
    "min_samples_leaf": [10, 20, 40, 80],
    "l2_regularization": [0.0, 0.1, 1.0, 5.0, 10.0],
    "max_features": [1.0, 0.8, 0.6],
}


def sample_params(rng):
    return {k: rng.choice(v) for k, v in SPACE.items()}


def load_history():
    path = C.DATA / "history.parquet"
    if path.exists():
        print(f"using cached {path}")
        return pd.read_parquet(path)
    print("fetching 3y history for 5 metros ...")
    frames = [C.fetch_history(c, "2022-01-01", "2024-12-31") for c in C.CITIES]
    df = pd.concat(frames).reset_index(drop=True)
    df.to_parquet(path)
    return df


def tune_horizon(df, horizon, current_mae, rng):
    feat = C.make_features(df, horizon=horizon).dropna(
        subset=C.FEATURES + ["target"]).reset_index(drop=True)
    t60 = feat["time"].quantile(0.6)
    t80 = feat["time"].quantile(0.8)
    tr = feat[feat["time"] <= t60]
    va = feat[(feat["time"] > t60) & (feat["time"] <= t80)]
    te = feat[feat["time"] > t80]
    Xtr, ytr = tr[C.FEATURES], tr["target"]
    Xva, yva = va[C.FEATURES], va["target"]

    print(f"\n=== horizon {horizon}h: {len(tr)} train / {len(va)} val / {len(te)} test "
          f"(current prod MAE {current_mae}) ===", flush=True)

    trials, best = [], None
    for i in range(N_TRIALS):
        params = sample_params(rng)
        t0 = time.time()
        model = HistGradientBoostingRegressor(
            random_state=SEED, early_stopping=True,
            validation_fraction=0.1, n_iter_no_change=30, **params)
        model.fit(Xtr, ytr)
        mae = mean_absolute_error(yva, model.predict(Xva))
        secs = time.time() - t0
        trials.append({"params": {k: (None if v is None else v) for k, v in params.items()},
                       "val_mae": round(float(mae), 4), "fit_seconds": round(secs, 1),
                       "n_iter": int(model.n_iter_)})
        tag = ""
        if best is None or mae < best["val_mae"]:
            best = trials[-1]
            tag = "  <-- best so far"
        print(f"  h{horizon} trial {i+1:02d}/{N_TRIALS} val_MAE={mae:.4f} "
              f"({secs:.0f}s, {model.n_iter_} iters) {params}{tag}", flush=True)

    # refit winner on train+val, judge once on the untouched test tail
    print(f"  refitting best config on train+val ...", flush=True)
    Xfull = pd.concat([Xtr, Xva]); yfull = pd.concat([ytr, yva])
    final = HistGradientBoostingRegressor(
        random_state=SEED, early_stopping=True,
        validation_fraction=0.1, n_iter_no_change=30, **best["params"])
    final.fit(Xfull, yfull)
    pred = final.predict(te[C.FEATURES])
    test_mae = float(mean_absolute_error(te["target"], pred))
    test_r2 = float(r2_score(te["target"], pred))
    persistence = float(mean_absolute_error(te["target"], te["pm2_5"]))
    improved = test_mae < current_mae

    print(f"  h{horizon} FINAL test MAE {test_mae:.4f} (prod {current_mae}) "
          f"R2 {test_r2:.4f} persistence {persistence:.4f} -> "
          f"{'REPLACING prod model' if improved else 'keeping prod model'}", flush=True)

    result = {
        "horizon_h": horizon, "best_params": best["params"],
        "val_mae": best["val_mae"],
        "test_mae": round(test_mae, 4), "test_r2": round(test_r2, 4),
        "persistence_mae": round(persistence, 4),
        "prod_mae_before": current_mae, "replaced": improved,
        "trials": trials,
    }
    if improved:
        pickle.dump(final, open(MODELS_DIR / f"model_h{horizon}.pkl", "wb"))
        result["backtest_row"] = {
            "horizon_h": horizon,
            "n_train": int(len(Xfull)), "n_test": int(len(te)),
            "model_mae": round(test_mae, 3), "model_r2": round(test_r2, 4),
            "persistence_mae": round(persistence, 3),
            "lift_pct": round(100 * (persistence - test_mae) / persistence, 1),
        }
    return result


def main():
    rng = random.Random(SEED)
    df = load_history()
    backtest = json.load(open(C.DATA / "backtest.json"))
    current = {h["horizon_h"]: h["model_mae"] for h in backtest["horizons"]}

    t0 = time.time()
    results = []
    for h in C.HORIZONS:
        results.append(tune_horizon(df, h, current[h], rng))

    # fold improvements back into backtest.json
    for res in results:
        if res["replaced"]:
            for i, row in enumerate(backtest["horizons"]):
                if row["horizon_h"] == res["horizon_h"]:
                    backtest["horizons"][i] = res["backtest_row"]
    backtest["tuned"] = True
    json.dump(backtest, open(C.DATA / "backtest.json", "w"), indent=2)
    json.dump({"seed": SEED, "n_trials": N_TRIALS,
               "total_minutes": round((time.time() - t0) / 60, 1),
               "results": [{k: v for k, v in r.items() if k != "trials"} for r in results],
               "all_trials": results},
              open(C.DATA / "tuning.json", "w"), indent=2)

    print(f"\nDone in {(time.time()-t0)/60:.0f} min. "
          f"Replaced: {[r['horizon_h'] for r in results if r['replaced']]}")
    print("Now re-run: python ml/forecast.py  (and rebuild web) if any model changed.")


if __name__ == "__main__":
    main()
