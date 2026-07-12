import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";
import { catMeta } from "./aqi.js";
import PH from "./ph.geo.json";

// Esri satellite imagery + CARTO label overlay (both free with attribution)
const TILES = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}";
const LABELS = "https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png";
const ATTRIB = "&copy; Esri, Maxar, Earthstar Geographics | &copy; OpenStreetMap &copy; CARTO";

// Continuous PM2.5 (µg/m³) -> color ramp. Anchored on the EPA thresholds the
// rest of the app uses, but interpolated so nearby values get visibly
// different shades (light green -> deep green -> yellow -> orange -> red).
const RAMP = [
  [0,    [196, 240, 194]],
  [4,    [136, 216, 144]],
  [8,    [72, 187, 110]],
  [12,   [30, 148, 82]],
  [16,   [120, 190, 70]],
  [20,   [190, 205, 62]],
  [27,   [232, 212, 58]],
  [35.4, [245, 198, 66]],
  [45,   [245, 163, 92]],
  [55.4, [240, 120, 70]],
  [100,  [230, 103, 103]],
  [150.4,[200, 60, 60]],
  [250,  [166, 120, 184]],
];
function rampColor(v) {
  if (v <= RAMP[0][0]) return RAMP[0][1];
  for (let i = 1; i < RAMP.length; i++) {
    if (v <= RAMP[i][0]) {
      const [v0, c0] = RAMP[i - 1], [v1, c1] = RAMP[i];
      const t = (v - v0) / (v1 - v0);
      return [0, 1, 2].map((k) => Math.round(c0[k] + (c1[k] - c0[k]) * t));
    }
  }
  return RAMP[RAMP.length - 1][1];
}

// Grid geometry must match ml/forecast.py fetch_grid()
const G = { lat0: 4, lat1: 20, lon0: 116, lon1: 127, step: 1 };

// Renders the PM2.5 grid as a smooth color field, bilinearly interpolated
// between grid points and clipped to the Philippine landmass.
function HeatOverlay({ grid }) {
  const map = useMap();
  useEffect(() => {
    if (!grid.length) return;

    const nLat = Math.round((G.lat1 - G.lat0) / G.step) + 1;
    const nLon = Math.round((G.lon1 - G.lon0) / G.step) + 1;
    const vals = Array.from({ length: nLat }, () => new Array(nLon).fill(null));
    for (const g of grid) {
      const i = Math.round((g.lat - G.lat0) / G.step);
      const j = Math.round((g.lon - G.lon0) / G.step);
      if (vals[i]) vals[i][j] = g.pm2_5;
    }
    const at = (i, j) => {
      const v = vals[Math.max(0, Math.min(nLat - 1, i))]?.[Math.max(0, Math.min(nLon - 1, j))];
      return v ?? 8; // sparse fallback
    };
    const sample = (lat, lon) => {
      const fi = (lat - G.lat0) / G.step, fj = (lon - G.lon0) / G.step;
      const i = Math.floor(fi), j = Math.floor(fj);
      const ti = fi - i, tj = fj - j;
      const a = at(i, j) * (1 - tj) + at(i, j + 1) * tj;
      const b = at(i + 1, j) * (1 - tj) + at(i + 1, j + 1) * tj;
      return a * (1 - ti) + b * ti;
    };

    const B = { s: 4.2, n: 19.8, w: 116.2, e: 127.0 };
    const W = 720, H = 1000;
    const X = (lon) => ((lon - B.w) / (B.e - B.w)) * W;
    const Y = (lat) => ((B.n - lat) / (B.n - B.s)) * H;

    // 1) smooth color field
    const field = document.createElement("canvas");
    field.width = W; field.height = H;
    const fctx = field.getContext("2d");
    const img = fctx.createImageData(W, H);
    for (let y = 0; y < H; y++) {
      const lat = B.n - (y / H) * (B.n - B.s);
      for (let x = 0; x < W; x++) {
        const lon = B.w + (x / W) * (B.e - B.w);
        const v = sample(lat, lon);
        const [r, g, b] = rampColor(v);
        const k = (y * W + x) * 4;
        img.data[k] = r; img.data[k + 1] = g; img.data[k + 2] = b;
        img.data[k + 3] = 235;
      }
    }
    fctx.putImageData(img, 0, 0);

    // 2) clip to the landmass
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    ctx.beginPath();
    for (const f of PH.features) {
      const polys = f.geometry.type === "Polygon"
        ? [f.geometry.coordinates] : f.geometry.coordinates;
      for (const poly of polys) {
        for (const ring of poly) {
          ring.forEach(([lon, lat], idx) => {
            const x = X(lon), y = Y(lat);
            idx === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
          });
          ctx.closePath();
        }
      }
    }
    ctx.clip();
    // darken the land first so the air colors read against a neutral base
    // instead of competing with green jungle in the satellite imagery
    ctx.fillStyle = "rgba(8, 11, 16, 0.85)";
    ctx.fillRect(0, 0, W, H);
    ctx.filter = "blur(2px)";
    ctx.drawImage(field, 0, 0);

    const overlay = L.imageOverlay(cv.toDataURL(),
      [[B.s, B.w], [B.n, B.e]], { opacity: 0.8, interactive: false });
    overlay.addTo(map);
    return () => overlay.remove();
  }, [grid, map]);
  return null;
}

const markerIcon = (city, active) => {
  const meta = catMeta(city.now.category);
  const size = active ? 42 : city.featured ? 32 : 22;
  return L.divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div class="citymarker${active ? " active" : ""}${city.featured || active ? "" : " mini"}"
                style="--mk:${meta.bg}" title="${city.name}: AQI ${city.now.aqi}">${
                  city.featured || active ? city.now.aqi : ""}</div>`,
  });
};

function FlyTo({ city }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([city.lat, city.lon], 9, { duration: 0.9 });
  }, [city.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export default function CityMap({ cities, grid = [], activeId, onPick, follow, full, userLoc }) {
  const active = cities.find((c) => c.id === activeId);
  return (
    <div className={full ? "mapbox full" : "mapbox big"}>
      <MapContainer center={[12.6, 122.0]} zoom={6} minZoom={5} scrollWheelZoom={false}
                    maxBounds={[[2, 110], [23, 134]]} maxBoundsViscosity={0.8}
                    attributionControl={true}>
        <TileLayer url={TILES} attribution={ATTRIB} />
        <TileLayer url={LABELS} subdomains="abcd" />
        <HeatOverlay grid={grid} />
        {follow && active && <FlyTo city={active} />}
        {userLoc && (
          <Marker position={[userLoc.lat, userLoc.lon]} zIndexOffset={3000}
                  icon={L.divIcon({ className: "", iconSize: [46, 20],
                    iconAnchor: [23, 10],
                    html: '<div class="youmarker">You</div>' })} />
        )}
        {cities.map((c) => (
          <Marker key={`${c.id}-${c.id === activeId}`} position={[c.lat, c.lon]}
                  icon={markerIcon(c, c.id === activeId)}
                  zIndexOffset={c.id === activeId ? 2000 : c.featured ? 1000 : 500}
                  eventHandlers={{ click: () => onPick(c.id) }} />
        ))}
      </MapContainer>

      <div className="maplegend">
        <span className="cap">Air over land</span>
        <span className="ramp" />
        <span className="ends">clean → dirty</span>
      </div>
    </div>
  );
}
