import { useEffect, useState } from "react";
import CityMap from "./CityMap.jsx";
import ForecastChart from "./ForecastChart.jsx";
import { catMeta, fmtTime, horizonLabel } from "./aqi.js";

const WindIcon = ({ size = 18 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#4da3ff"
       strokeWidth="2" strokeLinecap="round" aria-hidden="true">
    <path d="M3 8h9a3 3 0 1 0-3-3" />
    <path d="M3 12h13a3 3 0 1 1-3 3" />
    <path d="M3 16h6a2 2 0 1 1-2 2" />
  </svg>
);

const GitHubIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
  </svg>
);

function AqiScale({ aqi }) {
  const pct = Math.min(aqi, 500) / 500 * 100;
  return (
    <div className="scale">
      <div className="bar" />
      <div className="marker" style={{ left: `${pct}%` }} />
      <div className="ticks">
        <span>0</span><span>50</span><span>100</span><span>150</span>
        <span>200</span><span>300</span><span>500</span>
      </div>
      <p className="cap">
        <b>What's this score?</b> It's the US air-quality index — it tracks the tiny
        smoke and dust particles (PM2.5) that get deep into your lungs.
        <b> Under 50 is clean air</b>; the further right, the worse it gets.
      </p>
    </div>
  );
}

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
          <p className="cat" style={{ color: meta.bg }}>{meta.word}</p>
          <p className="advice">{meta.plain}</p>
          <p className="sub">
            Officially "{city.now.category}" · measured {fmtTime(city.now.time)}
          </p>
        </div>
      </div>
      <AqiScale aqi={city.now.aqi} />
    </div>
  );
}

function Delta({ from, to }) {
  const d = to - from;
  if (Math.abs(d) < 0.5) return <span className="delta flat">— steady</span>;
  return d > 0
    ? <span className="delta up">▲ worse</span>
    : <span className="delta down">▼ better</span>;
}

function ForecastStrip({ city }) {
  return (
    <div className="card">
      <h2>What happens next</h2>
      <div className="fstrip">
        {city.forecast.map((f) => {
          const meta = catMeta(f.category);
          return (
            <div className="fcell" key={f.horizon_h} style={{ "--fc": meta.bg }}>
              <div className="h">
                {horizonLabel(f.horizon_h)}
                <Delta from={city.now.pm2_5} to={f.pm2_5} />
              </div>
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

function DataPanel({ backtest }) {
  const h1 = backtest.horizons[0];
  const totalRows = (h1.n_train + h1.n_test).toLocaleString();
  return (
    <div className="card">
      <h2>What the model learned from</h2>
      <div className="tiles">
        <div className="tile">
          <div className="n">{totalRows}</div>
          <div className="d">hourly air snapshots from 2022–2024</div>
        </div>
        <div className="tile">
          <div className="n">5</div>
          <div className="d">cities learned together — patterns in one help the others</div>
        </div>
        <div className="tile">
          <div className="n">33</div>
          <div className="d">signals behind every prediction</div>
        </div>
        <div className="tile">
          <div className="n">4</div>
          <div className="d">specialist models — one each for 1h, 6h, 12h and 24h ahead</div>
        </div>
      </div>
      <p className="datap">
        The model trained on <b>three years of hour-by-hour history</b> for Manila,
        Quezon City, Cebu, Davao and Baguio, pulled from{" "}
        <a href="https://open-meteo.com/" style={{ color: "var(--actual)" }}>Open-Meteo</a>'s
        free public archives — the same satellite-and-station data used by weather apps.
      </p>
      <p className="datap">
        For every prediction it weighs <b>33 signals</b>: the pollution in the air right
        now (PM2.5, PM10, ozone, and other gases), the weather (wind, rain, humidity,
        temperature, air pressure), the rhythm of the clock and calendar (rush hours,
        weekdays vs. weekends, seasons), and how the air has been trending over the
        past two days in that specific city.
      </p>
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
        on average</b> — a small fraction of the gap between "clean" and "risky" air.
      </p>
      <p className="big">
        Is that good? The lazy alternative — assuming the air just stays the way it
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
  if (!data) return <div className="wrap"><p style={{ color: "var(--muted)", padding: "40px 0" }}>Checking the air…</p></div>;

  const city = data.cities.find((c) => c.id === cityId) ?? data.cities[0];

  return (
    <>
      <nav className="top">
        <div className="inner">
          <a className="brand" href="/"><span className="logo"><WindIcon /></span>Hangin<span>'</span></a>
          <div className="spacer" />
          <span className="stamp">Last checked: {fmtTime(data.generated_at)} PHT</span>
          <a className="gh" href="https://github.com/Zeref538/hangin"><GitHubIcon /> Source</a>
        </div>
      </nav>

      <div className="wrap">
        <header className="hero">
          <h1>How's the air <span className="grad">hangin'</span>?</h1>
          <p className="tagline">
            <em>Hangin</em> is Tagalog for wind. We watch the air in 5 Philippine
            metros and predict where it's heading over the next 24 hours — in words
            anyone can understand, with the receipts to back it up.
          </p>
          <div className="chips">
            <span className="chip"><b>5</b> PH metros</span>
            <span className="chip">predicts <b>24h</b> ahead</span>
            <span className="chip">built on <b>3 years</b> of data</span>
            <span className="chip">free & open source</span>
          </div>
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
                    <span className="pill" style={{ background: meta.bg }}>
                      {c.now.aqi} · {meta.word}
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
            <DataPanel backtest={data.backtest} />
            <TrustPanel backtest={data.backtest} />
          </div>
        </div>

        <footer className="site">
          Air & weather data from <a href="https://open-meteo.com/">Open-Meteo</a> ·
          Predictions from our own machine-learning model (scikit-learn) ·
          Health levels follow the US EPA air-quality index ·
          A portfolio project by <a href="https://github.com/Zeref538/hangin">John Andrei Martinez</a>.
          Forecasts are estimates, not official government readings.
        </footer>
      </div>
    </>
  );
}
