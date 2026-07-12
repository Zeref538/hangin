import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell, ReferenceLine,
} from "recharts";
import { catMeta } from "./aqi.js";

/* ---------- national stat tiles ---------- */
export function NationalStats({ cities }) {
  const vals = cities.map((c) => c.now.pm2_5);
  const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
  const sorted = [...cities].sort((a, b) => a.now.pm2_5 - b.now.pm2_5);
  const cleanest = sorted[0], dirtiest = sorted[sorted.length - 1];
  const cleanCount = cities.filter((c) => c.now.category === "Good").length;
  return (
    <div className="tiles nat">
      <div className="tile">
        <div className="n">{avg.toFixed(1)}</div>
        <div className="d">µg/m³ — average PM2.5 across all {cities.length} cities right now</div>
      </div>
      <div className="tile">
        <div className="n good">{cleanest.name}</div>
        <div className="d">cleanest air right now ({cleanest.now.pm2_5} µg/m³)</div>
      </div>
      <div className="tile">
        <div className="n bad">{dirtiest.name}</div>
        <div className="d">haziest air right now ({dirtiest.now.pm2_5} µg/m³)</div>
      </div>
      <div className="tile">
        <div className="n">{cleanCount}/{cities.length}</div>
        <div className="d">cities with officially "Good" air at this hour</div>
      </div>
    </div>
  );
}

/* ---------- ranking: every city, cleanest to haziest ---------- */
function RankTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="tt">
      <div className="t">{d.name}</div>
      <div>PM2.5: <b>{d.pm} µg/m³</b> · score {d.aqi} ({d.word})</div>
    </div>
  );
}

export function CityRanking({ cities, activeId, onPick }) {
  const rows = [...cities]
    .sort((a, b) => a.now.pm2_5 - b.now.pm2_5)
    .map((c) => ({
      id: c.id, name: c.name, pm: c.now.pm2_5, aqi: c.now.aqi,
      word: catMeta(c.now.category).word, fill: catMeta(c.now.category).bg,
    }));
  return (
    <div className="card">
      <h2>All {cities.length} cities, cleanest to haziest</h2>
      <p className="datap">Live PM2.5 in every city we watch — tap a bar to switch city.</p>
      <ResponsiveContainer width="100%" height={rows.length * 24 + 40}>
        <BarChart data={rows} layout="vertical"
                  margin={{ top: 4, right: 40, left: 8, bottom: 4 }}>
          <XAxis type="number" tick={{ fontSize: 11, fill: "var(--muted)" }}
                 stroke="var(--border-strong)" tickLine={false}
                 label={{ value: "µg/m³ of PM2.5", position: "insideBottomRight",
                          offset: -2, style: { fontSize: 10.5, fill: "var(--muted)" } }} />
          <YAxis type="category" dataKey="name" width={110}
                 tick={{ fontSize: 11.5, fill: "var(--ink-2)" }}
                 stroke="transparent" tickLine={false} interval={0} />
          <Tooltip content={<RankTooltip />} cursor={{ fill: "rgba(255,255,255,0.04)" }} />
          <ReferenceLine x={12} stroke="rgba(77,209,121,0.45)" strokeDasharray="3 4"
                         label={{ value: "clean-air limit", position: "top",
                                  fontSize: 10, fill: "var(--muted)" }} />
          <Bar dataKey="pm" radius={[0, 4, 4, 0]} barSize={13} isAnimationActive={false}
               onClick={(d) => onPick(d.id)} cursor="pointer"
               label={{ position: "right", fontSize: 10.5, fill: "var(--muted)" }}>
            {rows.map((r) => (
              <Cell key={r.id} fill={r.fill}
                    fillOpacity={r.id === activeId ? 1 : 0.55}
                    stroke={r.id === activeId ? "#fff" : "none"} strokeWidth={1} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ---------- what's in the air (pollutant breakdown vs WHO guideline) ---------- */
const POLLUTANTS = [
  { key: "pm2_5", name: "PM2.5", plain: "fine smoke & dust", who: 15 },
  { key: "pm10", name: "PM10", plain: "coarse dust", who: 45 },
  { key: "nitrogen_dioxide", name: "NO₂", plain: "traffic gas", who: 25 },
  { key: "ozone", name: "O₃", plain: "sunlight smog", who: 100 },
  { key: "sulphur_dioxide", name: "SO₂", plain: "industrial fumes", who: 40 },
  { key: "carbon_monoxide", name: "CO", plain: "exhaust gas", who: 4000 },
];

export function PollutantPanel({ city }) {
  const values = { pm2_5: city.now.pm2_5, ...(city.pollutants ?? {}) };
  return (
    <div className="card">
      <h2>What's in {city.name}'s air right now</h2>
      <p className="datap">
        Each bar compares a pollutant to the <b>World Health Organization's daily
        safe guideline</b> — under the white line means within safe levels.
      </p>
      <div className="pols">
        {POLLUTANTS.filter((p) => values[p.key] != null).map((p) => {
          const ratio = values[p.key] / p.who;
          const w = Math.min(ratio / 2.5, 1) * 100;
          const color = ratio <= 1 ? "#4dd179" : ratio <= 2 ? "#f5d442" : "#f5a35c";
          return (
            <div className="pol" key={p.key}>
              <div className="pl">
                <b>{p.name}</b> <span>{p.plain}</span>
              </div>
              <div className="pbar">
                <div className="pfill" style={{ width: `${w}%`, background: color }} />
                <div className="pwho" />
              </div>
              <div className="pv">{values[p.key]}<small> µg/m³</small></div>
            </div>
          );
        })}
      </div>
      <p className="btnote">
        The white line marks 100% of the WHO daily guideline
        (PM2.5 15 · PM10 45 · NO₂ 25 · O₃ 100 · SO₂ 40 · CO 4000 µg/m³).
      </p>
    </div>
  );
}
