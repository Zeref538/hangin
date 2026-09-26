"""Rebuild docs/backtest.png from data/backtest.json. Run: python ml/make_figure.py"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT / "data/backtest.json").read_text())["horizons"]
labels = [f"{r['horizon_h']} h ahead" for r in rows]
model = [r["model_mae"] for r in rows]
naive = [r["persistence_mae"] for r in rows]

fig, ax = plt.subplots(figsize=(8, 4.2), dpi=150)
x = range(len(rows))
w = 0.38
ax.bar([i - w / 2 - 0.01 for i in x], naive, w, color="#b8b7b0", label="Naive guess (air stays the same)")
ax.bar([i + w / 2 + 0.01 for i in x], model, w, color="#2a78d6", label="Hangin' model")
for i, r in enumerate(rows):
    ax.text(i - w / 2, naive[i] + 0.08, f"{naive[i]:.2f}", ha="center", fontsize=9, color="#52514e")
    ax.text(i + w / 2, model[i] + 0.08, f"{model[i]:.2f}", ha="center", fontsize=9, color="#0b0b0b")
    ax.text(i, max(naive[i], model[i]) + 0.55, f"{r['lift_pct']:.1f}% less error", ha="center",
            fontsize=10, fontweight="bold", color="#0b0b0b")
ax.set_xticks(list(x), labels)
ax.set_ylabel("Average miss, µg/m³ of PM2.5 (lower is better)", color="#52514e")
ax.set_ylim(0, max(naive) + 1.4)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", color="#e6e5e0", linewidth=0.8)
ax.set_axisbelow(True)
ax.legend(frameon=False, loc="upper left")
fig.suptitle("The model misses by less than a naive guess at every horizon", x=0.02, ha="left", fontsize=13, fontweight="bold")
ax.set_title(f"Each bar = average error over ~21,000 held-out hours, 5 PH cities pooled (one training run)",
             loc="left", fontsize=9, color="#52514e")
fig.tight_layout()
fig.savefig(ROOT / "docs/backtest.png")
print("wrote docs/backtest.png")
