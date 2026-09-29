# Next attempt: the 24-hour forecast

**Status: approved 2026-09-30 and run once. Result: no arm met the win rule; the live model stays.**

## The one target number

**24 h lift over the naive guess: +13.6%** (retrained model, MAE 4.09 ± 0.003 vs naive
4.74, full unseen year 2025-09-20..2026-09-20, `data/walkforward.json`).

It is the weakest headline number: the other horizons are +26% to +41%, and the README
already calls 24 h "the weak spot". A skeptical reviewer points here first.

## Already tried (not repeated)

- 40-trial hyperparameter search per horizon (`ml/tune.py`, `data/tuning.json`).
- Feature pipeline v2: hourly-grid cleaning, wind vectors, ventilation index, city
  category, fireworks flag (`ml/common.py`).
- Retraining on newer data (the step that took 24 h from +9.6% to +13.6%).

## Ideas (at most 3)

1. **Forecast wind and rain at the target hour.** Today the model only sees the weather
   *now*. PM2.5 a day ahead depends on how well the air is blown away and washed out
   *then*. At forecast time these come
   from Open-Meteo's weather forecast, which `fetch_recent` already downloads
   (`forecast_days=2`).
   *Why it should work:* dispersion and wet removal drive day-ahead PM2.5; the
   "ventilation index" (wind x mixing height) is the standard measure, and the model
   already uses it at the current hour (see the comment in `ml/common.py`).
   *Fairness rule:* train and test use weather **as it was forecast a day earlier**, never
   the archive's observed weather, or the backtest gets a free look at the future.
   Source: Open-Meteo Previous Runs API, variables `precipitation_previous_day1`,
   `wind_speed_10m_previous_day1`, `wind_direction_10m_previous_day1`.
   *Checked 2026-09-30 (Manila, one day per date):* empty on 2022-07-01, 2023-06-01 and
   2024-01-10; 24/24 hours present on 2024-04-01, 2024-07-01, 2024-10-01, 2025-01-01,
   2025-04-01 and 48/48 on 2026-09-18. So it covers the whole test year, and training rows
   before ~early 2024 get "unknown" (the model handles missing values).
   *Narrowed:* `boundary_layer_height_previous_day1` (mixing height) is empty on every date
   checked, including 2026, so mixing height and the ventilation index at the target hour
   are **dropped**, not substituted with observed values.
   *Lead time:* "previous_day1" is a forecast issued about a day before. That matches 24 h;
   for 1/6/12 h it is older than a live forecast would be, which can only understate them.
2. **Same-hour weekly profile.** Mean PM2.5 at the target's hour of day over the previous
   7 days. The model has lags at 24 h and 48 h but no stable "what this hour is usually
   like" baseline.
   *Why:* a seasonal-naive / climatology anchor is a standard strong baseline for series
   with a daily cycle (Hyndman & Athanasopoulos, *Forecasting: Principles and Practice*,
   3rd ed., section 5.2).

## Rules, fixed before running

- **Test set:** exactly `data/walkforward.json`'s test year, same purge (no training row
  whose target falls in the test year), same 5 cities, same hyperparameters (sklearn
  `clone` of the live model).
- **Arms:** baseline (current features), +1, +2, +1+2. Every arm at every horizon.
- **Seeds:** 0, 1, 2 for every arm. Results reported as mean and range (min to max).
- **Win rule for the target:** an arm wins at 24 h only if its mean MAE is lower than
  the baseline's mean MAE by **at least 2% of the baseline** AND by more than **3x the
  larger of the two seed ranges**.
- **Nothing else gets worse:** at 1 h, 6 h and 12 h, the winning arm's lift may not drop
  more than **2 percentage points** below baseline.
- **Pick at most one arm:** if several win, the one with the lowest 24 h mean MAE ships.
- **If nothing wins:** the live model stays, and the README records what was tried and
  the numbers.
- **No re-runs with tweaked features after seeing results.** One run of this plan.

## Budget

Measured 2026-09-30 on this laptop, one real run each (error not printed, so no result
was seen): **one fit (24 h, seed 0, 137,110 training rows) = 14 s**; feature build 1 s;
**one city's day-ahead weather download = 6 s**.
Plan = 4 arms x 4 horizons x 3 seeds = **48 fits: about 11 min at 14 s each, allow up to
25 min** in case 1 h fits run slower (its saved model is ~4x larger). Plus ~30 s of
downloads. Free: no GPU, no paid API.

## Not part of this attempt

`ml/sensor_model.py` (a Manila model trained on OpenAQ ground sensors) changes the
definition of "truth", so it cannot be scored on this test set. It is a separate
experiment; its first run stopped early (5 of ~70 sensors fetched) and has no result.

## Results

Run once on 2026-09-30 (`python ml/attempt_24h.py`, full output in
`data/attempt_24h.json`). Mean MAE in ug/m3 over seeds 0-2, range in brackets. Lift is
vs the naive guess. The day-ahead weather covered 100% of test hours.

| Horizon | base | +1 forecast wind & rain | +2 same-hour 7-day mean | +1+2 |
|--|--|--|--|--|
| 1 h | 0.928 [0.927-0.928] +26.26% | 0.930 [0.927-0.932] +26.11% | 0.926 [0.926-0.927] +26.39% | 0.929 [0.928-0.929] +26.20% |
| 6 h | 3.172 [3.170-3.174] +33.97% | 3.167 [3.166-3.168] +34.08% | 3.111 [3.106-3.117] +35.24% | 3.101 [3.096-3.105] +35.44% |
| 12 h | 3.811 [3.809-3.813] +41.03% | 3.775 [3.770-3.783] +41.59% | 3.730 [3.725-3.733] +42.29% | 3.699 [3.695-3.702] +42.77% |
| **24 h** | **4.092 [4.088-4.096] +13.65%** | 4.044 [4.040-4.052] +14.64% | 4.067 [4.064-4.070] +14.17% | 4.019 [4.016-4.023] +15.18% |

Sanity check: base reproduces the published walk-forward numbers (24 h 4.09, 1 h 0.93).

**Decision by the rule written above** (win needs gain >= 2% of base = 0.082 AND > 3x noise):

| Arm | 24 h gain | > 3x noise? | >= 2%? | Worst drop at 1/6/12 h | Ships? |
|--|--|--|--|--|--|
| +1 | 0.047 (1.2%) | yes (0.035) | no | 0.15 pts | no |
| +2 | 0.025 (0.6%) | no (0.025) | no | none | no |
| +1+2 | 0.073 (1.8%) | yes (0.025) | no | 0.06 pts | no |

**What it found:** both ideas help a little and the gain from both together is real (about
3x the seed noise), but at 24 h it is 1.8%, under the 2% bar set in advance. So the live
model stays. The bar was not moved after seeing the numbers.

**Worth a separate attempt:** +1+2 helps 6 h and 12 h more than 24 h (+1.5 and +1.7 points
of lift). That was not this attempt's target, so it is not claimed here; it would need its
own pre-written rule and run.
