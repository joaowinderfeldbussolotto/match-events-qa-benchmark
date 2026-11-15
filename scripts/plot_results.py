"""Draw the README results chart: accuracy on the questions with an answer,
by arm and model, from the results files in data/benchmark/.

Writes a light and a dark PNG to docs/img/. No model is called.

    python scripts/plot_results.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BENCH = ROOT / "data" / "benchmark"
OUT = ROOT / "docs" / "img"

# (label, results file); the order is the legend order
MODELS = [
    ("Claude Haiku 5.5 · closed, cheap", "claude-haiku-5.5_results.jsonl"),
    ("Qwen3.8-flash · open weights, cheap", "qwen3.8-flash_results.jsonl"),
    ("Claude Sonnet 4.6 · closed, expensive", "claude-sonnet-4.6_results.jsonl"),
    ("Kimi K3 · open weights, expensive", "kimi-k3_results.jsonl"),
]
ARMS = ["graph_tools", "text_to_cypher", "events_in_prompt", "vector", "stats_in_prompt", "no_context"]

THEMES = {
    "light": {"surface": "#fcfcfb", "text": "#0b0b0b", "muted": "#52514e", "grid": "#e6e5e1",
              "series": ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]},
    "dark": {"surface": "#1a1a19", "text": "#f0efec", "muted": "#c3c2b7", "grid": "#383835",
             "series": ["#3987e5", "#d95926", "#199e70", "#c98500"]},
}


def accuracy(path: Path) -> dict[str, tuple[int, int]]:
    """(correct, total) per arm, on the questions that have an answer."""
    out: dict[str, list[int]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row["type"] == "unanswerable":
            continue
        c = out.setdefault(row["arm"], [0, 0])
        c[0] += bool(row["correct"])
        c[1] += 1
    return {arm: (c[0], c[1]) for arm, c in out.items()}


def draw(data: list[dict[str, tuple[int, int]]], theme: str) -> Path:
    t = THEMES[theme]
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    fig, ax = plt.subplots(figsize=(9, 6.2), dpi=200)
    fig.patch.set_facecolor(t["surface"])
    ax.set_facecolor(t["surface"])

    n = len(MODELS)
    bar_h = 0.19
    for i, (label, _) in enumerate(MODELS):
        ys = [a + (i - (n - 1) / 2) * bar_h for a in range(len(ARMS))]
        vals = [100 * data[i][arm][0] / data[i][arm][1] for arm in ARMS]
        ax.barh(ys, vals, height=bar_h, color=t["series"][i], label=label,
                edgecolor=t["surface"], linewidth=1.0, zorder=3)
        for y, v in zip(ys, vals):
            ax.text(v + 1, y, f"{v:.0f}%", va="center", ha="left", fontsize=7.5, color=t["muted"], zorder=4)

    ax.set_yticks(range(len(ARMS)))
    ax.set_yticklabels(ARMS, fontfamily="DejaVu Sans Mono", fontsize=10, color=t["text"])
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xticks(range(0, 101, 20))
    ax.set_xticklabels([f"{x}%" for x in range(0, 101, 20)], color=t["muted"], fontsize=9)
    ax.xaxis.grid(True, color=t["grid"], linewidth=0.8, zorder=0)
    ax.tick_params(length=0, pad=6)
    for side in ("top", "right", "bottom"):
        ax.spines[side].set_visible(False)
    ax.spines["left"].set_color(t["muted"])
    ax.spines["left"].set_linewidth(0.8)

    total = data[0]["graph_tools"][1]
    fig.suptitle("Accuracy by arm and model", x=0.02, ha="left", y=0.975,
                 fontsize=14, fontweight="bold", color=t["text"])
    fig.text(0.02, 0.915, f"{total} questions with an answer · 2022 World Cup final · one repeat per question",
             ha="left", fontsize=9.5, color=t["muted"])
    leg = ax.legend(loc="lower right", frameon=False, fontsize=8.5, labelcolor=t["text"],
                    handlelength=1.2, handleheight=1.0)
    for h in leg.legend_handles:
        h.set_edgecolor(t["surface"])
    fig.subplots_adjust(left=0.18, right=0.97, top=0.86, bottom=0.06)

    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"accuracy-{theme}.png"
    fig.savefig(path, facecolor=t["surface"])
    plt.close(fig)
    return path


def main() -> None:
    data = [accuracy(BENCH / f) for _, f in MODELS]
    for theme in THEMES:
        print(draw(data, theme).relative_to(ROOT))


if __name__ == "__main__":
    main()
