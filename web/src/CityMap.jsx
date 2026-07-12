import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import { useEffect } from "react";
import L from "leaflet";
import { catMeta } from "./aqi.js";

// Dark basemap (CARTO, free with attribution)
const TILES = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const ATTRIB =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>';

const markerIcon = (city, active) => {
  const meta = catMeta(city.now.category);
  const size = active ? 40 : 30;
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
    map.flyTo([city.lat, city.lon], 10, { duration: 0.9 });
  }, [city.id]); // eslint-disable-line react-hooks/exhaustive-deps
  return null;
}

export default function CityMap({ cities, activeId, onPick, follow }) {
  const active = cities.find((c) => c.id === activeId);
  return (
    <div className="mapbox">
      <MapContainer center={[12.5, 122.5]} zoom={5} scrollWheelZoom={false}
                    attributionControl={true}>
        <TileLayer url={TILES} attribution={ATTRIB} subdomains="abcd" />
        {follow && active && <FlyTo city={active} />}
        {cities.map((c) => (
          <Marker key={`${c.id}-${c.id === activeId}`} position={[c.lat, c.lon]}
                  icon={markerIcon(c, c.id === activeId)}
                  eventHandlers={{ click: () => onPick(c.id) }} />
        ))}
      </MapContainer>
    </div>
  );
}
