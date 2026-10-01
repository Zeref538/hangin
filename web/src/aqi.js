// EPA AQI categories mapped to plain language + display colors.
// `word` is the one-word verdict shown to non-technical users;
// the official category name still appears as secondary text.
export const AQI_META = {
  "Good": {
    word: "Clean", bg: "#4dd179", ink: "var(--cat-good)", glow: "rgba(77,209,121,.18)",
    plain: "The air is clean. Perfect for a run, a walk, or leaving the windows open.",
  },
  "Moderate": {
    word: "Okay", bg: "#f5d442", ink: "var(--cat-moderate)", glow: "rgba(245,212,66,.14)",
    plain: "The air is okay for most people. If you're extra sensitive (asthma, allergies), just take it easy outside.",
  },
  "Unhealthy for Sensitive Groups": {
    word: "Risky for some", bg: "#f5a35c", ink: "var(--cat-usg)", glow: "rgba(245,163,92,.16)",
    plain: "Fine for most, but kids, seniors, pregnant women, and people with asthma or heart issues should cut back on time outdoors.",
  },
  "Unhealthy": {
    word: "Bad", bg: "#e66767", ink: "var(--cat-unhealthy)", glow: "rgba(230,103,103,.18)",
    plain: "Not a good day to be outside for long. Anyone can start feeling it, so consider a mask and keep windows closed.",
  },
  "Very Unhealthy": {
    word: "Very bad", bg: "#a678b8", ink: "var(--cat-very)", glow: "rgba(166,120,184,.2)",
    plain: "Health alert. Stay indoors as much as you can and wear a good mask (N95) if you must go out.",
  },
  "Hazardous": {
    word: "Dangerous", bg: "#c46a7d", ink: "var(--cat-hazardous)", glow: "rgba(196,106,125,.22)",
    plain: "Emergency levels. Stay inside, seal windows, and use an air purifier if you have one.",
  },
};

// bg = fill behind dark text (same in both themes); ink = the colour as TEXT (per theme)
const FALLBACK = { word: "n/a", bg: "#7d8894", ink: "var(--muted)", glow: "transparent", plain: "" };
export const catMeta = (category) => AQI_META[category] ?? FALLBACK;

export const fmtTime = (iso) => {
  const d = new Date(iso);
  return d.toLocaleString("en-PH", {
    month: "short", day: "numeric", hour: "numeric", hour12: true,
  });
};

export const fmtHour = (iso) => {
  const d = new Date(iso);
  return d.toLocaleString("en-PH", { hour: "numeric", hour12: true });
};

// "in 1 hour", "in 6 hours", "this time tomorrow"
export const horizonLabel = (h) =>
  h === 24 ? "This time tomorrow" : h === 1 ? "In 1 hour" : `In ${h} hours`;

// severity rank 0 (Good) .. 5 (Hazardous) for activity advice
const CAT_ORDER = Object.keys(AQI_META);
export const severity = (category) => Math.max(0, CAT_ORDER.indexOf(category));

export const haversineKm = (a, b) => {
  const R = 6371, d = Math.PI / 180;
  const dLat = (b.lat - a.lat) * d, dLon = (b.lon - a.lon) * d;
  const s = Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * d) * Math.cos(b.lat * d) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(s));
};
