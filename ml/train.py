"""
Hangin — train pooled multi-horizon PM2.5 forecasters (1/6/12/24h).

Fetches ~3 years of history for 5 PH metros, pools them into one dataset with
location features, and trains one HistGradientBoosting model per horizon.
Backtests each on a chronological holdout against a naive persistence baseline
and saves models + data/backtest.json for the dashboard.
"""
import json
import pickle

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, r2_score

import common as C

START, END = "2022-01-01", "2024-12-31"
MODELS_DIR = C.DATA / "models"


def load_all():
    frames = []
    for city in C.CITIES:
        print(f"  fetching {city['name']} ...")
        frames.append(C.fetch_history(city, START, END))
    df = pd.concat(frames).reset_index(drop=True)
    df.to_parquet(C.DATA / "history.parquet")
    return df


def train_horizon(df, horizon):
    feat = C.make_features(df, horizon=horizon).dropna(
        subset=["target", "pm2_5", "pm2_5_lag1"]).reset_index(drop=True)
    # chronological split by time (last 20% across all cities)
    cutoff = feat["time"].quantile(0.8)
    tr = feat[feat["time"] <= cutoff]
    te = feat[feat["time"] > cutoff]
    Xtr, ytr = tr[C.FEATURES], tr["target"]
    Xte, yte = te[C.FEATURES], te["target"]

    model = HistGradientBoostingRegressor(
        max_iter=600, learning_rate=0.05, max_depth=8,
        l2_regularization=1.0, early_stopping=True, random_state=42,
        categorical_features=C.CAT_IDX)
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    persistence = te["pm2_5"].values

    res = {
        "horizon_h": horizon,
        "n_train": int(len(tr)), "n_test": int(len(te)),
        "model_mae": round(float(mean_absolute_error(yte, pred)), 3),
        "model_r2": round(float(r2_score(yte, pred)), 4),
        "persistence_mae": round(float(mean_absolute_error(yte, persistence)), 3),
    }
    res["lift_pct"] = round(
        100 * (res["persistence_mae"] - res["model_mae"]) / res["persistence_mae"], 1)
    return model, res


def main():
    C.DATA.mkdir(exist_ok=True)
    MODELS_DIR.mkdir(exist_ok=True)
    print("Loading history for 5 metros ...")
    df = load_all()
    print(f"  {len(df)} total rows\n")

    all_res = []
    for h in C.HORIZONS:
        print(f"Training horizon {h}h ...")
        model, res = train_horizon(df, h)
        pickle.dump(model, open(MODELS_DIR / f"model_h{h}.pkl", "wb"))
        print(f"  MAE={res['model_mae']:.3f}  R2={res['model_r2']:.4f}  "
              f"persist={res['persistence_mae']:.3f}  (+{res['lift_pct']}% vs naive)")
        all_res.append(res)

    meta = {
        "cities": [c["name"] for c in C.CITIES],
        "train_period": f"{START}..{END}",
        "features": C.FEATURES,
        "horizons": all_res,
    }
    json.dump(meta, open(C.DATA / "backtest.json", "w"), indent=2)
    print(f"\nsaved models -> {MODELS_DIR}")
    print(f"saved backtest -> {C.DATA/'backtest.json'}")


if __name__ == "__main__":
    main()
