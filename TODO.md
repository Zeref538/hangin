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

## Claude AI

- [ ] Commit `ml/sensor_model.py` with its result and add one line to the case study's "What it cannot do"

## Pending

- [ ] `ml/sensor_model.py` run (John started it 2026-09-30; needs the OpenAQ key, so only John can run it)

## Zeref Queue

- [ ] Phase 3: sign off the dashboard layout, then polish (last recorded as awaiting sign-off)
- [ ] Portfolio card numbers are stale: metric should be 41.0% less error than naive at 12h, highlight 14-41% at 6-24h, test is one unseen year (2025-09-20..2026-09-20); add `hangin-4.jpg` to `images`
