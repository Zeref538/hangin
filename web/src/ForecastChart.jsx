import {
  ResponsiveContainer, LineChart, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine,
} from "recharts";
import { fmtTime, fmtHour } from "./aqi.js";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tt">
      <div className="t">{fmtTime(label)}</div>
      {payload.filter((p) => p.value != null).map((p) => (
        <div key={p.dataKey}>
          {p.dataKey === "actual" ? "Observed" : "Forecast"}:{" "}
          <b>{p.value} µg/m³</b>
        </div>
      ))}
    </div>
  );
}

export default function ForecastChart({ city }) {
  const nowT = city.now.time;
  const nowMs = new Date(nowT).getTime();

  const rows = city.history.map((h) => ({ t: h.time, actual: h.pm2_5 }));
  // bridge the two series at "now" so the forecast line connects
  rows[rows.length - 1].predicted = city.now.pm2_5;
  for (const f of city.forecast) {
    const t = new Date(nowMs + f.horizon_h * 3600_000);
    // API times are naive local (Asia/Manila) — format the same way
    const iso = `${t.getFullYear()}-${String(t.getMonth() + 1).padStart(2, "0")}-${String(t.getDate()).padStart(2, "0")}T${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`;
    rows.push({ t: iso, predicted: f.pm2_5 });
  }

  return (
    <>
      <div className="legend">
        <span className="key"><span className="line" /> Observed (last 48h)</span>
        <span className="key"><span className="line dash" /> Model forecast (+1/6/12/24h)</span>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={rows} margin={{ top: 6, right: 12, left: -14, bottom: 0 }}>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <XAxis dataKey="t" tickFormatter={fmtHour} minTickGap={40}
                 tick={{ fontSize: 11, fill: "var(--muted)" }}
                 stroke="var(--baseline)" tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }}
                 stroke="transparent" tickLine={false}
                 label={{ value: "PM2.5 µg/m³", angle: -90, position: "insideLeft",
                          offset: 22, style: { fontSize: 11, fill: "var(--muted)" } }} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--baseline)" }} />
          <ReferenceLine x={nowT} stroke="var(--baseline)" strokeDasharray="2 3"
                         label={{ value: "now", position: "insideTopLeft", fontSize: 11,
                                  fill: "var(--muted)" }} />
          <Line dataKey="actual" stroke="var(--actual)" strokeWidth={2}
                dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
          <Line dataKey="predicted" stroke="var(--predicted)" strokeWidth={2}
                strokeDasharray="5 4" isAnimationActive={false}
                dot={{ r: 4, fill: "var(--predicted)", stroke: "var(--surface)", strokeWidth: 2 }}
                activeDot={{ r: 5 }} />
        </LineChart>
      </ResponsiveContainer>
    </>
  );
}
