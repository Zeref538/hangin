"""Build the case study page from the committed result files.

    python docs/make_figures.py && python docs/build_case_study.py

Writes web/public/case-study.html and web/public/case-study/app.js. Every number in
the copy is a {{placeholder}} filled from data/*.json here, and the claims the prose
makes are re-checked against the data, so a re-run with new results either updates
the page or fails loudly instead of leaving a stale or false sentence.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS, PUB = ROOT / "docs", ROOT / "web" / "public"
ld = lambda name: json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))

# the live dashboard's cities that the tests cover
CITIES = ["manila", "quezon_city", "cebu", "davao", "baguio"]

# widget styles for the live forecast box (the rest is LiitLLM's CSS, docs/case_study.css)
EXTRA_CSS = """
.live-body { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 1px;
  background: var(--rule); border-top: 1px solid var(--rule); }
.lc { background: var(--card); padding: 14px 12px; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.lc-h { font-size: 12px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-3); }
.lc b { font-size: 30px; font-weight: 600; letter-spacing: -.04em; line-height: 1.1; color: var(--proj); }
.lc-c { font-size: 12.5px; color: var(--ink); line-height: 1.3; }
.lc-r { font-family: var(--mono); font-size: 11px; color: var(--ink-3); margin-top: 4px; }
#live .chip[aria-pressed="true"] { background: var(--ink); color: var(--paper); border-color: var(--ink); }
@media (max-width: 700px) { .live-body { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .lc:first-child { grid-column: 1 / -1; } }
"""


def main():
    wf, iv, bt = ld("walkforward.json"), ld("intervals.json"), ld("backtest.json")
    le, att, gt = ld("live_eval.json"), ld("attempt_24h.json"), ld("ground_truth.json")
    W = {r["horizon_h"]: r for r in wf["horizons"]}
    cov = [r["coverage_pct"] for r in iv["horizons"]]
    raw = [r["raw_coverage_pct"] for r in iv["horizons"]]
    A = att["results"]
    pct = lambda arm: 100 * (A["base"]["24"]["mean"] - A[arm]["24"]["mean"]) / A["base"]["24"]["mean"]
    start, end = wf["test_period"].split("..")
    sm = ld("sensor_model.json")
    S = {r["horizon_h"]: r for r in sm["horizons"]}
    sm_lifts = [r["model_a_vs_best_baseline_pct"] for r in S.values()]

    v = {
        **{f"lift{h}": f"{W[h]['retrained_lift_pct']:.1f}" for h in (1, 6, 12, 24)},
        "shipped_lift1": f"{W[1]['shipped_lift_pct']:.1f}",
        "seed_std_max": f"{max(r['retrained_mae_std'] for r in W.values()):.3f}",
        "n_test": f"{min(r['n_test'] for r in W.values()):,}",
        "wf_start": start, "wf_end": end,
        "cov_min": f"{min(cov):.0f}", "cov_max": f"{max(cov):.0f}",
        "raw_min": f"{min(raw):.0f}", "raw_max": f"{max(raw):.0f}",
        "orig_lift1": f"{bt['horizons'][0]['lift_pct']:.1f}",
        "live_lift1": f"{next(r for r in le['horizons'] if r['horizon_h'] == 1)['lift_pct']:.1f}",
        "n_features": str(len(bt["features"])),
        "att_base": f"{A['base']['24']['mean']:.3f}",
        **{f"att_{a}": f"{A[a]['24']['mean']:.3f}" for a in ("a1", "a2", "a12")},
        **{f"att_{a}_pct": f"{pct(a):.1f}" for a in ("a1", "a2", "a12")},
        "gt_sensors": str(gt["sensors"]), "gt_hours": f"{gt['hours']:,}",
        "gt_r_hour": f"{gt['correlation_hourly']:.2f}", "gt_r_day": f"{gt['correlation_daily']:.2f}",
        "gt_cams": f"{gt['cams_mae_vs_ground']:.2f}", "gt_naive": f"{gt['naive24_mae_vs_ground']:.2f}",
        "sm_train": sm["train"].replace("..", " to "),
        "sm_a6": f"{S[6]['model_a_mae']:.2f}",
        "sm_best6": f"{min(S[6][k] for k in ('persist_mae', 'yday_mae', 'cams_mae')):.2f}",
        "sm_lift_min": f"{min(sm_lifts):.1f}", "sm_lift_max": f"{max(sm_lifts):.1f}",
    }

    # the prose makes these claims; if the data stops supporting one, stop the build
    assert all(r["retrained_lift_pct"] > 0 for r in W.values()), "no longer beats naive at every horizon"
    assert max(W, key=lambda h: W[h]["retrained_lift_pct"]) == 12, "12 h is no longer the best horizon"
    assert min(W, key=lambda h: W[h]["retrained_lift_pct"]) == 24, "24 h is no longer the weakest"
    assert W[1]["retrained_lift_pct"] > W[1]["shipped_lift_pct"], "retraining no longer helps 1 h"
    assert min(cov) >= 80 > max(raw), "coverage story changed"
    assert att["ship"] is None and 0 < pct("a12") < 2, "attempt outcome changed"
    assert gt["correlation_daily"] > gt["correlation_hourly"], "sensor check story changed"
    assert abs(gt["cams_mae_vs_ground"] - gt["naive24_mae_vs_ground"]) < 0.5, "'about as much' no longer true"
    assert min(sm_lifts) > 0, "sensor-trained model no longer beats every simple guess"
    assert any(m["lift_pct"] < 0 for m in le["by_month"] if m["horizon_h"] == 1), "no losing month"

    html = (DOCS / "case_study.html").read_text(encoding="utf-8")
    css = (DOCS / "case_study.css").read_text(encoding="utf-8") + EXTRA_CSS
    html = html.replace("/*%%CSS%%*/", css)
    html = re.sub(r"\{\{(\w+)\}\}", lambda m: v[m.group(1)], html)
    left = re.findall(r"\{\{\w+\}\}", html)
    assert not left, f"unfilled: {left}"
    assert "—" not in html and "&mdash;" not in html, "em dash in copy"

    data = {"wf": [W[h] for h in sorted(W)], "iv": iv["horizons"], "cities": CITIES,
            "months": [m for m in le["by_month"] if m["horizon_h"] == 1]}
    app = (DOCS / "case_study_app.js").read_text(encoding="utf-8")
    app = app.replace("/*%%DATA%%*/", json.dumps(data, separators=(",", ":")))

    # content hash in the script URL: a changed app.js gets a new address, so no stale cache
    tag = hashlib.sha256(app.encode()).hexdigest()[:10]
    html = html.replace('src="case-study/app.js"', f'src="case-study/app.js?v={tag}"')
    (PUB / "case-study").mkdir(parents=True, exist_ok=True)
    (PUB / "case-study.html").write_text(html, encoding="utf-8")
    (PUB / "case-study" / "app.js").write_text(app, encoding="utf-8")
    print(f"wrote web/public/case-study.html ({len(html):,} bytes) and case-study/app.js")
    print("  " + ", ".join(f"{k}={v[k]}" for k in ("lift1", "lift12", "lift24", "cov_min", "cov_max", "n_test")))


if __name__ == "__main__":
    main()
