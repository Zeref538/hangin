import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";
import { catMeta } from "./aqi.js";

// Dark basemap (CARTO, free with attribution)
const TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const ATTRIB =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

// PM2.5 (µg/m³) -> overlay color, following the EPA breakpoints the rest of
// the app uses. Values here are µg/m³, not AQI.
const pmColor = (pm) =>
  pm <= 12 ? "#4dd179" :
  pm <= 35.4 ? "#f5d442" :
  pm <= 55.4 ? "#f5a35c" :
  pm <= 150.4 ? "#e66767" :
  pm <= 250.4 ? "#a678b8" : "#b05c6e";

// Renders the PM2.5 grid as one smooth translucent "pollution cloud":
// each grid point becomes a soft radial gradient on an offscreen canvas,
// which is draped over the archipelago as a single image overlay.
function HeatOverlay({ grid }) {
  const map = useMap();
  useEffect(() => {
    if (!grid.length) return;
    const B = { s: 4.2, n: 19.8, w: 116.2, e: 127.0 };
    const W = 640, H = 900;
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const ctx = cv.getContext("2d");
    const r = 72; // px — grid step is 1° ≈ 59px wide, so discs blend
    for (const g of grid) {
      const x = ((g.lon - B.w) / (B.e - B.w)) * W;
      const y = ((B.n - g.lat) / (B.n - B.s)) * H;
      const col = pmColor(g.pm2_5);
      // heavier air -> denser color
      const alpha = Math.round(120 + Math.min(g.pm2_5 / 100, 1) * 110)
        .toString(16).padStart(2, "0");
      const grad = ctx.createRadialGradient(x, y, 0, x, y, r);
      grad.addColorStop(0, col + alpha);
      grad.addColorStop(0.65, col + "55");
      grad.addColorStop(1, col + "00");
      ctx.fillStyle = grad;
      ctx.fillRect(x - r, y - r, 2 * r, 2 * r);
    }
    // dissolve the rectangle's edges so the cloud fades into the ocean
    // instead of ending in a hard vertical curtain
    ctx.globalCompositeOperation = "destination-out";
    const F = 90;
    for (const [x0, y0, x1, y1] of [
      [0, 0, F, 0], [W, 0, W - F, 0], [0, 0, 0, F], [0, H, 0, H - F],
    ]) {
      const m = ctx.createLinearGradient(x0, y0, x1, y1);
      m.addColorStop(0, "rgba(0,0,0,1)");
      m.addColorStop(1, "rgba(0,0,0,0)");
      ctx.fillStyle = m;
      ctx.fillRect(0, 0, W, H);
    }
    ctx.globalCompositeOperation = "source-over";

    const overlay = L.imageOverlay(cv.toDataURL(),
      [[B.s, B.w], [B.n, B.e]], { opacity: 0.45, interactive: false });
    overlay.addTo(map);
    return () => overlay.remove();
  }, [grid, map]);
  return null;
}

const markerIcon = (city, active) => {
  const meta = catMeta(city.now.category);
  const size = active ? 42 : 32;
  return L.divIcon({
    className: "",
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    html: `<div class="citymarker${active ? " active" : ""}" style="--mk:${meta.bg}"
                title="${city.name}: AQI ${city.now.aqi}">${city.now.aqi}</div>`,
  });
};

function FlyTo({ city }) {
  const map = useMap();
  useEffect(() => {
    map.flyTo([city.lat, city.lon], 9, { duration: 0.9 });
  }, [city.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export default function CityMap({ cities, grid = [], activeId, onPick, follow }) {
  const active = cities.find((c) => c.id === activeId);
  return (
    <div className="mapbox big">
      <MapContainer center={[12.6, 122.0]} zoom={6} minZoom={5} scrollWheelZoom={false}
                    maxBounds={[[2, 110], [23, 134]]} maxBoundsViscosity={0.8}
                    attributionControl={true}>
        <TileLayer url={TILES} attribution={ATTRIB} subdomains="abcd" />
        <HeatOverlay grid={grid} />
        {follow && active && <FlyTo city={active} />}
        {cities.map((c) => (
          <Marker key={`${c.id}-${c.id === activeId}`} position={[c.lat, c.lon]}
                  icon={markerIcon(c, c.id === activeId)} zIndexOffset={1000}
                  eventHandlers={{ click: () => onPick(c.id) }} />
        ))}
      </MapContainer>

      <div className="maplegend">
        <span className="cap">Air right now</span>
        <span className="swatches">
          <i style={{ background: "#4dd179" }} /> clean
          <i style={{ background: "#f5d442" }} /> okay
          <i style={{ background: "#f5a35c" }} /> risky
          <i style={{ background: "#e66767" }} /> dirty
        </span>
      </div>
    </div>
  );
}
