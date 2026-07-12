// EPA AQI category colors (conventional, fixed). `text` keeps labels readable
// on the badge; category names always accompany the color.
export const AQI_COLORS = {
  "Good":                           { bg: "#8fd67a", text: "#0b3d00" },
  "Moderate":                       { bg: "#f5d442", text: "#4a3a00" },
  "Unhealthy for Sensitive Groups": { bg: "#f5a35c", text: "#5c2e00" },
  "Unhealthy":                      { bg: "#e66767", text: "#4d0000" },
  "Very Unhealthy":                 { bg: "#a678b8", text: "#2e0b3d" },
  "Hazardous":                      { bg: "#b05c6e", text: "#3d000f" },
};

export const catColor = (category) =>
  AQI_COLORS[category] ?? { bg: "#c3c2b7", text: "#0b0b0b" };

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
