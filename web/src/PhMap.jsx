// Minimal Philippines locator map: an equirectangular projection of the
// archipelago's bounding box with city dots. Not a geographic outline —
// just spatial context for the 5 metros.
const LAT = [4.5, 19.5];
const LON = [116.5, 127.0];
const W = 260, H = 300;

const px = (lon) => ((lon - LON[0]) / (LON[1] - LON[0])) * W;
const py = (lat) => H - ((lat - LAT[0]) / (LAT[1] - LAT[0])) * H;

// Manila/QC sit 0.08° apart and Davao hugs the right edge — per-city label
// placement keeps names from colliding or clipping.
const LABEL = {
  manila:      { dx: -10, dy: 14, anchor: "end" },
  quezon_city: { dx: 10, dy: -6, anchor: "start" },
  cebu:        { dx: 10, dy: 4, anchor: "start" },
  davao:       { dx: -10, dy: 4, anchor: "end" },
  baguio:      { dx: 10, dy: 4, anchor: "start" },
};

export default function PhMap({ cities, activeId, onPick }) {
  return (
    <svg className="phmap" viewBox={`0 0 ${W} ${H}`} role="img"
         aria-label="Map of the Philippines with the 5 forecast cities">
      <rect x="0" y="0" width={W} height={H} rx="10" fill="none"
            stroke="var(--grid)" />
      {cities.map((c) => {
        const active = c.id === activeId;
        return (
          <g key={c.id} className="dot" onClick={() => onPick(c.id)}>
            <circle cx={px(c.lon)} cy={py(c.lat)} r={active ? 7 : 5}
                    fill={active ? "var(--actual)" : "var(--baseline)"}
                    stroke="var(--surface)" strokeWidth="2" />
            <text x={px(c.lon) + (LABEL[c.id]?.dx ?? 10)}
                  y={py(c.lat) + (LABEL[c.id]?.dy ?? 4)}
                  textAnchor={LABEL[c.id]?.anchor ?? "start"} fontSize="11"
                  fill={active ? "var(--ink)" : "var(--muted)"}
                  fontWeight={active ? 600 : 400}>
              {c.name}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
