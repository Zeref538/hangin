import {
  ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis,
  CartesianGrid, Tooltip, ReferenceLine, ReferenceArea,
} from "recharts";
import { fmtTime, fmtHour } from "./aqi.js";

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="tt">
      <div className="t">{fmtTime(label)}</div>
      {payload.filter((p) => p.value != null && p.dataKey !== "actualArea").map((p) => (
        <div key={p.dataKey}>
          {p.dataKey === "actual" ? "Measured" : "Our prediction"}:{" "}
          <b>{p.value} µg/m³</b>
        </div>
      ))}
    </div>
  );
}

export default function ForecastChart({ city }) {
  const nowT = city.now.time;
  const nowMs = new Date(nowT).getTime();

  const rows = city.history.map((h) => ({
    t: h.time, actual: h.pm2_5, actualArea: h.pm2_5,
  }));
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
        <span className="key"><span className="line" /> What we measured (last 2 days)</span>
        <span className="key"><span className="line dash" /> What we predict (next 24h)</span>
        <span className="key"><span className="zone" /> Clean-air zone (0–12 µg/m³)</span>
      </div>
      <ResponsiveContainer width="100%" height={270}>
        <ComposedChart data={rows} margin={{ top: 8, right: 14, left: -12, bottom: 0 }}>
          <defs>
            <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--actual)" stopOpacity={0.28} />
              <stop offset="100%" stopColor="var(--actual)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="var(--grid)" vertical={false} />
          <ReferenceArea y1={0} y2={12} fill="rgba(77, 209, 121, 0.06)"
                         stroke="rgba(77, 209, 121, 0.18)" strokeDasharray="3 4" />
          <XAxis dataKey="t" tickFormatter={fmtHour} minTickGap={44}
                 tick={{ fontSize: 11, fill: "var(--muted)" }}
                 stroke="var(--border-strong)" tickLine={false} />
          <YAxis tick={{ fontSize: 11, fill: "var(--muted)" }}
                 stroke="transparent" tickLine={false}
                 label={{ value: "PM2.5 µg/m³", angle: -90, position: "insideLeft",
                          offset: 22, style: { fontSize: 11, fill: "var(--muted)" } }} />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: "var(--border-strong)" }} />
          <ReferenceLine x={nowT} stroke="var(--border-strong)" strokeDasharray="2 3"
                         label={{ value: "now", position: "insideTopLeft", fontSize: 11,
                                  fill: "var(--muted)" }} />
          <Area dataKey="actualArea" stroke="none" fill="url(#actualFill)"
                isAnimationActive={false} tooltipType="none" />
          <Line dataKey="actual" stroke="var(--actual)" strokeWidth={2.5}
                dot={false} activeDot={{ r: 4 }} isAnimationActive={false} />
          <Line dataKey="predicted" stroke="var(--predicted)" strokeWidth={2.5}
                strokeDasharray="6 5" isAnimationActive={false}
                dot={{ r: 4.5, fill: "var(--predicted)", stroke: "#0b0f14", strokeWidth: 2 }}
                activeDot={{ r: 5.5 }} />
        </ComposedChart>
      </ResponsiveContainer>
    </>
  );
}
