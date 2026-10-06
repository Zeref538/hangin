# TODO

Moved out of CLAUDE.md on 2026-09-30 (status goes stale there).

## Done

- [x] Phase 1: single-city forecaster + backtest
- [x] Phase 2: pooled 5-city multi-horizon models, EPA AQI and health advice, `ml/forecast.py`
- [x] Phase 4: hourly refresh Action, Vercel deploy at https://hangin-zeref.vercel.app, screenshots
- [x] Portfolio entry in `Portfolio/src/data.js` (found there 2026-09-30)
- [x] Pre-registered 24h attempt (`docs/ATTEMPT_NEXT.md`): no arm met the win rule, nothing shipped
- [x] 2024 US EPA AQI bands, tests, light theme, case study page (live 2026-09-30)
- [x] Portfolio screenshots `hangin-{1..4}.jpg` and `hangin-light-{1..4}.jpg`
- [x] Sensor-trained Manila model (`ml/sensor_model.py`): beats the best simple guess by 1.3-16.9% at 1-24 h, one seed; in README and case study
- [x] Portfolio card: full-year numbers, case study link, light screenshots (live 2026-10-01)
- [x] Hourly refresh survives one city's Open-Meteo timeout (4 of the last 200 runs failed that way)
- [x] Phase 3 layout: John waived the sign-off on 2026-10-01

## Claude Tasks

LSTM vs HistGradientBoosting on the full-year test (`docs/LSTM_PLAN.md`):

- [x] Plan with win rule, `ml/lstm.py`, smoke test (rows match walkforward.py)
- [x] Run 1: 3 seeds, plan as written (loss at every horizon, beats naive)
- [x] Log run 1 in `experiments.md`
- [x] Run 2: predict the change from now (better at 1h, still a loss everywhere; logged)
- [x] Results into README and the case study page, numbers copied from the log
- [ ] Portfolio Hangin card: one line on the LSTM result
