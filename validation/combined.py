"""Phase 4: a synthetic fleet simulated under physical failures and attacks together."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np

from cyberrel import plotting
from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.attack_to_metric_translation import combined_steady_state
from cyberrel.combined_monte_carlo_simulation import simulate_fleet
from cyberrel.system_model import navigation_system

from common import FIGURES, table, write_result

SEED = 20261115
PLATFORMS = 24
YEARS = 10
HORIZON = YEARS * 8760.0
CONFIDENCE = 0.95


def main() -> None:
    system = navigation_system()
    scenarios = list(load_scenarios().values())
    cases = {
        "physical only": (simulate_fleet(system, [], PLATFORMS, HORIZON, SEED), []),
        "physical + cyber": (
            simulate_fleet(system, scenarios, PLATFORMS, HORIZON, SEED),
            scenarios,
        ),
    }

    rows = []
    for label, (fleet, scen) in cases.items():
        exact = combined_steady_state(system, scen)
        for metric, value in (
            ("availability (= MC rate)", exact.availability),
            ("failure frequency (/h)", exact.failure_frequency),
            ("FMC share", exact.status.fmc),
            ("NMC share, physical", exact.status.nmc_maintenance),
            ("NMC share, cyber", exact.status.nmc_cyber),
        ):
            key = {
                "availability (= MC rate)": "availability",
                "failure frequency (/h)": "failure_frequency",
                "FMC share": "fmc",
                "NMC share, physical": "nmc_maintenance",
                "NMC share, cyber": "nmc_cyber",
            }[metric]
            e = fleet.estimate(key, CONFIDENCE)
            rows.append(
                [label, metric, value, e.mean, e.low, e.high, "yes" if e.contains(value) else "NO"]
            )
    agreement = table(
        ["case", "metric", "exact", "simulated mean", "95 % low", "95 % high", "inside"], rows
    )

    fleet = cases["physical + cyber"][0]
    log_rows = []
    for label, causes in (
        ("all outages", None),
        ("physical", {"physical"}),
        ("cyber", {"cyber"}),
        ("both", {"both"}),
    ):
        k = fleet.kpis(causes)
        log_rows.append([label, k.failure_count, k.down_hours, k.mtbf, k.mttr])
    kpis = table(
        ["outage cause", "outages", "down hours", "MTBF (h, dashboard formula)", "MTTR (h)"],
        log_rows,
    )
    physical = cases["physical only"][0].kpis()
    combined = fleet.kpis()
    headline = table(
        ["metric (fleet, dashboard formulas)", "physical only", "physical + cyber"],
        [
            ["platform-hours", cases["physical only"][0].possessed_hours, fleet.possessed_hours],
            ["function-loss events", physical.failure_count, combined.failure_count],
            ["MTBF (h)", physical.mtbf, combined.mtbf],
            ["MTTR (h)", physical.mttr, combined.mttr],
            ["availability", physical.availability, combined.availability],
            ["MC rate", cases["physical only"][0].status.mc_rate, fleet.status.mc_rate],
            ["FMC rate", cases["physical only"][0].status.fmc_rate, fleet.status.fmc_rate],
        ],
    )
    reduction = table(
        ["check", "value"],
        [
            [
                "largest per-platform difference between physical-alone down hours (attacked "
                "run) and down hours (physical-only run)",
                max(
                    abs(a.physical_down_hours - p.status.nmc)
                    for a, p in zip(fleet.runs, cases["physical only"][0].runs, strict=True)
                ),
            ]
        ],
    )
    write_result(
        "combined",
        "Phase 4 · Combined physical + cyber Monte Carlo",
        [
            (
                f"Fleet: {PLATFORMS} platforms × {YEARS} years ({HORIZON:g} h each), seed {SEED}",
                headline,
            ),
            ("Simulation against the exact steady state", agreement),
            ("The outage log by cause", kpis),
            ("Exact reduction: attacks do not change the physical history", reduction),
        ],
    )

    plotting.use_style()
    fig = plotting.status_bars(
        {
            "physical only (exact)": combined_steady_state(system).status,
            "physical only (simulated)": cases["physical only"][0].status,
            "physical + cyber (exact)": combined_steady_state(system, scenarios).status,
            "physical + cyber (simulated)": fleet.status,
        },
        title=f"Fleet of {PLATFORMS} for {YEARS} years: time not fully mission capable",
    )
    fig.savefig(FIGURES / "combined_status.png")
    plt.close(fig)

    color = {
        "physical": plotting.PHYSICAL_COLOR,
        "cyber": plotting.CYBER_COLOR,
        "both": plotting.BOTH_COLOR,
    }
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for run in fleet.runs:
        for cause, c in color.items():
            t = [o.start / 8760 for o in run.outages if o.cause == cause]
            ax.vlines(t, run.platform + 0.1, run.platform + 0.9, color=c, lw=0.8)
    for cause, c in color.items():
        ax.plot([], [], color=c, lw=3, label=cause)
    ax.set_xlim(0, YEARS)
    ax.set_ylim(0, PLATFORMS)
    ax.set_xlabel("years")
    ax.set_ylabel("platform")
    ax.grid(False)
    ax.set_title(f"Every loss of the navigation function across the fleet ({len(fleet.outages)})")
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0), fontsize=8, frameon=False)
    fig.savefig(FIGURES / "combined_timeline.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    bins = np.logspace(-2, 2, 33)
    for cause in ("physical", "cyber"):
        d = [o.duration for o in fleet.outages if o.cause == cause]
        ax.hist(
            d, bins=bins, color=color[cause], histtype="step", lw=2, label=f"{cause} ({len(d)})"
        )
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("outage length (h)")
    ax.set_ylabel("outages")
    ax.set_title("Cyber outages are many and short; physical ones few and long")
    ax.legend(fontsize=8)
    fig.savefig(FIGURES / "combined_outage_lengths.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
