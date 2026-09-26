import { useEffect, useMemo, useRef, useState } from "react";
import CityMap from "./CityMap.jsx";
import ForecastChart from "./ForecastChart.jsx";
import { NationalStats, CityRanking, PollutantPanel, ActivityGuide } from "./Panels.jsx";
import { catMeta, fmtTime, horizonLabel, haversineKm } from "./aqi.js";

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
          <p className="sub">General guidance based on US EPA air-quality bands, not medical advice. If you have a health condition, follow your doctor.</p>
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

function DataPanel({ backtest, model }) {
  const totalRows = model.n_rows?.toLocaleString() ?? "–";
  return (
    <div className="card">
      <h2>What the model learned from</h2>
      <div className="tiles">
        <div className="tile">
          <div className="n">{totalRows}</div>
          <div className="d">hourly air snapshots, {model.data_start?.slice(0, 4)} to now</div>
        </div>
        <div className="tile">
          <div className="n">5</div>
          <div className="d">metros learned together — patterns in one help the others</div>
        </div>
        <div className="tile">
          <div className="n">{backtest.features?.length ?? 33}</div>
          <div className="d">signals behind every prediction</div>
        </div>
        <div className="tile">
          <div className="n">4</div>
          <div className="d">horizons (1h, 6h, 12h, 24h), each with its own model plus a likely-range pair</div>
        </div>
      </div>
      <p className="datap">
        The model trained on <b>hour-by-hour history since mid-2022</b> (when Open-Meteo's
        air archive begins) for Manila,
        Quezon City, Cebu, Davao and Baguio, pulled from{" "}
        <a href="https://open-meteo.com/" style={{ color: "var(--actual)" }}>Open-Meteo</a>'s
        free public archives. The air readings come from CAMS, the European Copernicus
        atmosphere model, not from street-level sensors. It's retrained every month
        (latest data used: {model.trained_through}).
      </p>
      <p className="datap">
        For every prediction it weighs <b>{backtest.features?.length ?? 33} signals</b>:
        the pollution in the air right now (PM2.5, PM10, ozone, and other gases), the
        weather (wind direction and speed, rain, humidity, temperature, air pressure,
        and how well the atmosphere can flush pollution away), the rhythm of the clock
        and calendar (rush hours, weekends, seasons, even New Year fireworks), and how
        the air has been trending over the past two days in that specific city.
      </p>
    </div>
  );
}

const toPoints = (ug) => Math.round(ug * (50 / 12));

function LiveScore({ live }) {
  const rows = live?.horizons ?? [];
  if (!rows.length) return (
    <p className="btnote">
      <b>Live scorecard:</b> every hourly forecast is now logged, then graded once
      that hour actually arrives. Scores appear here as they come in.
    </p>
  );
  return (
    <>
      <h3 className="subh">Live scorecard — forecasts graded after the fact</h3>
      <table className="bt">
        <thead>
          <tr><th>Ahead</th><th>Our miss</th><th>Open-Meteo's miss</th>
              <th>"Stays the same" miss</th><th>Inside our band</th><th>Graded</th></tr>
        </thead>
        <tbody>
          {rows.map((h) => (
            <tr key={h.horizon_h}>
              <td>+{h.horizon_h}h</td>
              <td>{h.model_mae.toFixed(2)}</td>
              <td>{h.openmeteo_mae != null ? h.openmeteo_mae.toFixed(2) : "–"}</td>
              <td>{h.naive_mae.toFixed(2)}</td>
              <td>{h.band_coverage_pct}%</td>
              <td>{h.n}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="btnote">
        Average miss in µg/m³ (lower is better) since {fmtTime(live.since)}, 5 main
        cities. Open-Meteo's own forecast is logged at the same moment as ours. Small
        counts early on are noisy — give it a few weeks.
      </p>
    </>
  );
}

function TrustPanel({ data }) {
  const [expert, setExpert] = useState(false);
  const wf = data.walkforward;
  const band = Object.fromEntries(data.intervals.horizons.map((h) => [h.horizon_h, h]));
  const h1 = wf.horizons.find((h) => h.horizon_h === 1);
  const h12 = wf.horizons.find((h) => h.horizon_h === 12);
  const covs = data.intervals.horizons.map((h) => h.coverage_pct);
  const [from, to] = wf.test_period.split("..");
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
            We hid a whole year of air ({from} to {to}, every season) from the model,
            then made it forecast that year and checked its answers. Half a day ahead,
            it was off by about <b>{toPoints(h12.retrained_mae_mean)} points out of 500</b> on
            the air score, and <b>{h12.retrained_lift_pct}% closer</b> than just assuming
            "the air will stay like it is now".
          </p>
          <p className="big">
            The shaded band on the chart is the range we're 80% sure about. On that
            hidden year, reality landed inside it <b>{Math.min(...covs)}–{Math.max(...covs)}%</b> of
            the time — so the band means what it says.
          </p>
          <p className="big">
            We retrain every month. We learned the hard way: a model trained once on
            2022–2024 had lost almost all of its 1-hour edge by 2026 ({h1.shipped_lift_pct}%
            better than the simple guess, vs {h1.retrained_lift_pct}% after retraining).
          </p>
        </>
      ) : (
        <>
          <p className="big">
            Walk-forward test: same hyperparameters, trained on all hours before {from},
            tested on the full year after (purged so no target crosses the split),
            3 seeds. "2024 model" = the original model, never retrained.
          </p>
          <table className="bt">
            <thead>
              <tr>
                <th>Horizon</th><th>Retrained MAE (± seeds)</th><th>2024 model MAE</th>
                <th>Persistence MAE</th><th>Lift</th><th>80% band hit</th>
              </tr>
            </thead>
            <tbody>
              {wf.horizons.map((h) => (
                <tr key={h.horizon_h}>
                  <td>+{h.horizon_h}h</td>
                  <td>{h.retrained_mae_mean.toFixed(2)} ± {h.retrained_mae_std.toFixed(3)}</td>
                  <td>{h.shipped_mae.toFixed(2)}</td>
                  <td>{h.naive_mae.toFixed(2)}</td>
                  <td className="lift">+{h.retrained_lift_pct}%</td>
                  <td>{band[h.horizon_h]?.coverage_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="btnote">
            Band = 10th/90th-percentile HistGradientBoosting models, widened by a
            conformal margin fitted on the 90 days before the test year. Live model
            trained through {data.model.trained_through}; retrained monthly, shipped
            only if it beats the current model on the latest 30 days. Metrics are
            for the 5 training metros; the other cities use the same pooled model
            without city-specific verification.
          </p>
        </>
      )}
      <LiveScore live={data.live} />
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [cityId, setCityId] = useState("manila");
  const [followMap, setFollowMap] = useState(false);
  const [userLoc, setUserLoc] = useState(null); // {lat, lon, km, cityName} | "asking" | "denied"

  const locate = () => {
    if (!navigator.geolocation || !data) return;
    setUserLoc("asking");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const me = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        const nearest = data.cities.reduce((a, b) =>
          haversineKm(me, b) < haversineKm(me, a) ? b : a);
        setUserLoc({ ...me, km: Math.round(haversineKm(me, nearest)),
                     cityName: nearest.name });
        setCityId(nearest.id);
        setFollowMap(true);
      },
      () => setUserLoc("denied"),
      { timeout: 10000 });
  };

  useEffect(() => {
    fetch("/forecasts.json")
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(r.status))))
      .then(setData)
      .catch((e) => setErr(e));
  }, []);

  const pick = (id) => { setCityId(id); setFollowMap(true); };

  if (err) return <div className="wrap"><p>Couldn't load the forecasts — try refreshing. ({String(err)})</p></div>;
  if (!data) return <div className="wrap"><p style={{ color: "var(--muted)", padding: "40px 0" }}>Checking the air…</p></div>;

  // GitHub delays scheduled runs, so a few hours old is normal; past 8h the refresh job has likely failed
  const ageH = (Date.now() - Date.parse(data.generated_at)) / 36e5;
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
          <span className="stamp">Last checked: {fmtTime(data.generated_at)} PHT{ageH > 8 && <b style={{ color: "#e5484d" }}> · {Math.round(ageH)}h old, may be out of date</b>}</span>
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
            <span className="chip">data since <b>2022</b>, retrained monthly</span>
            <span className="chip">free & open source</span>
          </div>
        </header>
      </div>

      {/* full-bleed live map */}
      <section className="mapsection" aria-label="Live air quality map">
        <CityMap cities={data.cities} grid={data.grid ?? []} activeId={city.id}
                 onPick={pick} follow={followMap} full
                 userLoc={typeof userLoc === "object" ? userLoc : null} />
        <div className="mapcontrols">
          <div className="citylist row">
            <button className="locbtn" onClick={locate}
                    disabled={userLoc === "asking"}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none"
                   stroke="currentColor" strokeWidth="2" strokeLinecap="round"
                   aria-hidden="true">
                <circle cx="12" cy="12" r="3.5" />
                <path d="M12 2v3.5M12 18.5V22M2 12h3.5M18.5 12H22" />
              </svg>
              {userLoc === "asking" ? "Locating…"
                : userLoc === "denied" ? "Location blocked"
                : userLoc ? `${userLoc.cityName} · ${userLoc.km} km from you`
                : "Use my location"}
            </button>
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
          <ActivityGuide city={city} />
          <div className="card">
            <h2>The last 2 days — and the next 24 hours</h2>
            <ForecastChart city={city} />
          </div>
          <ForecastStrip city={city} />
          <div className="duo">
            <PollutantPanel city={city} />
            <CityRanking cities={data.cities} activeId={city.id} onPick={pick} />
          </div>
          <DataPanel backtest={data.backtest} model={data.model} />
          <TrustPanel data={data} />
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
