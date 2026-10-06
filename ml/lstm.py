"""
Hangin: does an LSTM beat the shipped HistGradientBoosting forecaster?
Plan and win rule: docs/LSTM_PLAN.md (written before any result).

Same full-year test as walkforward.py: the last 365 days of history + unseen,
the same purge (a training target must land before the test year), the same
MAE, scored on the same test rows. The LSTM reads the last 48 hours of raw
readings (no hand-made lags or rolling means) and predicts 1/6/12/24 h at once.

  pip install -r requirements-lstm.txt
  python ml/lstm.py --smoke    # 1 seed, 1 epoch, a few minutes: catches crashes first
  python ml/lstm.py            # 3 seeds, about 20 min on CPU -> data/lstm.json
  python ml/lstm.py --delta    # run 2: predict the change from now -> data/lstm_delta.json
"""
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import torch
import torch.nn as nn

import common as C

SEEDS = [0, 1, 2]
SMOKE = "--smoke" in sys.argv  # 1 seed, 1 epoch, nothing written: checks the code runs end to end
# --delta: learn the change from the current reading instead of the level, so
# "air stays the same" is the starting point rather than something to rediscover
DELTA = "--delta" in sys.argv
OUT = "lstm_delta.json" if DELTA else "lstm.json"
WINDOW = 48                 # hours of history the network sees
VAL_DAYS = 60               # early-stopping block, just before the test year
EPOCHS, PATIENCE, BATCH = (1, 4, 512) if SMOKE else (30, 4, 512)
if SMOKE:
    SEEDS = [0]
H = C.HORIZONS              # [1, 6, 12, 24]
# raw hourly inputs only; wind and time come pre-encoded from make_features
INPUTS = ["pm2_5", "pm10", "carbon_monoxide", "nitrogen_dioxide", "ozone", "sulphur_dioxide",
          "temperature_2m", "relative_humidity_2m", "wind_speed_10m", "wind_dir_sin", "wind_dir_cos",
          "precipitation", "surface_pressure", "boundary_layer_height",
          "hour_sin", "hour_cos", "dow_sin", "dow_cos", "month_sin", "month_cos", "is_fireworks"]


class Net(nn.Module):
    def __init__(self, n_in, n_city):
        super().__init__()
        self.city = nn.Embedding(n_city, 4)
        self.lstm = nn.LSTM(n_in + 4, 64, batch_first=True)
        self.head = nn.Linear(64, len(H))

    def forward(self, x, city):
        c = self.city(city)[:, None, :].expand(-1, x.shape[1], -1)
        out, _ = self.lstm(torch.cat([x, c], dim=2))
        return self.head(out[:, -1])


def build():
    """One long array of hours (cities back to back), plus which rows can be samples."""
    df = pd.concat([pd.read_parquet(C.DATA / "history.parquet"),
                    pd.read_parquet(C.DATA / "unseen.parquet")]).reset_index(drop=True)
    test_start = df["time"].max() - pd.Timedelta(days=365)
    f = C.make_features(df).sort_values(["city", "time"]).reset_index(drop=True)
    # windows assume back-to-back hours inside each city
    step = f.groupby("city")["time"].diff().dropna()
    assert (step == pd.Timedelta(hours=1)).all(), "gap or duplicate hour inside a city"
    cities = sorted(f["city"].unique())
    f["cid"] = f["city"].map({c: i for i, c in enumerate(cities)})
    X = f[INPUTS].to_numpy(np.float32)
    # targets per horizon, shifted inside each city so they never cross cities
    Y = np.stack([f.groupby("city")["pm2_5"].shift(-h).to_numpy(np.float32) for h in H], axis=1)
    pos = f.groupby("city").cumcount().to_numpy()
    ok_window = pos >= WINDOW - 1
    # a sample needs a complete 48 h window: count NaN rows in the trailing window
    bad = np.isnan(X).any(axis=1).astype(np.int32)
    run = pd.Series(bad).groupby(f["city"]).transform(lambda s: s.rolling(WINDOW, min_periods=1).sum()).to_numpy()
    ok = ok_window & (run == 0)
    return f, X, Y, ok, test_start, cities


def main():
    t0 = time.perf_counter()
    f, X, Y, ok, test_start, cities = build()
    t = f["time"]
    val_start = test_start - pd.Timedelta(days=VAL_DAYS)
    last_h = pd.Timedelta(hours=max(H))
    # purge: every target of a train/val sample lands before the next block starts
    tr_idx = np.where(ok & (t + last_h < val_start) & ~np.isnan(Y).any(axis=1))[0]
    va_idx = np.where(ok & (t >= val_start) & (t + last_h < test_start) & ~np.isnan(Y).any(axis=1))[0]
    te_idx = np.where(ok & (t >= test_start))[0]
    assert t.iloc[tr_idx].max() + last_h < val_start and t.iloc[va_idx].max() + last_h < test_start
    assert t.iloc[te_idx].min() >= test_start

    # scaling fit on training rows only (each row's own hour; windows reuse it)
    mu = X[tr_idx].mean(axis=0)
    sd = X[tr_idx].std(axis=0) + 1e-6
    Xs = torch.from_numpy(np.nan_to_num((X - mu) / sd))
    y_mu, y_sd = float(mu[0]), float(sd[0])           # pm2_5 is INPUTS[0]
    cur = X[:, :1]                                     # PM2.5 now, the persistence guess
    base = cur if DELTA else np.full_like(cur, y_mu)
    Yt = torch.from_numpy(np.nan_to_num((Y - base) / y_sd))
    cid = torch.from_numpy(f["cid"].to_numpy(np.int64))
    offs = torch.arange(-WINDOW + 1, 1)

    def batch(idx):
        idx = torch.as_tensor(idx)
        return Xs[idx[:, None] + offs], cid[idx], Yt[idx]

    def predict(model, idx):
        model.eval()
        out = []
        with torch.no_grad():
            for i in range(0, len(idx), 4096):
                x, c, _ = batch(idx[i:i + 4096])
                out.append(model(x, c))
        return torch.cat(out).numpy() * y_sd + base[idx]

    print(f"train {len(tr_idx):,}  val {len(va_idx):,}  test {len(te_idx):,}  "
          f"(test {test_start:%Y-%m-%d}..)  build {time.perf_counter() - t0:.0f}s")

    runs = []
    for seed in SEEDS:
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        model = Net(len(INPUTS), len(cities))
        opt = torch.optim.Adam(model.parameters(), lr=1e-3)
        best, best_state, wait = np.inf, None, 0
        for ep in range(EPOCHS):
            model.train()
            order = rng.permutation(tr_idx)
            for i in range(0, len(order), BATCH):
                x, c, y = batch(order[i:i + BATCH])
                opt.zero_grad()
                nn.functional.l1_loss(model(x, c), y).backward()
                opt.step()
            val = float(np.mean(np.abs(predict(model, va_idx) - Y[va_idx])))
            if val < best - 1e-4:
                best, best_state, wait = val, {k: v.clone() for k, v in model.state_dict().items()}, 0
            else:
                wait += 1
            print(f"  seed {seed} epoch {ep + 1:2}  val MAE {val:.3f}{'  *' if wait == 0 else ''}", flush=True)
            if wait >= PATIENCE:
                break
        model.load_state_dict(best_state)
        pred = np.clip(predict(model, te_idx), 0, None)
        maes = {}
        for k, h in enumerate(H):
            # score exactly the rows walkforward.py scores: target, pm2_5 and lag1 present
            lag1 = f.groupby("city")["pm2_5"].shift(1).to_numpy()[te_idx]
            m = ~np.isnan(Y[te_idx, k]) & ~np.isnan(X[te_idx, 0]) & ~np.isnan(lag1)
            maes[h] = (float(np.mean(np.abs(pred[m, k] - Y[te_idx, k][m]))), int(m.sum()))
        runs.append({"seed": seed, "epochs": ep + 1, "val_mae": round(best, 4),
                     "test_mae": {str(h): round(v[0], 4) for h, v in maes.items()},
                     "n_test": {str(h): v[1] for h, v in maes.items()}})
        print(f"  seed {seed} test MAE " + "  ".join(f"{h}h {v[0]:.3f}" for h, v in maes.items()), flush=True)

    wf = {r["horizon_h"]: r for r in json.load(open(C.DATA / "walkforward.json"))["horizons"]}
    rows = []
    for h in H:
        v = [r["test_mae"][str(h)] for r in runs]
        g = wf[h]
        n = runs[0]["n_test"][str(h)]
        assert n == g["n_test"], f"{h}h scores {n} rows, walkforward scored {g['n_test']}"
        margin = max(float(np.std(v)), g["retrained_mae_std"])
        verdict = ("win" if g["retrained_mae_mean"] - np.mean(v) > margin
                   else "loss" if np.mean(v) - g["retrained_mae_mean"] > margin else "tie")
        rows.append({"horizon_h": h, "n_test": n, "naive_mae": g["naive_mae"],
                     "gbm_mae_mean": g["retrained_mae_mean"], "gbm_mae_std": g["retrained_mae_std"],
                     "lstm_mae_mean": round(float(np.mean(v)), 3), "lstm_mae_std": round(float(np.std(v)), 3),
                     "lstm_mae_seeds": [round(x, 3) for x in v], "verdict": verdict})
        print(f"{h:>2}h  naive {g['naive_mae']:.3f} | GBM {g['retrained_mae_mean']:.3f} ± {g['retrained_mae_std']:.3f} | "
              f"LSTM {np.mean(v):.3f} ± {np.std(v):.3f}  -> {verdict}  (n={n:,})")

    if SMOKE:
        print("smoke run ok, nothing written")
        return
    out = {"test_period": f"{test_start:%Y-%m-%d}..", "window_h": WINDOW, "seeds": SEEDS, "delta": DELTA,
           "inputs": INPUTS, "runs": runs, "horizons": rows,
           "minutes": round((time.perf_counter() - t0) / 60, 1)}
    tmp = C.DATA / (OUT + ".tmp")
    json.dump(out, open(tmp, "w"), indent=1)
    os.replace(tmp, C.DATA / OUT)
    print(f"wrote data/{OUT} in {out['minutes']} min")


if __name__ == "__main__":
    sys.exit(main())
