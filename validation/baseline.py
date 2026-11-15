"""Phase 1: the physical reliability baseline of the navigation system, in closed form."""

from __future__ import annotations

import matplotlib.pyplot as plt

from cyberrel import plotting
from cyberrel.system_model import (
    MISSION_HOURS,
    availabilities,
    birnbaum_importance,
    component_availability,
    mission_reliability,
    navigation_system,
    steady_state,
    steady_state_status,
)
from cyberrel.system_model.closed_form import failure_frequencies
from cyberrel.system_model.navigation import load_parameters

from common import FIGURES, table, write_result


def main() -> None:
    system = navigation_system()
    rows = load_parameters()
    a = availabilities(system)
    ib = birnbaum_importance(system, a)
    nu = failure_frequencies(system)
    ss = steady_state(system)
    status = steady_state_status(system)
    r_mission = mission_reliability(system, MISSION_HOURS)
    share = {n: nu[n] * ib[n] / ss.failure_frequency for n in system.names}

    components = table(
        ["component", "group", "λ (/h)", "MTBF (h)", "MTTR (h)", "A", "Birnbaum", "share of ω"],
        [
            [
                c.name,
                c.group,
                c.failure_rate,
                c.mtbf,
                c.mttr,
                component_availability(c),
                ib[c.name],
                share[c.name],
            ]
            for c in system.components
        ],
    )
    basis = table(["component", "basis"], [[r.name, r.basis] for r in rows.values()])
    summary = table(
        ["metric", "value"],
        [
            ["structure", f"`{system.summary()}`"],
            ["steady-state availability A", ss.availability],
            ["unavailability 1 − A", ss.unavailability],
            ["system failure frequency ω (/h)", ss.failure_frequency],
            ["system MTBF = A/ω (h)", ss.mtbf],
            ["system MDT = (1 − A)/ω (h)", ss.mdt],
            [
                f"mission reliability, {MISSION_HOURS:g} h, no repair",
                r_mission,
            ],
            [
                f"mission unreliability, {MISSION_HOURS:g} h",
                1 - r_mission,
            ],
        ],
    )
    readiness = table(
        ["status", "share of possessed hours"],
        [
            ["FMC", status.fmc_rate],
            ["PMC", status.pmc_rate],
            ["MC = FMC + PMC", status.mc_rate],
            ["NMC (maintenance)", status.nmc_rate],
        ],
    )
    redundancy_rows = []
    for e in (1, 2, 3):
        for b in (1, 2, 3):
            variant = navigation_system(e, b)
            s_v, st_v = steady_state(variant), steady_state_status(variant)
            redundancy_rows.append(
                [e, b, s_v.unavailability, s_v.mtbf, st_v.nmc_rate, st_v.pmc_rate]
            )
    redundancy = table(
        ["EGI units", "bus channels", "1 − A", "MTBF (h)", "NMC rate", "PMC rate"],
        redundancy_rows,
    )
    write_result(
        "baseline",
        "Phase 1 · Physical reliability baseline",
        [
            ("Summary", summary),
            ("Components", components + "\n" + basis),
            ("Mission-capable status (physical failures only)", readiness),
            ("Redundancy variants", redundancy),
        ],
    )

    plotting.use_style()
    fig, ax = plt.subplots(figsize=(7, 3.2))
    names = sorted(share, key=share.get)  # type: ignore[arg-type]
    ax.barh(names, [100 * share[n] for n in names], color=plotting.PHYSICAL_COLOR)
    ax.set_xlabel("share of system failures (%)")
    ax.set_title("Which component failures take the function down (physical only)")
    fig.savefig(FIGURES / "baseline_failure_share.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
