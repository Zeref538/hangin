# LSTM vs the shipped model: plan

Written 2026-10-07, before any LSTM code exists. The question: does a sequence model beat Hangin's HistGradientBoosting forecaster on the same full-year test?

## What gets compared

All three run on the walk-forward split in `ml/walkforward.py`. The test year is the last 365 days of `history.parquet` + `unseen.parquet` (2025-09-20 to 2026-09-20, 8,761 hours per city, 43,805 rows per horizon). Training uses every hour before it, with the same purge: a training row's target (t + h) must land before the test year starts.

| Model | 1h MAE | 6h MAE | 12h MAE | 24h MAE |
|---|---|---|---|---|
| Naive ("air stays the same") | 1.26 | 4.80 | 6.46 | 4.74 |
| HistGradientBoosting, retrained (3 seeds) | 0.93 | 3.17 | 3.81 | 4.09 |
| LSTM | to measure | | | |

The baseline numbers come from `data/walkforward.json`. They get re-run, not copied, before the LSTM is scored, in case the data moved.

## The LSTM

- **Input:** the last 48 hours of raw hourly readings per city: PM2.5, PM10, the four gases, weather, wind as sin/cos, hour and day of week as sin/cos, plus a learned city embedding. No hand-made lags or rolling means: the point is to see whether the network learns them itself.
- **Output:** one network predicting all four horizons at once (1, 6, 12, 24 h).
- **Loss:** L1 (mean absolute error), the same number we report.
- **Size:** one LSTM layer, 64 units, then a small linear head. Bigger only if this one clearly underfits.
- **Training:** Adam, early stopping on a validation block taken from the last 60 days *before* the test year (never from the test year itself), 3 seeds (0, 1, 2).

## Leak checks before any score is believed

- Scaling (mean and spread per feature) is fit on training hours only.
- Windows never cross the train/test boundary, and the purge rule above holds for every horizon.
- The early-stopping block sits before the test year.
- Hours with missing PM2.5 (5,168 per city, early 2022) are dropped from targets and never filled with test-year data.

## Win rule (set now, not after seeing results)

The LSTM "wins" a horizon only if its 3-seed mean MAE is lower than HistGradientBoosting's by more than the larger of the two seed spreads. A win at some horizons and a loss at others gets reported as exactly that. Nothing ships to the live dashboard from this experiment: it is a comparison for the README and the case study.

A loss is a real result. Gradient-boosted trees often beat LSTMs on hourly tabular data, and the honest framing stays either way.

## Cost

Measured on this laptop (CPU, 6 threads): 43 ms per batch of 512, so about 12 s per epoch over roughly 137,000 training windows. 30 epochs × 3 seeds is about 20 minutes. PyTorch 2.12 (CPU) is already installed; it goes in a separate `requirements-lstm.txt` so the hourly refresh and the dashboard keep their sklearn-only install.

## Files

- `ml/lstm.py`: data windows, model, training, scoring. Writes `data/lstm.json`.
- `experiments.md`: one row per run, per the experiment log format.
