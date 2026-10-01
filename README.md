# Hangin': Philippine Air-Quality Forecasting & Health-Risk Dashboard

> *hangin* (Tagalog: **wind, air**). So… how's the air hangin'?

Forecasts PM2.5 for Philippine cities **1–24 hours ahead** and translates it into
plain-language health advice. Unlike existing PH air trackers, which only show the
current reading, Hangin' **predicts where air quality is heading**, and shows its own
model's accuracy honestly, backtested against a naive baseline.

![Backtest: model vs naive baseline](docs/backtest.png)

**Live:** https://hangin-zeref.vercel.app, refreshed by a scheduled GitHub Action.
**Case study:** https://hangin-zeref.vercel.app/case-study.html (how it was tested, what broke, and what did not work)

## Result
Tested on **one full year the model never saw** (2025-09-20 → 2026-09-20, every
season, ~43,000 hours per horizon across 5 cities), the monthly-retrained model's
average error is **14–41% lower** than a naive "air stays the same" guess.

| Horizon | Retrained MAE (3 seeds) | Model trained once (2024) | Naive MAE | Lift vs naive | 80% band hit rate |
|--------:|:--:|:--:|:--:|:--:|:--:|
| 1 h  | 0.93 ± 0.001 | 1.23 | 1.26 | +26.3% | 82.8% |
| 6 h  | 3.17 ± 0.002 | 3.68 | 4.80 | +34.0% | 81.3% |
| 12 h | 3.81 ± 0.001 | 4.29 | 6.46 | +41.0% | 82.2% |
| 24 h | 4.09 ± 0.003 | 4.28 | 4.74 | +13.6% | 81.0% |

MAE = average miss in µg/m³ of PM2.5. Sources: [`data/walkforward.json`](data/walkforward.json),
[`data/intervals.json`](data/intervals.json).

### What we learned: a model trained once goes stale
The first version was trained once on 2022–2024 and scored **+18.8%** at 1 h on its
own holdout. Replayed on 2025–2026 ([`data/live_eval.json`](data/live_eval.json)),
that fell to **+2.2%**, and it was *worse* than the naive guess from April to August
of both years. Two causes, both measured:
- **The original holdout was flattering.** It covered mostly late 2024, the easy
  dry-season months. The 1 h lead is seasonal: +10–17% Nov–Mar, below zero Apr–Aug.
- **The air changed.** The average hour-to-hour jump in PM2.5 rose from 0.94 to
  1.28 µg/m³ between the two periods.

Retraining the *same recipe* on newer data brought the 1 h lead back to +26%. So the
model is now **retrained monthly** by [`retrain.yml`](.github/workflows/retrain.yml),
and a new model only ships if it beats the live one on the latest 30 days.

### Likely-range band
Each forecast comes with an 80% range: 10th/90th-percentile models, widened by a
*conformal* margin. That margin is measured on the 90 days before the test period
so the band catches reality as often as it claims. Raw bands hit only 72–74%;
calibrated, they hit 81–83% on the unseen year.

### Live scorecard
Every hourly forecast is logged to [`data/forecast_log.csv`](data/forecast_log.csv)
with the naive guess for the same hour, then graded once that hour arrives. The
dashboard shows the last 30 days. It started on 2026-09-27, so early numbers rest on
few samples.

Open-Meteo's own forecast is logged too, but **not scored**. The "real" values come
from the same CAMS model that produces that forecast, so it would be graded against
itself (its first 5 graded forecasts all missed by exactly 0.00).

### Tried and not shipped: improving the 24 h forecast
A pre-registered attempt ([`docs/ATTEMPT_NEXT.md`](docs/ATTEMPT_NEXT.md)) added
(1) the day-ahead forecast of wind and rain at the target hour, as it was issued at the
time, and (2) the average PM2.5 at the same hour over the past 7 days. Both together cut
24 h error from 4.09 to 4.02 (3 seeds), which is real but only 1.8%, under the 2% bar set
before running. The live model stays. The same features helped 6 h and 12 h more
(+1.5 and +1.7 points of lift), which is left for a separate test.

## Limitations
- **Inputs are modelled, not sensor readings.** Open-Meteo's PM2.5 comes from the
  CAMS atmosphere model, so this forecasts CAMS, not a street-level monitor. CAMS
  also publishes its own forecast, so the claim here is "beats a naive guess", not
  "beats the free forecast". That needs ground-sensor data, which isn't wired in yet.
  A first check (`ml/sensor_model.py`, Manila only, one seed): a model trained on
  OpenAQ sensor readings beat the best simple guess by 1.3% to 16.9% across 1-24 h
  on the same test year (`data/sensor_model.json`).
- **24 h is the weak spot:** +13.6% over naive, and the band is ±5 µg/m³ wide.
- **Band leans low on spikes:** misses are ~11% above the band vs ~7% below it.
- **Only the 5 training metros are verified.** The other 24 cities on the map use
  the same pooled model without their own test.
- **Not medical advice.** The health tips follow the US EPA AQI bands.

## Data (all free, no API key)
- **Open-Meteo Air-Quality API**: PM2.5/PM10/NO₂/O₃/CO/SO₂, hourly history + forecast
- **Open-Meteo Archive (weather)**: temperature, humidity, wind, rain, pressure, PBL height

## Stack
- **ML:** Python · pandas · scikit-learn (`HistGradientBoostingRegressor`)
- **Web:** React + Vite (dashboard)
- **Refresh:** scheduled job re-fetches data and republishes forecasts

## Run it
```bash
pip install -r requirements.txt
python ml/tune.py         # original 2022-2024 training + hyperparameter search (~40 min)
python ml/live_eval.py    # replay those models on 2025-2026 (~1 min, caches data/unseen.parquet)
python ml/walkforward.py  # full-year test, 3 seeds (~4 min)
python ml/intervals.py    # band coverage test (~4 min)
python ml/refit.py        # production retrain + gate -> data/models/ (~5 min)
python ml/forecast.py     # live forecast -> web/public/forecasts.json + forecast log
python ml/make_figure.py  # rebuilds docs/backtest.png
```
Times measured on a laptop CPU; no GPU, no cost (the data is free). The live models
are published as the [`models` release](https://github.com/Zeref538/hangin/releases/tag/models):
`gh release download models -D data/models`.

## License
MIT. See [LICENSE](LICENSE).
