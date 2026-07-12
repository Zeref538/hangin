# Hangin' — build context & instructions (read this first)

Brand name is **Hangin'** (with apostrophe): *hangin* = Tagalog for wind/air, plus
"how's it hangin'?". The GitHub repo slug stays `hangin` (no apostrophes allowed).

This file is the handoff for continuing the build in a fresh Claude Code session
opened **on this `Hangin` folder** (kept separate from the portfolio repo to save tokens).

## What we're building
A web dashboard that forecasts **PM2.5 for 5 Philippine metros 1–24 hours ahead** and
turns it into plain-language health advice. The differentiator vs. existing PH air
trackers: they only show the current reading — Hangin' **predicts where air quality is
heading** and shows its own model's accuracy honestly (backtested vs a naive baseline).

Owner: **John Andrei Martinez** (GitHub `Zeref538`). This becomes a portfolio project at
johnandrei.vercel.app, positioning him as an aspiring Data Analyst / AI / ML Engineer.

## Decisions already locked (do not re-litigate)
- **ML depth:** Version B — train our own forecaster + backtest it (not just call an API).
- **Horizons:** multi-horizon 1 / 6 / 12 / 24h.
- **Cities:** 5 metros pooled into ONE model with location features — Manila, Quezon City,
  Cebu City, Davao City, Baguio.
- **Repo:** standalone, public → https://github.com/Zeref538/hangin (already created & pushed).
- **Cadence:** phase gates — check in with the user before starting each phase.

## Data sources (all free, no API key — verified live)
- Open-Meteo **Air-Quality API** — pm2_5/pm10/CO/NO2/O3/SO2, hourly history + forecast.
  Note: archive coverage starts ~mid-2022; early-2022 hours are missing (not a bug).
- Open-Meteo **Archive (weather)** — temp, humidity, wind, precip, pressure, PBL height.
- Open-Meteo **Forecast** — same weather vars for live inference (`past_days`/`forecast_days`).

## Repo layout
```
ml/
  common.py   # CITIES, HORIZONS, fetch_history/fetch_recent, make_features, pm25_to_aqi (EPA AQI)
  train.py    # pooled multi-horizon training -> data/models/model_h{1,6,12,24}.pkl + data/backtest.json
data/         # parquet + model pkls + backtest.json (parquet & pkls are gitignored)
web/          # React+Vite dashboard (NOT built yet) — web/public/ will hold generated JSON
```
Run training: `pip install -r requirements.txt` then `python ml/train.py` (from repo root,
or `cd ml && python train.py`). Takes ~2–4 min (fetches ~131k rows).

## Backtest results (pipeline v2 + tuned, pooled, chronological holdout)
| H | Model MAE | R² | Persistence MAE | Lift |
|--|--|--|--|--|
| 1h | 0.77 | 0.96 | 0.94 | +18.8% |
| 6h | 2.68 | 0.74 | 3.37 | +20.6% |
| 12h | 3.42 | 0.57 | 4.45 | +23.0% |
| 24h | 3.76 | 0.45 | 4.45 | +15.6% |
Pipeline v2 (`ml/tune.py`): hourly-grid cleaning, wind vectors + ventilation index,
city categorical, absolute_error loss won every horizon; 40-trial random search per
horizon, 60/20/20 chronological protocol, log in data/tuning.json.

## Phases
- [x] **Phase 1** — single-city forecaster + backtest (proof of signal).
- [x] **Phase 2** — pooled 5-city multi-horizon models + EPA AQI/health mapping.
      DONE: `common.py`, `train.py`, models + backtest.json, and `ml/forecast.py`
      (live inference → `web/public/forecasts.json` with shape
      `{generated_at, cities:[{id,name,lat,lon,now,history[48],
      forecast:[{horizon_h, pm2_5, aqi, category, advice}]}], backtest}`).
- [~] **Phase 3 (first layout built — awaiting user layout sign-off before polish)** —
      React+Vite dashboard in `web/`: city picker + map, "now" AQI gauge,
      multi-horizon forecast line chart (Recharts), health advisory card, and a
      model-performance panel that shows the backtest table (the ML proof). Consumes
      `forecasts.json`. **Gate: confirm layout with user before polishing.**
- [ ] **Phase 4** — automate refresh (GitHub Actions cron runs `forecast.py`, commits JSON),
      deploy `web/` to Vercel, then add the project to the portfolio `src/data.js`
      (title, tags: Python/scikit-learn/Time-Series/Open-Meteo/React, metric like
      "+20% MAE vs naive @12h", demo + repo links, 3 screenshots in public/projects/).
      **Gate: user sign-off before it goes live / into the portfolio.**

## Conventions (match the portfolio repo)
- Commit author must be the GitHub-linked noreply email so contributions count:
  `git -c user.email="238805789+Zeref538@users.noreply.github.com" -c user.name="Zeref538" commit ...`
- **Never** add `Co-Authored-By: Claude` trailers.
- sklearn only for ML (Python 3.14 here has no xgboost/lightgbm wheels;
  `HistGradientBoostingRegressor` is the chosen model). pyarrow is available.
- Keep the honest-evaluation framing — do not inflate metrics.

## When done, to wire into the portfolio
The portfolio lives at `../Portfolio`. Add an entry to `src/data.js` `projects` array and
skill/issuer icons in `src/skillIcons.jsx` if new tech is introduced. Deploy hook for the
portfolio Vercel build is documented in that repo's session memory.
