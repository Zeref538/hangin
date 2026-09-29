// Hangin' case study. Built by docs/build_case_study.py, which injects the result
// data below; served as a file because the site's CSP blocks inline scripts.
const D = /*%%DATA%%*/;
const NS = "http://www.w3.org/2000/svg";
function svg(tag, attrs) {
  const el = document.createElementNS(NS, tag);
  for (const k in attrs) el.setAttribute(k, attrs[k]);
  return el;
}
function text(parent, x, y, str, attrs = {}) {
  const t = svg("text", { x, y, fill: "var(--ink-3)", "font-size": 11, "font-family": "var(--mono)", ...attrs });
  t.textContent = str; parent.appendChild(t); return t;
}

/* ---------- 01: error per horizon, three methods ---------- */
function maeChart() {
  const rows = D.wf, W = 760, H = 300, PL = 44, PR = 10, PT = 24, PB = 40;
  const max = Math.ceil(Math.max(...rows.map(r => r.naive_mae)) + 0.5);
  const Y = v => PT + (1 - v / max) * (H - PT - PB);
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Average error per horizon for the retrained model, the model trained once, and the naive guess" });
  for (let v = 0; v <= max; v += 1) {
    s.appendChild(svg("line", { x1: PL, x2: W - PR, y1: Y(v), y2: Y(v), stroke: "var(--rule)", "stroke-width": 1 }));
    text(s, PL - 8, Y(v) + 4, String(v), { "text-anchor": "end" });
  }
  const group = (W - PL - PR) / rows.length, bw = 34, gap = 4;
  // the once-trained model is an outline, so it differs from the grey naive bar by shape, not shade
  const series = [["retrained_mae_mean", "var(--proj)"], ["shipped_mae", "outline"], ["naive_mae", "var(--tide)"]];
  rows.forEach((r, i) => {
    const cx = PL + group * i + group / 2;
    series.forEach(([k, c], j) => {
      const x = cx + (j - 1) * (bw + gap) - bw / 2, v = r[k];
      s.appendChild(svg("rect", c === "outline"
        ? { x: x + 0.75, y: Y(v) + 0.75, width: bw - 1.5, height: Y(0) - Y(v) - 0.75, fill: "none", stroke: "var(--ink-2)", "stroke-width": 1.5, rx: 2 }
        : { x, y: Y(v), width: bw, height: Y(0) - Y(v), fill: c, rx: 2 }));
      text(s, x + bw / 2, Y(v) - 6, v.toFixed(2), { "text-anchor": "middle", fill: j ? "var(--ink-3)" : "var(--ink)", "font-weight": j ? 400 : 700 });
    });
    text(s, cx, H - 16, r.horizon_h + " h ahead", { "text-anchor": "middle", fill: "var(--ink)", "font-size": 12.5, "font-family": "var(--sans)" });
  });
  document.getElementById("chart-mae").appendChild(s);
}

/* ---------- 04: the stale model's 1 h lead, month by month ---------- */
function monthChart() {
  const m = D.months, W = 760, H = 260, PL = 44, PR = 10, PT = 16, PB = 44;
  const vals = m.map(r => r.lift_pct), lo = Math.floor(Math.min(...vals, 0) / 5) * 5, hi = Math.ceil(Math.max(...vals) / 5) * 5;
  const Y = v => PT + (1 - (v - lo) / (hi - lo)) * (H - PT - PB);
  const bw = (W - PL - PR) / m.length;
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Monthly 1-hour lead over the naive guess for the model trained once" });
  for (let v = lo; v <= hi; v += 5) {
    s.appendChild(svg("line", { x1: PL, x2: W - PR, y1: Y(v), y2: Y(v), stroke: v === 0 ? "var(--ink)" : "var(--rule)", "stroke-width": 1 }));
    text(s, PL - 8, Y(v) + 4, (v > 0 ? "+" : "") + v + "%", { "text-anchor": "end" });
  }
  m.forEach((r, i) => {
    const v = r.lift_pct, x = PL + i * bw + 2;
    s.appendChild(svg("rect", { x, y: Math.min(Y(v), Y(0)), width: bw - 4, height: Math.abs(Y(v) - Y(0)),
      fill: v < 0 ? "var(--tide)" : "var(--proj)", rx: 1.5 }));
    if (i % 3 === 0) text(s, x + (bw - 4) / 2, H - 22, r.month, { "text-anchor": "middle" });
  });
  text(s, PL, H - 4, "Grey bars: months where it lost to the naive guess");
  document.getElementById("chart-month").appendChild(s);
}

/* ---------- 05: range coverage before and after calibration ---------- */
function covChart() {
  const rows = D.iv, W = 760, H = 230, PL = 92, PR = 60, PT = 12, PB = 36;
  const X = v => PL + ((v - 60) / 40) * (W - PL - PR);
  const s = svg("svg", { viewBox: `0 0 ${W} ${H}`, role: "img",
    "aria-label": "Share of test hours inside the 80 percent range, raw and calibrated, per horizon" });
  for (let v = 60; v <= 100; v += 10) {
    s.appendChild(svg("line", { x1: X(v), x2: X(v), y1: PT, y2: H - PB, stroke: v === 80 ? "var(--ink)" : "var(--rule)", "stroke-width": 1 }));
    text(s, X(v), H - PB + 18, v + "%", { "text-anchor": "middle" });
  }
  rows.forEach((r, i) => {
    const y = PT + 18 + i * 44;
    text(s, PL - 14, y + 4, r.horizon_h + " h ahead", { "text-anchor": "end", fill: "var(--ink)", "font-size": 13, "font-family": "var(--sans)" });
    s.appendChild(svg("line", { x1: X(r.raw_coverage_pct), x2: X(r.coverage_pct), y1: y, y2: y, stroke: "var(--rule-2)", "stroke-width": 2 }));
    s.appendChild(svg("circle", { cx: X(r.raw_coverage_pct), cy: y, r: 6, fill: "var(--tide)" }));
    s.appendChild(svg("circle", { cx: X(r.coverage_pct), cy: y, r: 6, fill: "var(--proj)" }));
    text(s, X(r.coverage_pct) + 12, y + 4, r.coverage_pct.toFixed(1) + "%", { fill: "var(--ink)", "font-weight": 700 });
    text(s, X(r.raw_coverage_pct) - 12, y + 4, r.raw_coverage_pct.toFixed(1) + "%", { "text-anchor": "end" });
  });
  text(s, PL, H - 4, "Grey: raw range. Amber: after calibration.");
  document.getElementById("chart-cov").appendChild(s);
}
maeChart(); monthChart(); covChart();

/* ---------- hero: the live forecast, read from the dashboard's own data ---------- */
(async () => {
  const when = document.getElementById("live-when"), chips = document.getElementById("live-cities"),
        body = document.getElementById("live-body");
  let data;
  try {
    const r = await fetch("/forecasts.json", { cache: "no-store" });
    if (!r.ok) throw new Error(r.status);
    data = await r.json();
  } catch (e) {
    when.textContent = "Could not load the live forecast. Open the dashboard instead.";
    return;
  }
  const main = data.cities.filter(c => D.cities.includes(c.id));
  const t = new Date(data.generated_at);
  when.textContent = "Forecast made " + t.toLocaleString("en-PH", { month: "short", day: "numeric", hour: "numeric", timeZone: "Asia/Manila" }) + " (Manila time)";
  const show = c => {
    chips.querySelectorAll("button").forEach(b => b.setAttribute("aria-pressed", b.dataset.id === c.id));
    const cell = (label, pm, aqi, cat, range) =>
      `<div class="lc"><span class="lc-h">${label}</span><b>${aqi}</b><span class="lc-c">${cat}</span>` +
      `<span class="lc-r">${pm} &micro;g/m&sup3;${range ? `<br>likely ${range}` : ""}</span></div>`;
    body.innerHTML = cell("Now", c.now.pm2_5, c.now.aqi, c.now.category) +
      c.forecast.map(f => cell("In " + f.horizon_h + " h", f.pm2_5, f.aqi, f.category,
        f.low != null ? f.low + " to " + f.high : "")).join("");
  };
  main.forEach(c => {
    const b = Object.assign(document.createElement("button"), { type: "button", className: "chip", textContent: c.name });
    b.dataset.id = c.id; b.addEventListener("click", () => show(c)); chips.appendChild(b);
  });
  if (main.length) show(main[0]);
})();

/* ---------- controls ---------- */
const root = document.documentElement;
function setView(v) {
  root.dataset.view = v;
  document.getElementById("m-plain").setAttribute("aria-pressed", v === "plain");
  document.getElementById("m-expert").setAttribute("aria-pressed", v === "expert");
  try { localStorage.setItem("hangin-view", v); } catch (e) {}
}
document.getElementById("m-plain").addEventListener("click", () => setView("plain"));
document.getElementById("m-expert").addEventListener("click", () => setView("expert"));
// same "theme" key as the dashboard, so the choice follows the reader across the site
document.getElementById("theme").addEventListener("click", () => {
  const next = root.dataset.theme === "dark" ? "light" : "dark";
  root.dataset.theme = next;
  try { localStorage.setItem("theme", next); } catch (e) {}
});
try { const v = localStorage.getItem("hangin-view"); if (v) setView(v); } catch (e) {}

/* ---------- chapter rail: built from each section's label, current one highlighted ---------- */
(() => {
  const rail = document.querySelector(".rail");
  const links = [...document.querySelectorAll("main section[id]")].map(sec => {
    const no = sec.querySelector(".console-head .step-no"), title = sec.querySelector(".console-head .caps");
    if (!no || !title) return null;
    const a = document.createElement("a");
    a.href = "#" + sec.id;
    a.innerHTML = `<span>${no.textContent.trim()}</span>${title.textContent.trim()}`;
    rail.appendChild(a);
    return [sec, a];
  }).filter(Boolean);
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (!e.isIntersecting) return;
    links.forEach(([sec, a]) => a.setAttribute("aria-current", sec === e.target));
  }), { rootMargin: "-45% 0px -50% 0px" });
  links.forEach(([sec]) => io.observe(sec));
})();

/* ---------- border glow: same maths as the portfolio's BorderGlow.jsx ---------- */
document.querySelectorAll(".console").forEach(card => {
  card.prepend(Object.assign(document.createElement("span"), { className: "edge-light" }));
  card.addEventListener("pointermove", e => {
    const r = card.getBoundingClientRect();
    const dx = e.clientX - r.left - r.width / 2, dy = e.clientY - r.top - r.height / 2;
    const edge = Math.min(Math.max(Math.abs(dx) / (r.width / 2), Math.abs(dy) / (r.height / 2)), 1);
    let angle = Math.atan2(dy, dx) * 180 / Math.PI + 90;
    if (angle < 0) angle += 360;
    card.style.setProperty("--edge", (edge * 100).toFixed(1));
    card.style.setProperty("--angle", angle.toFixed(1) + "deg");
  });
});

/* ---------- dot field: same approach as the portfolio's ParticleField.jsx ---------- */
(() => {
  const canvas = document.querySelector(".dot-field");
  const ctx = canvas.getContext("2d");
  const dpr = Math.min(devicePixelRatio || 1, 2), GAP = 22, RADIUS = 140;
  let dots = [], mouse = { x: -9999, y: -9999 }, raf = null, idle = 0, colours;
  const readColours = () => {
    const cs = getComputedStyle(root);
    colours = { dot: cs.getPropertyValue("--dot").trim() || "rgba(28,25,23,.13)",
                hot: cs.getPropertyValue("--proj").trim() || "#7c5800" };
  };
  const build = () => {
    canvas.width = innerWidth * dpr; canvas.height = innerHeight * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    dots = [];
    for (let x = GAP / 2; x < innerWidth; x += GAP)
      for (let y = GAP / 2; y < innerHeight; y += GAP) dots.push({ ox: x, oy: y, x, y });
  };
  const draw = () => {
    ctx.clearRect(0, 0, innerWidth, innerHeight);
    let moving = false;
    for (const d of dots) {
      const dx = mouse.x - d.ox, dy = mouse.y - d.oy, dist = Math.hypot(dx, dy);
      const t = dist < RADIUS ? 1 - dist / RADIUS : 0;
      const tx = d.ox + dx * 0.08 * t, ty = d.oy + dy * 0.08 * t;
      d.x += (tx - d.x) * 0.2; d.y += (ty - d.y) * 0.2;
      if (Math.abs(tx - d.x) > 0.05 || Math.abs(ty - d.y) > 0.05) moving = true;
      ctx.globalAlpha = t ? 0.35 + t * 0.65 : 1;
      ctx.fillStyle = t ? colours.hot : colours.dot;
      ctx.beginPath(); ctx.arc(d.x, d.y, (2 + t * 2) / 2, 0, 7); ctx.fill();
    }
    ctx.globalAlpha = 1;
    idle = mouse.x === -9999 && !moving ? idle + 1 : 0;
    raf = idle > 30 ? null : requestAnimationFrame(draw);
  };
  const wake = () => { if (raf === null) raf = requestAnimationFrame(draw); };
  readColours(); build(); draw();
  addEventListener("resize", () => { build(); wake(); });
  new MutationObserver(() => { readColours(); wake(); })
    .observe(root, { attributes: true, attributeFilter: ["data-theme"] });
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  addEventListener("pointermove", e => { mouse.x = e.clientX; mouse.y = e.clientY; wake(); }, { passive: true });
  document.addEventListener("pointerleave", () => { mouse.x = mouse.y = -9999; });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) wake(); });
})();
