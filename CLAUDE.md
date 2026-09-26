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

## Model results (read before quoting numbers anywhere)
The original 2022–2024 holdout (+18.8% at 1h) was flattering: it covered mostly easy
dry-season months. The honest headline is the **full-year walk-forward test**
(`ml/walkforward.py` → `data/walkforward.json`, test 2025-09-20..2026-09-20, 3 seeds):
| H | Retrained MAE | 2024-model MAE | Naive MAE | Lift | 80% band hit |
|--|--|--|--|--|--|
| 1h | 0.93 | 1.23 | 1.26 | +26.3% | 82.8% |
| 6h | 3.17 | 3.68 | 4.80 | +34.0% | 81.3% |
| 12h | 3.81 | 4.29 | 6.46 | +41.0% | 82.2% |
| 24h | 4.09 | 4.28 | 4.74 | +13.6% | 81.0% |
- Models go stale: `retrain.yml` runs `ml/refit.py` monthly; ships only if better on
  average vs the live model on the last 30 days (≤2% worse on any one horizon).
- Models live in the `models` GitHub Release, NOT git. `gh release download models -D data/models`.
- Live scorecard: `data/forecast_log.csv` (ours vs Open-Meteo vs naive), started 2026-09-27.
- Map labels are Esri: CARTO tiles began returning an "API KEY REQUIRED" stamp.

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
- [~] **Phase 4 (nearly done)** — DONE: GitHub Actions hourly refresh
      (`.github/workflows/refresh.yml`, cron :20, commits forecasts.json as Zeref538);
      Vercel deploy live + public at https://hangin-acra1.vercel.app (project `hangin`,
      team acra1, git-connected → auto-redeploys on push, deployment protection off);
      3 screenshots in portfolio `public/projects/hangin-{1,2,3}.jpg`.
      TODO: portfolio `src/data.js` entry + skillIcons (Time-Series/Open-Meteo/Leaflet)
      — edits were blocked by a transient permission-service outage; retry then deploy
      portfolio. **Gate: user sign-off before portfolio goes live.**

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
