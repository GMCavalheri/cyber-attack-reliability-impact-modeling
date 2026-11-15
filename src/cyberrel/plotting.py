"""Matplotlib style and the recurring chart of the project: time split by readiness status."""

from __future__ import annotations

from collections.abc import Mapping

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from cyberrel.metrics.readiness import STATUSES, StatusHours

PHYSICAL_COLOR = "#2f6db5"
CYBER_COLOR = "#c8452c"
BOTH_COLOR = "#7b4fa0"
NEUTRAL_COLOR = "#555555"
STATUS_COLORS = {
    "fmc": "#3a8f5c",
    "pmc": "#9cc9a8",
    "nmc_maintenance": PHYSICAL_COLOR,
    "nmc_cyber": CYBER_COLOR,
    "nmc_both": BOTH_COLOR,
}
STATUS_LABELS = {
    "fmc": "FMC",
    "pmc": "PMC",
    "nmc_maintenance": "NMC: physical",
    "nmc_cyber": "NMC: cyber",
    "nmc_both": "NMC: both",
}


def use_style() -> None:
    """A clean, consistent style for every figure in the repository (same as CPS-02)."""
    plt.rcParams.update(
        {
            "figure.dpi": 110,
            "savefig.dpi": 150,
            "savefig.bbox": "tight",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "font.size": 10,
        }
    )


def status_bars(
    statuses: Mapping[str, StatusHours],
    title: str = "",
    show: tuple[str, ...] = ("pmc", "nmc_maintenance", "nmc_cyber", "nmc_both"),
) -> Figure:
    """Horizontal stacked bars of the share of time in each status, one bar per case.

    FMC is usually most of the time, so by default it is left out and the bars show what
    is *not* FMC; the x axis is then in percent of possessed hours.
    """
    fig, ax = plt.subplots(figsize=(8, 0.6 * len(statuses) + 1.4))
    labels = list(statuses)
    left = [0.0] * len(labels)
    for status in STATUSES:
        if status not in show:
            continue
        widths = [100 * statuses[k].rate(getattr(statuses[k], status)) for k in labels]
        ax.barh(
            labels,
            widths,
            left=left,
            color=STATUS_COLORS[status],
            label=STATUS_LABELS[status],
        )
        left = [a + b for a, b in zip(left, widths, strict=True)]
    ax.invert_yaxis()
    ax.set_xlabel("share of possessed hours (%)")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=False)
    if title:
        ax.set_title(title)
    return fig
