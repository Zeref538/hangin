# Hangin' — Philippine Air-Quality Forecasting & Health-Risk Dashboard

> *hangin* (Tagalog: **wind, air**) — so… how's the air hangin'?

Forecasts PM2.5 for Philippine cities **1–24 hours ahead** and translates it into
plain-language health advice. Unlike existing PH air trackers, which only show the
current reading, Hangin' **predicts where air quality is heading** — and shows its own
model's accuracy honestly, backtested against a naive baseline.

## Why it's different
Most junior ML portfolios use static, clichéd datasets. Hangin' uses **live, free public
data** and ships a real forecasting model plus an honest evaluation: it beats a
persistence baseline by ~9–10% MAE at the 12–24h horizons that actually matter.

## Backtest (5 PH metros pooled, ~1.9 yrs history, chronological holdout)
| Horizon | Model MAE (µg/m³) | R² | Naive persistence MAE | Lift |
|--------:|:-----------------:|:--:|:---------------------:|:----:|
| 1 h  | 0.88 | 0.95 | 0.95 | +8.1% |
| 6 h  | 2.88 | 0.72 | 3.44 | +16.4% |
| 12 h | 3.63 | 0.56 | 4.57 | +20.5% |
| 24 h | 4.08 | 0.42 | 4.66 | +12.5% |

One pooled model across Manila, Quezon City, Cebu, Davao, and Baguio (with location
features). Naive guessing is fine for the next hour, but the model's edge grows to
+12–20% at the 6–24h horizons — exactly where a forecast is useful.

## Data (all free, no API key)
- **Open-Meteo Air-Quality API** — PM2.5/PM10/NO₂/O₃/CO/SO₂, hourly history + forecast
- **Open-Meteo Archive (weather)** — temperature, humidity, wind, rain, pressure, PBL height

## Stack
- **ML:** Python · pandas · scikit-learn (`HistGradientBoostingRegressor`)
- **Web:** React + Vite (dashboard)
- **Refresh:** scheduled job re-fetches data and republishes forecasts

## Run the model
```bash
pip install -r requirements.txt
python ml/train.py   # fetches data, trains, writes data/backtest.json
```
