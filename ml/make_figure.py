"""Rebuild docs/backtest.png from data/walkforward.json. Run: python ml/make_figure.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
wf = json.loads((ROOT / "data/walkforward.json").read_text())
rows = wf["horizons"]
series = [("naive_mae", "Naive guess (air stays the same)", "#b8b7b0"),
          ("shipped_mae", "Model trained once on 2022–2024", "#eb6834"),
          ("retrained_mae_mean", "Same model, retrained on newer data", "#2a78d6")]

fig, ax = plt.subplots(figsize=(8.6, 4.4), dpi=150)
w = 0.27
for k, (key, label, color) in enumerate(series):
    xs = [i + (k - 1) * (w + 0.01) for i in range(len(rows))]
    vals = [r[key] for r in rows]
    ax.bar(xs, vals, w, color=color, label=label)
    for x, v in zip(xs, vals):
        ax.text(x, v + 0.08, f"{v:.2f}", ha="center", fontsize=8, color="#52514e")
for i, r in enumerate(rows):
    top = max(r["naive_mae"], r["shipped_mae"])
    ax.text(i, top + 0.35, f"{r['retrained_lift_pct']:.0f}% less error\nthan naive", ha="center",
            fontsize=10, fontweight="bold", color="#0b0b0b")
ax.set_xticks(range(len(rows)), [f"{r['horizon_h']} h ahead" for r in rows])
ax.set_ylabel("Average miss, µg/m³ of PM2.5 (lower is better)", color="#52514e")
ax.set_ylim(0, max(r["naive_mae"] for r in rows) + 2.0)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left", fontsize=9)
start, end = wf["test_period"].split("..")
fig.suptitle("Retrained monthly, the model beats a naive guess at every horizon",
             x=0.02, ha="left", fontsize=13, fontweight="bold")
ax.set_title(f"Each bar = average error over one unseen year ({start} to {end}), 5 PH cities.\n"
             f"Retrained bars = mean of {len(wf['seeds'])} seeds (spread ≤ 0.003)",
             loc="left", fontsize=8.5, color="#52514e")
fig.tight_layout()
fig.savefig(ROOT / "docs/backtest.png")
print("wrote docs/backtest.png")
