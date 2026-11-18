"""Chart the synthetic revenue bridge and the monthly budget-versus-actual.

Labels are formatted from the model. The figure is written by this module;
it is not a picture drawn by hand.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from fpa_driver_model.money import fmt_money
from fpa_driver_model.synthetic import CompanyModel
from fpa_driver_model.variance import revenue_bridge

PAPER = "#F4F1EA"
INK = "#1C2430"
NAVY = "#1F3A5F"
STEEL = "#8FA4B8"
GREEN = "#2F6F4E"
GOLD = "#B0893E"
RED = "#8C3A3A"
GRID = "#E3DACE"
MUTED = "#5E6A75"


def render_chart(model: CompanyModel, output: Path) -> Path:
    """Write a PNG of the FY 2025 revenue bridge and monthly revenue."""
    bridge = revenue_bridge(model)
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams["font.family"] = "DejaVu Sans"
    fig = plt.figure(figsize=(11.4, 6.5), dpi=140, facecolor=PAPER)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.02, 1.18], wspace=0.32)
    left = fig.add_subplot(grid[0, 0])
    right = fig.add_subplot(grid[0, 1])
    _waterfall(left, bridge.budget_revenue, bridge.volume, bridge.price, bridge.actual_revenue)
    _monthly(right, model)
    fig.suptitle(
        "Fairhaven Metrics LLC — FY 2025 revenue (synthetic)",
        fontsize=14,
        color=NAVY,
        x=0.06,
        ha="left",
        y=0.98,
    )
    fig.text(
        0.06,
        0.915,
        "Computed by fpa-model from the synthetic drivers. Not real financials.",
        fontsize=8.5,
        color=MUTED,
        ha="left",
    )
    fig.text(
        0.06,
        0.035,
        "SYNTHETIC DATA  ·  fictional B2B SaaS company  ·  variance = actual − budget",
        fontsize=8,
        color=MUTED,
        ha="left",
    )
    fig.subplots_adjust(left=0.07, right=0.98, top=0.82, bottom=0.16)
    fig.savefig(output, facecolor=fig.get_facecolor())
    plt.close(fig)
    return output


def _waterfall(ax: Axes, budget: Decimal, volume: Decimal, price: Decimal, actual: Decimal) -> None:
    steps = [
        ("FY 2025\nbudget", budget, Decimal(0)),
        ("Volume", volume, budget),
        ("Price", price, budget + volume),
        ("FY 2025\nactual", actual, Decimal(0)),
    ]
    colors = [STEEL, GREEN if volume >= 0 else RED, GOLD if price >= 0 else RED, NAVY]
    xs = list(range(len(steps)))
    for index, ((_label, amount, base), color) in enumerate(zip(steps, colors, strict=True)):
        ax.bar(index, float(amount), bottom=float(base), color=color, width=0.62, zorder=3)
        if index in {1, 2}:
            ax.plot(
                [index - 0.62, index + 0.31],
                [float(base), float(base)],
                color=MUTED,
                linewidth=0.6,
                zorder=2,
            )
        top = base + amount if amount >= 0 else base
        ax.text(
            index,
            float(top),
            fmt_money(amount),
            ha="center",
            va="bottom",
            fontsize=8,
            color=INK,
            zorder=4,
        )
    ax.set_xticks(xs, [step[0] for step in steps])
    ax.set_title("Revenue bridge", loc="left", color=INK, fontsize=11, pad=8)
    _style_axis(ax)
    highest = max(budget, budget + volume, budget + volume + price, actual)
    ax.set_ylim(0, float(highest) * 1.28)
    ax.yaxis.set_major_formatter(lambda value, _pos: f"${value / 1_000_000:.1f}m")


def _monthly(ax: Axes, model: CompanyModel) -> None:
    labels = [month.label[:3] for month in model.actuals]
    xs = list(range(len(labels)))
    width = 0.38
    budget = [float(month.revenue) for month in model.budget]
    actual = [float(month.revenue) for month in model.actuals]
    ax.bar([x - width / 2 for x in xs], budget, width=width, color=STEEL, label="Budget", zorder=3)
    ax.bar([x + width / 2 for x in xs], actual, width=width, color=NAVY, label="Actual", zorder=3)
    ax.set_xticks(xs, labels)
    ax.set_title("Monthly revenue", loc="left", color=INK, fontsize=11, pad=10)
    legend = ax.legend(frameon=False, fontsize=8, loc="upper left")
    for text in legend.get_texts():
        text.set_color(INK)
    _style_axis(ax)
    peak = max([*budget, *actual])
    ax.set_ylim(0, peak * 1.22)
    ax.yaxis.set_major_formatter(lambda value, _pos: f"${value / 1000:.0f}k")


def _style_axis(ax: Axes) -> None:
    ax.set_facecolor(PAPER)
    ax.tick_params(colors=MUTED, labelsize=8)
    ax.grid(axis="y", color=GRID, linewidth=0.8, zorder=0)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(GRID)
    ax.spines["bottom"].set_color(GRID)
    ax.yaxis.label.set_color(MUTED)
