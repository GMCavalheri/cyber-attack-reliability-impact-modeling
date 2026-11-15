"""Phase 3: each attack scenario in reliability units, ranked, and the common-mode effect."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np

from cyberrel import plotting
from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.attack_to_metric_translation import (
    combined_steady_state,
    episode_timeline,
    rank_scenarios,
    scenario_process,
)
from cyberrel.system_model import component_availability, navigation_system

from common import FIGURES, table, write_result

SEED = 20261115
RUNS, HORIZON = 200, 2e5


def main() -> None:
    system = navigation_system()
    lib = load_scenarios()
    scenarios = list(lib.values())
    base = combined_steady_state(system)
    ranked = rank_scenarios(system, scenarios)
    every = combined_steady_state(system, scenarios)

    as_failure_mode = table(
        ["scenario", "equivalent MTBF (h)", "equivalent MTTR (h)", "P(deny)", "P(degrade)"],
        [[i.scenario, i.equivalent_mtbf, i.equivalent_mttr, i.p_deny, i.p_degrade] for i in ranked],
    )
    impact_rows = [
        [
            "physical only",
            base.unavailability,
            "—",
            base.mtbf,
            1.0,
            base.mdt,
            base.mc_rate,
            base.fmc_rate,
        ]
    ]
    for i in ranked:
        a = i.attacked
        impact_rows.append(
            [
                f"+ {i.scenario}",
                a.unavailability,
                i.unavailability_multiple,
                a.mtbf,
                i.mtbf_ratio,
                a.mdt,
                a.mc_rate,
                a.fmc_rate,
            ]
        )
    impact_rows.append(
        [
            "+ all four",
            every.unavailability,
            (every.unavailability - base.unavailability) / base.unavailability,
            every.mtbf,
            every.mtbf / base.mtbf,
            every.mdt,
            every.mc_rate,
            every.fmc_rate,
        ]
    )
    impacts = table(
        [
            "case",
            "1 − A",
            "added 1 − A ÷ physical 1 − A",
            "system MTBF (h)",
            "MTBF ratio",
            "MDT (h)",
            "MC rate",
            "FMC rate",
        ],
        impact_rows,
    )
    s = every.status
    attribution = table(
        ["status", "share of possessed hours"],
        [
            ["FMC", s.fmc],
            ["PMC", s.pmc],
            ["NMC: physical failures", s.nmc_maintenance],
            ["NMC: cyber effects", s.nmc_cyber],
            ["NMC: both together", s.nmc_both],
        ],
    )

    dos = lib["bus_flood_dos"]
    q_dos = scenario_process(dos).p_deny
    channel = system.component("bus_ch_a")
    q_ch = 1 - component_availability(channel)
    common_rows = []
    for n in (1, 2, 3):
        variant = navigation_system(2, n)
        b = combined_steady_state(variant)
        a = combined_steady_state(variant, [dos])
        common_rows.append(
            [n, q_ch**n, q_dos, b.unavailability, a.unavailability, a.availability / b.availability]
        )
    common = table(
        [
            "bus channels",
            "data path down, physical (q^n)",
            "P(bus denied by DoS)",
            "system 1 − A, physical",
            "system 1 − A, with DoS",
            "A ratio (= 1 − P(deny))",
        ],
        common_rows,
    )

    rng = np.random.default_rng(SEED)
    mc_rows = []
    for sc in scenarios:
        proc = scenario_process(sc)
        shares = np.array(
            [episode_timeline(sc, HORIZON, rng).time_in(True) / HORIZON for _ in range(RUNS)]
        )
        se = shares.std(ddof=1) / math.sqrt(RUNS)
        mc_rows.append(
            [sc.name, proc.p_deny, shares.mean(), se, (shares.mean() - proc.p_deny) / se]
        )
    monte_carlo = table(
        ["scenario", "P(deny) closed form", "Monte Carlo mean", "standard error", "z"],
        mc_rows,
    )

    write_result(
        "translation",
        "Phase 3 · Attack scenarios translated into reliability metrics",
        [
            ("Each scenario as a failure mode", as_failure_mode),
            ("Impact on the system (exact steady state), largest first", impacts),
            ("Where the time goes with all four scenarios", attribution),
            ("Common mode: redundancy and a bus denial", common),
            (f"Monte Carlo check of the renewal formula ({RUNS} × {HORIZON:g} h)", monte_carlo),
        ],
    )

    plotting.use_style()
    fig, ax = plt.subplots(figsize=(7, 3))
    labels = ["physical failures"] + [i.scenario for i in ranked]
    values = [base.unavailability] + [i.delta_availability for i in ranked]
    colors = [plotting.PHYSICAL_COLOR] + [plotting.CYBER_COLOR] * len(ranked)
    ax.barh(labels, [1e4 * v for v in values], color=colors)
    ax.invert_yaxis()
    ax.set_xlabel("unavailability added (hours per 10 000 h)")
    ax.set_title("Each scenario's cost in availability, next to all physical failures")
    fig.savefig(FIGURES / "translation_unavailability.png")
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(6, 3.4))
    n = [r[0] for r in common_rows]
    ax.semilogy(
        n,
        [r[1] for r in common_rows],
        "o-",
        color=plotting.PHYSICAL_COLOR,
        label="data path lost to physical failures",
    )
    ax.semilogy(
        n,
        [r[2] for r in common_rows],
        "s-",
        color=plotting.CYBER_COLOR,
        label="data path lost to the bus denial",
    )
    ax.set_xticks(n)
    ax.set_xlabel("bus channels")
    ax.set_ylabel("probability (steady state)")
    ax.set_title("Redundancy divides physical risk, not common-mode cyber risk")
    ax.legend(fontsize=8)
    fig.savefig(FIGURES / "translation_common_mode.png")
    plt.close(fig)

    cases = {"physical only": base.status}
    cases |= {f"+ {i.scenario}": i.attacked.status for i in ranked}
    cases["+ all four"] = every.status
    fig = plotting.status_bars(cases, title="Time not fully mission capable, by cause")
    fig.savefig(FIGURES / "translation_status.png")
    plt.close(fig)


if __name__ == "__main__":
    main()
