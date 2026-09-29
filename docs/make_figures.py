"""Draw the case study's table image from the committed result files.

    python docs/make_figures.py

Writes web/public/case-study/img/results.png: a Word-style table (dark header row,
thin borders, on white) of the full-year walk-forward test and the band coverage.
Every cell is read from data/walkforward.json and data/intervals.json.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "web" / "public" / "case-study" / "img" / "results.png"
wf = json.loads((ROOT / "data" / "walkforward.json").read_text())
iv = {h["horizon_h"]: h for h in json.loads((ROOT / "data" / "intervals.json").read_text())["horizons"]}

head = ["Horizon", "Retrained model\nMAE (3 seeds)", "Trained once\n(2024) MAE",
        "Naive guess\nMAE", "Less error\nthan naive", "80% range\nhit rate"]
rows = [[f"{r['horizon_h']} h ahead",
         f"{r['retrained_mae_mean']:.2f} ± {r['retrained_mae_std']:.3f}",
         f"{r['shipped_mae']:.2f}", f"{r['naive_mae']:.2f}",
         f"{r['retrained_lift_pct']:.1f}%", f"{iv[r['horizon_h']]['coverage_pct']:.1f}%"]
        for r in wf["horizons"]]

fig, ax = plt.subplots(figsize=(10, 2.9), dpi=160)
ax.axis("off")
t = ax.table(cellText=rows, colLabels=head, loc="center", cellLoc="center")
t.auto_set_font_size(False)
t.set_fontsize(10.5)
t.scale(1, 2.1)
for (r, c), cell in t.get_celld().items():
    cell.set_edgecolor("#1c1917")
    cell.set_linewidth(0.6)
    if r == 0:
        cell.set_facecolor("#1c1917")
        cell.get_text().set_color("#ffffff")
        cell.get_text().set_fontweight("bold")
        cell.set_height(cell.get_height() * 1.35)
    else:
        cell.set_facecolor("#ffffff")
        cell.get_text().set_color("#1c1917")
        if c == 0:
            cell.get_text().set_fontweight("bold")
start, end = wf["test_period"].split("..")
fig.suptitle(f"One unseen year ({start} to {end}), 5 Philippine cities. MAE = average miss in µg/m³ of PM2.5, lower is better.",
             fontsize=9.5, color="#57534e", y=0.06)
fig.patch.set_facecolor("#ffffff")
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, bbox_inches="tight", facecolor="#ffffff")
print(f"wrote {OUT.relative_to(ROOT)}")
