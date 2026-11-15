"""Phase 5: where mitigation matters — redundancy vs detection time, tornado, mitigations."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

from cyberrel import plotting
from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.sensitivity_analysis import evaluate_mitigations, redundancy_detection_grid, tornado
from cyberrel.system_model import navigation_system

from common import FIGURES, fmt, table, write_result

DETECT = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0)
CHANNELS = (1, 2, 3)
COMPUTERS = (1, 2)
TOP = 14


def pivot(points, row_of, rows, metric):  # type: ignore[no-untyped-def]
    grid = np.zeros((len(rows), len(DETECT)))
    for p in points:
        grid[rows.index(row_of(p)), DETECT.index(p.design.detect_scale)] = metric(p)
    return grid


def main() -> None:
    scenarios = list(load_scenarios().values())
    bus = redundancy_detection_grid(scenarios, CHANNELS, DETECT)
    mc = [
        p
        for n in COMPUTERS
        for p in redundancy_detection_grid(scenarios, (2,), DETECT, mission_computers=n)
    ]

    def unavail(p):  # type: ignore[no-untyped-def]
        return p.combined.unavailability

    def mtbf(p):  # type: ignore[no-untyped-def]
        return p.combined.mtbf

    headers = ["", *[f"detect × {k:g}" for k in DETECT], "physical only"]
    bus_u = pivot(bus, lambda p: p.design.bus_channels, list(CHANNELS), unavail)
    bus_rows = [
        [
            f"{n} bus channel{'s' if n > 1 else ''}",
            *bus_u[i],
            next(p.physical.unavailability for p in bus if p.design.bus_channels == n),
        ]
        for i, n in enumerate(CHANNELS)
    ]
    mc_u = pivot(mc, lambda p: p.design.mission_computers, list(COMPUTERS), unavail)
    mc_rows = [
        [
            f"{n} mission computer{'s' if n > 1 else ''}",
            *mc_u[i],
            next(p.physical.unavailability for p in mc if p.design.mission_computers == n),
        ]
        for i, n in enumerate(COMPUTERS)
    ]
    mc_mtbf = pivot(mc, lambda p: p.design.mission_computers, list(COMPUTERS), mtbf)
    mtbf_rows = [
        [
            f"{n} mission computer{'s' if n > 1 else ''}",
            *mc_mtbf[i],
            next(p.physical.mtbf for p in mc if p.design.mission_computers == n),
        ]
        for i, n in enumerate(COMPUTERS)
    ]

    system = navigation_system()
    bars = tornado(system, scenarios)
    tornado_table = table(
        ["parameter", "origin", "1 − A at ×0.5", "1 − A at ×1.5", "swing"],
        [[b.parameter, b.origin, b.low, b.high, b.swing] for b in bars[:TOP]],
    )
    mitigations = evaluate_mitigations(scenarios)
    mitigation_table = table(
        [
            "mitigation",
            "kind",
            "1 − A after",
            "unavailability removed",
            "system MTBF ×",
            "FMC rate change",
        ],
        [
            [
                r.name,
                r.kind,
                r.result.unavailability,
                f"{100 * r.unavailability_reduction:.1f} %",
                r.mtbf_gain,
                r.fmc_gain,
            ]
            for r in mitigations
        ],
    )
    base = mitigations[0].baseline
    write_result(
        "sensitivity",
        "Phase 5 · Sensitivity to redundancy and detection time",
        [
            (
                "Unavailability: bus channels × time-to-detect multiplier (all scenarios)",
                table(headers, bus_rows),
            ),
            (
                "Unavailability: mission computers × time-to-detect multiplier (2 bus channels)",
                table(headers, mc_rows),
            ),
            (
                "System MTBF (h): mission computers × time-to-detect multiplier",
                table(headers, mtbf_rows),
            ),
            (
                f"Tornado: each parameter × 0.5 and × 1.5 "
                f"(baseline 1 − A = {fmt(base.unavailability)}), top {TOP}",
                tornado_table,
            ),
            ("Mitigations, each alone, largest unavailability cut first", mitigation_table),
        ],
    )

    plotting.use_style()
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.4), sharey=False)
    for ax, data, rows, label in (
        (axes[0], bus_u, CHANNELS, "bus channels"),
        (axes[1], mc_u, COMPUTERS, "mission computers"),
    ):
        im = ax.imshow(1e4 * data, aspect="auto", cmap="Reds", origin="lower")
        ax.set_xticks(range(len(DETECT)), [f"{k:g}" for k in DETECT])
        ax.set_yticks(range(len(rows)), [str(r) for r in rows])
        ax.set_xlabel("time-to-detect multiplier")
        ax.set_ylabel(label)
        ax.grid(False)
        for i in range(len(rows)):
            for j in range(len(DETECT)):
                ax.text(j, i, f"{1e4 * data[i, j]:.1f}", ha="center", va="center", fontsize=8)
        fig.colorbar(im, ax=ax, label="unavailability (h per 10 000 h)")
    axes[0].set_title("Beyond two bus channels, nothing changes")
    axes[1].set_title("Adding a mission computer: one constant step")
    fig.savefig(FIGURES / "sensitivity_heatmaps.png")
    plt.close(fig)

    shown = bars[:TOP][::-1]
    fig, ax = plt.subplots(figsize=(8, 5))
    centre = base.unavailability
    for i, b in enumerate(shown):
        color = plotting.CYBER_COLOR if b.origin == "cyber" else plotting.PHYSICAL_COLOR
        lo, hi = sorted((b.low, b.high))
        ax.barh(i, 1e4 * (hi - lo), left=1e4 * lo, color=color)
    ax.axvline(1e4 * centre, color=plotting.NEUTRAL_COLOR, lw=1)
    ax.set_yticks(range(len(shown)), [b.parameter for b in shown], fontsize=8)
    ax.set_xlabel("unavailability (h per 10 000 h), parameter × 0.5 to × 1.5")
    ax.set_title("Tornado: what moves the function's unavailability")
    ax.legend(
        handles=[
            Patch(color=plotting.CYBER_COLOR, label="cyber parameter"),
            Patch(color=plotting.PHYSICAL_COLOR, label="physical parameter"),
        ],
        fontsize=8,
        loc="lower right",
    )
    fig.savefig(FIGURES / "sensitivity_tornado.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(7.5, 3.6))
    names = [r.name for r in mitigations][::-1]
    cuts = [100 * r.unavailability_reduction for r in mitigations][::-1]
    colors = [
        plotting.PHYSICAL_COLOR if r.kind.startswith("physical") else plotting.CYBER_COLOR
        for r in mitigations
    ][::-1]
    ax.barh(names, cuts, color=colors)
    ax.set_xlabel("share of the function's unavailability removed (%)")
    ax.set_title("Each mitigation alone, against physical failures and all four scenarios")
    fig.savefig(FIGURES / "sensitivity_mitigations.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
