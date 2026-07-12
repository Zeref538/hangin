# Hangin — Philippine Air-Quality Nowcasting & Health-Risk Dashboard

Forecasts PM2.5 for Philippine cities **1–24 hours ahead** and translates it into
plain-language health advice. Unlike existing PH air trackers, which only show the
current reading, Hangin **predicts where air quality is heading** — and shows its own
model's accuracy honestly, backtested against a naive baseline.

## Why it's different
Most junior ML portfolios use static, clichéd datasets. Hangin uses **live, free public
data** and ships a real forecasting model plus an honest evaluation: it beats a
persistence baseline by ~9–10% MAE at the 12–24h horizons that actually matter.

## Backtest (Manila, ~1.9 yrs history, chronological holdout)
| Horizon | Model MAE (µg/m³) | R² | Naive persistence MAE |
|--------:|:-----------------:|:--:|:---------------------:|
| 1 h  | 1.68 | 0.93 | 1.57 |
| 6 h  | 5.34 | 0.58 | 5.61 |
| 12 h | 6.90 | 0.32 | 7.55 |
| 24 h | 7.52 | 0.20 | 8.33 |

Naive guessing is fine for the next hour; the model's edge grows the further ahead you
forecast — exactly where a forecast is useful.

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
