import { useEffect, useState } from "react";
import CityMap from "./CityMap.jsx";
import ForecastChart from "./ForecastChart.jsx";
import { catMeta, fmtTime, horizonLabel } from "./aqi.js";

const WindIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#4da3ff"
       strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <path d="M3 8h9a3 3 0 1 0-3-3" />
    <path d="M3 12h13a3 3 0 1 1-3 3" />
    <path d="M3 16h6a2 2 0 1 1-2 2" />
  </svg>
);

function NowPanel({ city }) {
  const meta = catMeta(city.now.category);
  return (
    <div className="card nowcard" style={{ "--glow": meta.glow }}>
      <h2>The air in {city.name} right now</h2>
      <div className="nowrow">
        <div className="aqi-badge" style={{ background: meta.bg, "--glow": meta.glow }}>
          <div className="num">{city.now.aqi}</div>
          <div className="lbl">Air score</div>
        </div>
        <div className="nowmeta">
          <p className="cat">{meta.word}</p>
          <p className="advice">{meta.plain}</p>
          <p className="sub">
            Officially "{city.now.category}" · measured {fmtTime(city.now.time)}
          </p>
        </div>
      </div>
      <div className="whatis">
        <b>What's the score?</b> It's the US air-quality index (0–500) — it measures
        the tiny smoke and dust particles (PM2.5) that can get deep into your lungs.
        <b> 0–50 is clean, and the higher it goes, the worse the air.</b>
      </div>
    </div>
  );
}

function ForecastStrip({ city }) {
  return (
    <div className="card">
      <h2>What happens next</h2>
      <div className="fstrip">
        {city.forecast.map((f) => {
          const meta = catMeta(f.category);
          return (
            <div className="fcell" key={f.horizon_h}>
              <div className="h">{horizonLabel(f.horizon_h)}</div>
              <div className="v" style={{ color: meta.bg }}>{f.aqi}</div>
              <div className="word" style={{ color: meta.bg }}>{meta.word}</div>
              <div className="c">{f.pm2_5} µg/m³ of PM2.5</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function TrustPanel({ backtest }) {
  const h12 = backtest.horizons.find((h) => h.horizon_h === 12);
  const bestLift = Math.max(...backtest.horizons.map((h) => h.lift_pct));
  return (
    <div className="card trust">
      <h2>Can you trust these predictions?</h2>
      <p className="big">
        We tested the model on months of past data it had never seen: we made it
        "predict" days it didn't know, then compared against what actually happened.
        Its 12-hour predictions were off by about <b>{h12.model_mae.toFixed(1)} µg/m³
        on average</b> — for context, that's a small fraction of the gap between
        "clean" and "risky" air.
      </p>
      <p className="big">
        Is that good? The lazy alternative — just assuming the air stays the way it
        is right now — misses by {h12.persistence_mae.toFixed(1)} µg/m³. Our model is
        up to <b>{bestLift}% more accurate</b> than that, and its edge is biggest
        6–24 hours ahead: exactly when a heads-up is actually useful.
      </p>
      <details>
        <summary>See the full test numbers</summary>
        <table className="bt">
          <thead>
            <tr>
              <th>Prediction</th>
              <th>Our average miss</th>
              <th>"No change" guess misses by</th>
              <th>We're better by</th>
            </tr>
          </thead>
          <tbody>
            {backtest.horizons.map((h) => (
              <tr key={h.horizon_h}>
                <td>{horizonLabel(h.horizon_h).toLowerCase()}</td>
                <td>{h.model_mae.toFixed(2)} µg/m³</td>
                <td>{h.persistence_mae.toFixed(2)} µg/m³</td>
                <td className="lift">+{h.lift_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="btnote">
          Tested on 2022–2024 data for all 5 cities, always predicting "forward in
          time" so the model can never peek at the answer. "Miss" is the mean
          absolute error in micrograms of PM2.5 per cubic meter of air. Honest
          caveat: for 1 hour ahead, the lazy guess is nearly as good — the model
          really earns its keep further out.
        </p>
      </details>
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [cityId, setCityId] = useState("manila");
  const [followMap, setFollowMap] = useState(false);

  useEffect(() => {
    fetch("/forecasts.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
      .then(setData)
      .catch((e) => setErr(e));
  }, []);

  const pick = (id) => { setCityId(id); setFollowMap(true); };

  if (err) return <div className="wrap"><p>Couldn't load the forecasts — try refreshing. ({String(err)})</p></div>;
  if (!data) return <div className="wrap"><p style={{ color: "var(--muted)" }}>Checking the air…</p></div>;

  const city = data.cities.find((c) => c.id === cityId) ?? data.cities[0];

  return (
    <div className="wrap">
      <header className="site">
        <div className="brandrow">
          <div className="logo"><WindIcon /></div>
          <h1>Hangin<span>'</span></h1>
        </div>
        <p className="tagline">
          <em>Hangin</em> is Tagalog for wind — so, how's the air hangin'? We check
          the air in 5 Philippine cities and predict where it's heading over the
          next 24 hours, in words anyone can understand.
        </p>
        <p className="stamp">Last checked: {fmtTime(data.generated_at)} (Philippine time)</p>
      </header>

      <div className="grid">
        <div className="card">
          <h2>Pick your city</h2>
          <CityMap cities={data.cities} activeId={city.id} onPick={pick}
                   follow={followMap} />
          <div className="citylist">
            {data.cities.map((c) => {
              const meta = catMeta(c.now.category);
              return (
                <button key={c.id} className={c.id === city.id ? "active" : ""}
                        onClick={() => pick(c.id)}>
                  <span>{c.name}</span>
                  <span className="right">
                    <span className="pill" style={{ background: meta.bg }}>
                      {c.now.aqi} · {meta.word}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="stack">
          <NowPanel city={city} />
          <div className="card">
            <h2>The last 2 days — and the next 24 hours</h2>
            <ForecastChart city={city} />
          </div>
          <ForecastStrip city={city} />
          <TrustPanel backtest={data.backtest} />
        </div>
      </div>

      <footer className="site">
        Air & weather data from <a href="https://open-meteo.com/">Open-Meteo</a> ·
        Predictions from our own machine-learning model (built with scikit-learn) ·
        Health levels follow the US EPA air-quality index ·
        A portfolio project by <a href="https://github.com/Zeref538/hangin">John Andrei Martinez</a>.
        Forecasts are estimates, not official government readings.
      </footer>
    </div>
  );
}
