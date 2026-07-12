import { useEffect, useState } from "react";
import PhMap from "./PhMap.jsx";
import ForecastChart from "./ForecastChart.jsx";
import { catColor, fmtTime } from "./aqi.js";

function NowPanel({ city }) {
  const c = catColor(city.now.category);
  return (
    <div className="card">
      <h2>Right now — {city.name}</h2>
      <div className="nowrow">
        <div className="aqi-badge" style={{ background: c.bg, color: c.text }}>
          <div className="num">{city.now.aqi}</div>
          <div className="lbl">US AQI</div>
        </div>
        <div className="nowmeta">
          <p className="cat">{city.now.category}</p>
          <p className="advice">{city.now.advice}</p>
          <p className="sub">
            PM2.5 {city.now.pm2_5} µg/m³ · observed {fmtTime(city.now.time)} (PHT)
          </p>
        </div>
      </div>
    </div>
  );
}

function ForecastStrip({ city }) {
  return (
    <div className="card">
      <h2>Model forecast</h2>
      <div className="fstrip">
        {city.forecast.map((f) => {
          const c = catColor(f.category);
          return (
            <div className="fcell" key={f.horizon_h}>
              <div className="h">+{f.horizon_h}h</div>
              <div className="v">{f.pm2_5} <small>µg/m³</small></div>
              <div className="c">
                <span className="swatch" style={{ background: c.bg }} />
                AQI {f.aqi} · {f.category}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function BacktestPanel({ backtest }) {
  return (
    <div className="card">
      <h2>How good is this model, honestly?</h2>
      <table className="bt">
        <thead>
          <tr>
            <th>Horizon</th><th>Model MAE</th><th>R²</th>
            <th>Naive MAE</th><th>Improvement</th>
          </tr>
        </thead>
        <tbody>
          {backtest.horizons.map((h) => (
            <tr key={h.horizon_h}>
              <td>+{h.horizon_h}h</td>
              <td>{h.model_mae.toFixed(2)}</td>
              <td>{h.model_r2.toFixed(2)}</td>
              <td>{h.persistence_mae.toFixed(2)}</td>
              <td className="lift">+{h.lift_pct}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="btnote">
        Backtested on a chronological holdout across all 5 cities
        ({backtest.train_period}), against a naive baseline that assumes the air
        stays exactly as it is now (persistence). MAE in µg/m³ — lower is better.
        The honest read: persistence is hard to beat 1 hour out; the model earns
        its keep at 6–24 hours, where knowing weather, traffic rhythms, and
        recent trends actually matters.
      </p>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [cityId, setCityId] = useState("manila");

  useEffect(() => {
    fetch("/forecasts.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
      .then(setData)
      .catch((e) => setErr(e));
  }, []);

  if (err) return <div className="wrap"><p>Couldn't load forecasts: {String(err)}</p></div>;
  if (!data) return <div className="wrap"><p style={{ color: "var(--muted)" }}>Loading…</p></div>;

  const city = data.cities.find((c) => c.id === cityId) ?? data.cities[0];

  return (
    <div className="wrap">
      <header className="site">
        <h1>Hangin'</h1>
        <span className="tagline">
          <i>hangin</i> (Tagalog: wind, air) — so, how's the air hangin'?
          PM2.5 forecasts 1–24h ahead for 5 PH metros.
        </span>
      </header>
      <p className="stamp">Model run: {fmtTime(data.generated_at)} (PHT)</p>

      <div className="grid">
        <div className="card">
          <h2>Pick a metro</h2>
          <PhMap cities={data.cities} activeId={city.id} onPick={setCityId} />
          <div className="citylist">
            {data.cities.map((c) => (
              <button key={c.id} className={c.id === city.id ? "active" : ""}
                      onClick={() => setCityId(c.id)}>
                <span>{c.name}</span>
                <span className="pm">{c.now.pm2_5} µg/m³</span>
              </button>
            ))}
          </div>
        </div>

        <div style={{ display: "grid", gap: 16 }}>
          <NowPanel city={city} />
          <div className="card">
            <h2>Last 48h + where it's heading</h2>
            <ForecastChart city={city} />
          </div>
          <ForecastStrip city={city} />
          <BacktestPanel backtest={data.backtest} />
        </div>
      </div>

      <footer className="site">
        Data: <a href="https://open-meteo.com/">Open-Meteo</a> air-quality &
        weather APIs · Model: pooled HistGradientBoosting (scikit-learn), one per
        horizon · Health categories: US EPA AQI · Built by{" "}
        <a href="https://github.com/Zeref538/hangin">John Andrei Martinez</a>.
        Forecasts are estimates, not official readings.
      </footer>
    </div>
  );
}
