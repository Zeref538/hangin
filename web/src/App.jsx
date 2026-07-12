import { useEffect, useMemo, useRef, useState } from "react";
import CityMap from "./CityMap.jsx";
import ForecastChart from "./ForecastChart.jsx";
import { NationalStats, CityRanking, PollutantPanel } from "./Panels.jsx";
import { catMeta, fmtTime, horizonLabel } from "./aqi.js";

const GitHubIcon = () => (
  <svg width="15" height="15" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
    <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
  </svg>
);

/* ---------- searchable city picker ---------- */
function CitySearch({ cities, activeId, onPick }) {
  const [q, setQ] = useState("");
  const [open, setOpen] = useState(false);
  const [hi, setHi] = useState(0);
  const boxRef = useRef(null);

  useEffect(() => {
    const close = (e) => {
      if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  const matches = useMemo(() => {
    const all = [...cities].sort((a, b) => a.name.localeCompare(b.name));
    const s = q.trim().toLowerCase();
    return s ? all.filter((c) => c.name.toLowerCase().includes(s)) : all;
  }, [cities, q]);

  useEffect(() => { setHi(0); }, [q]);

  const choose = (id) => { onPick(id); setOpen(false); setQ(""); };

  const onKey = (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setOpen(true); setHi((h) => Math.min(h + 1, matches.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setHi((h) => Math.max(h - 1, 0)); }
    else if (e.key === "Enter" && open && matches[hi]) { e.preventDefault(); choose(matches[hi].id); }
    else if (e.key === "Escape") setOpen(false);
  };

  return (
    <div className="citysearch" ref={boxRef}>
      <svg className="mag" width="15" height="15" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
        <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
      </svg>
      <input type="text" placeholder={`Search all ${cities.length} cities…`} value={q}
             aria-label="Search cities" aria-expanded={open} role="combobox"
             onFocus={() => setOpen(true)}
             onChange={(e) => { setQ(e.target.value); setOpen(true); }}
             onKeyDown={onKey} />
      {open && (
        <div className="citymenu" role="listbox">
          {matches.length === 0 && <div className="empty">No city matches "{q}"</div>}
          {matches.map((c, i) => {
            const meta = catMeta(c.now.category);
            return (
              <button key={c.id} role="option"
                      aria-selected={c.id === activeId}
                      className={`${c.id === activeId ? "active" : ""} ${i === hi ? "hi" : ""}`}
                      onPointerEnter={() => setHi(i)}
                      onClick={() => choose(c.id)}>
                <span>{c.name}{c.featured ? " ★" : ""}</span>
                <span className="pill" style={{ background: meta.bg }}>
                  {c.now.aqi} · {meta.word}
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ---------- now panel with weather context ---------- */
const WX_CHIPS = [
  { key: "temperature_2m", label: (v) => `${v}°C` },
  { key: "relative_humidity_2m", label: (v) => `${v}% humidity` },
  { key: "wind_speed_10m", label: (v) => `wind ${v} km/h` },
  { key: "precipitation", label: (v) => v > 0 ? `${v} mm rain` : "no rain" },
];

function NowPanel({ city }) {
  const meta = catMeta(city.now.category);
  const wx = city.weather ?? {};
  const raining = (wx.precipitation ?? 0) > 0;
  const windy = (wx.wind_speed_10m ?? 0) >= 15;
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
          <div className="wxchips">
            {WX_CHIPS.filter((c) => wx[c.key] != null).map((c) => (
              <span className="chip" key={c.key}>{c.label(wx[c.key])}</span>
            ))}
          </div>
          <p className="sub">
            Officially "{city.now.category}" · measured {fmtTime(city.now.time)}
          </p>
        </div>
      </div>
      <AqiScale aqi={city.now.aqi} />
      <details className="whynote">
        <summary>Wait — why does it look cleaner than it feels outside?</summary>
        <p>
          Three honest reasons. <b>Weather:</b>{" "}
          {raining
            ? "it's raining there right now, and rain physically washes smoke and dust out of the sky — "
            : windy
            ? "it's windy there right now, and wind blows pollution away before it builds up — "
            : "in the rainy season, monsoon rain and wind regularly scrub the air clean — "}
          the notorious smog months are the cool, windless ones (December–April).{" "}
          <b>Coverage:</b> our source measures an average over a wide area (~10–40 km),
          so a jeepney-choked road can be much worse than the city's average.{" "}
          <b>What we track:</b> this score follows fine particles (PM2.5) — a lot of
          what makes traffic air <i>feel</i> awful (fumes, gases, smell) is other
          pollutants, which you can see in the "What's in the air" section below.
        </p>
      </details>
    </div>
  );
}

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
          <div className="d">metros learned together — patterns in one help the others</div>
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

const toPoints = (ug) => Math.round(ug * (50 / 12));

function TrustPanel({ backtest }) {
  const [expert, setExpert] = useState(false);
  const h12 = backtest.horizons.find((h) => h.horizon_h === 12);
  const bestLift = Math.max(...backtest.horizons.map((h) => h.lift_pct));
  return (
    <div className="card trust">
      <h2>
        Can you trust these predictions?
        <span className="mode" role="tablist" aria-label="Explanation level">
          <button role="tab" aria-selected={!expert}
                  className={expert ? "" : "on"} onClick={() => setExpert(false)}>
            Simple
          </button>
          <button role="tab" aria-selected={expert}
                  className={expert ? "on" : ""} onClick={() => setExpert(true)}>
            Expert
          </button>
        </span>
      </h2>

      {!expert ? (
        <>
          <p className="big">
            We made the model "predict" months of past days it had never seen, then
            checked its answers. Looking half a day ahead, its guess for the air
            score was off by only about <b>{toPoints(h12.model_mae)} points out of
            500</b> on average — roughly the difference between a score of 30 and{" "}
            {30 + toPoints(h12.model_mae)}, which you wouldn't even feel.
          </p>
          <p className="big">
            And compared to simply assuming "the air will stay like it is now", our
            predictions are up to <b>{bestLift}% more accurate</b> — with the biggest
            edge 6–24 hours ahead, exactly when a heads-up helps you plan.
          </p>
          <p className="btnote">
            Verified on the 5 big metros using 2022–2024 data. The other 24 cities
            use the same model but weren't part of that test.
          </p>
        </>
      ) : (
        <>
          <p className="big">
            Chronological backtest, last 20% of 2022–2024 held out (~17k hourly
            samples across the 5 metros), pooled HistGradientBoostingRegressor per
            horizon vs. a persistence baseline. At +12h: <b>MAE{" "}
            {h12.model_mae.toFixed(2)} µg/m³</b> vs. persistence{" "}
            {h12.persistence_mae.toFixed(2)} µg/m³.
          </p>
          <table className="bt">
            <thead>
              <tr>
                <th>Horizon</th><th>Model MAE (µg/m³)</th><th>R²</th>
                <th>Persistence MAE</th><th>Lift</th>
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
            Strictly forward-in-time evaluation — no leakage; features use only
            data available at prediction time. Persistence ≈ model at +1h (as
            expected for a slow-mixing process); the model's edge grows with
            horizon. Metrics computed on the 5 training metros only; the 24 extra
            cities are served by the same pooled model (lat/lon features) without
            city-specific verification.
          </p>
        </>
      )}
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
          <a className="brand" href="/">
            <img className="logoimg" src="/hangin-logo.png" alt="" />
            Hangin<span>'</span>
          </a>
          <div className="spacer" />
          <span className="stamp">Last checked: {fmtTime(data.generated_at)} PHT</span>
          <a className="gh" href="https://github.com/Zeref538/hangin"><GitHubIcon /> Source</a>
        </div>
      </nav>

      <div className="wrap">
        <header className="hero">
          <h1>How's the air <span className="grad">hangin'</span>?</h1>
          <p className="tagline">
            <em>Hangin</em> is Tagalog for wind. We watch the air in {data.cities.length}{" "}
            Philippine cities and predict where it's heading over the next 24 hours —
            in words anyone can understand, with the receipts to back it up.
          </p>
          <div className="chips">
            <span className="chip"><b>{data.cities.length}</b> PH cities</span>
            <span className="chip">predicts <b>24h</b> ahead</span>
            <span className="chip">built on <b>3 years</b> of data</span>
            <span className="chip">free & open source</span>
          </div>
        </header>
      </div>

      {/* full-bleed live map */}
      <section className="mapsection" aria-label="Live air quality map">
        <CityMap cities={data.cities} grid={data.grid ?? []} activeId={city.id}
                 onPick={pick} follow={followMap} full />
        <div className="mapcontrols">
          <div className="citylist row">
            {data.cities.filter((c) => c.featured).map((c) => {
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
            <CitySearch cities={data.cities} activeId={city.id} onPick={pick} />
          </div>
        </div>
      </section>

      <div className="wrap">
        <div className="stack" style={{ marginTop: 18 }}>
          <NationalStats cities={data.cities} />
          <NowPanel city={city} />
          <div className="card">
            <h2>The last 2 days — and the next 24 hours</h2>
            <ForecastChart city={city} />
          </div>
          <ForecastStrip city={city} />
          <div className="duo">
            <PollutantPanel city={city} />
            <CityRanking cities={data.cities} activeId={city.id} onPick={pick} />
          </div>
          <DataPanel backtest={data.backtest} />
          <TrustPanel backtest={data.backtest} />
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
