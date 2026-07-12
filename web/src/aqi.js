// EPA AQI categories mapped to plain language + display colors.
// `word` is the one-word verdict shown to non-technical users;
// the official category name still appears as secondary text.
export const AQI_META = {
  "Good": {
    word: "Clean", bg: "#4dd179", glow: "rgba(77,209,121,.18)",
    plain: "The air is clean. Perfect for a run, a walk, or leaving the windows open.",
  },
  "Moderate": {
    word: "Okay", bg: "#f5d442", glow: "rgba(245,212,66,.14)",
    plain: "The air is okay for most people. If you're extra sensitive (asthma, allergies), just take it easy outside.",
  },
  "Unhealthy for Sensitive Groups": {
    word: "Risky for some", bg: "#f5a35c", glow: "rgba(245,163,92,.16)",
    plain: "Fine for most, but kids, seniors, pregnant women, and people with asthma or heart issues should cut back on time outdoors.",
  },
  "Unhealthy": {
    word: "Bad", bg: "#e66767", glow: "rgba(230,103,103,.18)",
    plain: "Not a good day to be outside for long. Anyone can start feeling it — consider a mask and keep windows closed.",
  },
  "Very Unhealthy": {
    word: "Very bad", bg: "#a678b8", glow: "rgba(166,120,184,.2)",
    plain: "Health alert. Stay indoors as much as you can and wear a good mask (N95) if you must go out.",
  },
  "Hazardous": {
    word: "Dangerous", bg: "#b05c6e", glow: "rgba(176,92,110,.22)",
    plain: "Emergency levels. Stay inside, seal windows, and use an air purifier if you have one.",
  },
};

const FALLBACK = { word: "—", bg: "#7d8894", glow: "transparent", plain: "" };
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
