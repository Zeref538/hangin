# Experiments

One row per run. Scores are test MAE in µg/m³ (lower is better), mean ± spread over the listed seeds, as 1h / 6h / 12h / 24h.

## Section A: LSTM vs HistGradientBoosting (plan: `docs/LSTM_PLAN.md`)

Split: walk-forward from `ml/walkforward.py`. Test year 2025-09-20 to 2026-09-20 from `history.parquet` + `unseen.parquet`, 5 cities. n = 43,800 / 43,775 / 43,745 / 43,685 test rows. Training targets must land before the test year. The LSTM's early-stopping block is the 60 days before the test year.

| # | date | data | change from best | settings | score (1h / 6h / 12h / 24h) | n | seed | code | verdict |
|---|---|---|---|---|---|---|---|---|---|
| 0 | 2026-09-27 | history + unseen | baseline: shipped HistGradientBoosting recipe, retrained | 43 hand-made features, one model per horizon | 0.928 ± 0.001 / 3.172 ± 0.002 / 3.811 ± 0.001 / 4.092 ± 0.003 | 43,685 to 43,800 | 0, 1, 2 | `0a30e5c` (`data/walkforward.json`) | best |
| 1 | 2026-10-07 | same | LSTM on 48 h of raw readings, predicts the PM2.5 level | 1 layer, 64 units, L1 loss, Adam 1e-3, batch 512, early stop (patience 4), stopped at epoch 8 | 1.198 ± 0.009 / 3.370 ± 0.010 / 3.972 ± 0.016 / 4.193 ± 0.016 | same | 0, 1, 2 | `6d0a166` (`data/lstm.json`) | loss at every horizon; beats naive at every horizon |
| 2 | 2026-10-07 | same | run 1, but the LSTM predicts the change from the current reading (`--delta`) | as run 1 | 1.143 ± 0.006 / 3.374 ± 0.024 / 3.983 ± 0.025 / 4.203 ± 0.045 | same | 0, 1, 2 | `2fb5170` (`data/lstm_delta.json`) | best LSTM: better than run 1 at 1h, tie at 6/12/24h; still a loss to row 0 at every horizon |

**Result:** the tree model stays. The best LSTM (run 2) trails it by 23% at 1h and 3% at 24h, and beats the naive guess at every horizon. Stopped after one follow-up, as the plan set.
