"""Generate and execute the demo notebooks, one per lesson, from the cell sources below.

    uv run python notebooks/build_notebooks.py           # write and execute all notebooks
    uv run python notebooks/build_notebooks.py --check   # execute in memory only (CI)

Keeping the sources here, instead of hand-editing .ipynb JSON, makes the notebooks reviewable
in diffs. Every computation in them is exact or seeded, so a rebuild reproduces them.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent

SETUP = """\
import matplotlib.pyplot as plt

from cyberrel import plotting

plotting.use_style()"""

Cell = tuple[str, str]

NOTEBOOKS: dict[str, list[Cell]] = {
    "01_one_language.ipynb": [
        (
            "md",
            """\
# 1 · One language for failure

MTBF, availability, mission reliability and readiness for the synthetic navigation system,
physical failures only. See [Lesson 1](../docs/lessons/01-one-language-for-failure.md).""",
        ),
        ("code", SETUP),
        (
            "code",
            """\
from cyberrel.system_model import (
    MISSION_HOURS,
    mission_reliability,
    navigation_system,
    steady_state,
    steady_state_status,
)

system = navigation_system()
print(system.summary())
s = steady_state(system)
print(f"A = {s.availability:.6f}   MTBF = {s.mtbf:,.0f} h   MDT = {s.mdt:.2f} h")
print(f"10 h mission unreliability = {1 - mission_reliability(system, MISSION_HOURS):.3e}")
status = steady_state_status(system)
print(f"FMC {status.fmc_rate:.4f}   PMC {status.pmc_rate:.4f}   MC {status.mc_rate:.6f}")""",
        ),
        ("md", "Where system failures come from: failure frequency times Birnbaum importance."),
        (
            "code",
            """\
from cyberrel.system_model import availabilities, birnbaum_importance
from cyberrel.system_model.closed_form import failure_frequencies

ib = birnbaum_importance(system, availabilities(system))
nu = failure_frequencies(system)
share = {n: nu[n] * ib[n] / s.failure_frequency for n in system.names}
fig, ax = plt.subplots(figsize=(6, 3))
ax.barh(list(share), [100 * v for v in share.values()], color=plotting.PHYSICAL_COLOR)
ax.set_xlabel("share of system failures (%)");""",
        ),
        ("md", "The same mission unreliability from CPS-02's failure-logic model (`cpsrbd`)."),
        (
            "code",
            """\
from cpsrbd.consequence_driven_analysis import navigation_case_study
from cpsrbd.probability_likelihood_propagation import exact_probability, origin_overrides
from cpsrbd.unified_graph_model import Origin

model = navigation_case_study(mission_hours=MISSION_HOURS)
cps02 = exact_probability(model, origin_overrides(model, Origin.PHYSICAL))
here = 1 - mission_reliability(system, MISSION_HOURS)
print(f"CPS-02 {cps02:.15e}\\nCPS-01 {here:.15e}\\ndifference {abs(cps02 - here):.1e}")""",
        ),
    ],
    "02_effects.ipynb": [
        (
            "md",
            """\
# 2 · Describing an attack by what it does

The effect-level scenario library and its episodes. See
[Lesson 2](../docs/lessons/02-describing-an-attack-by-what-it-does.md).""",
        ),
        (
            "code",
            """\
import numpy as np

from cyberrel.attack_scenario_library import load_scenarios

lib = load_scenarios()
for s in lib.values():
    print(f"{s.name:22s} {s.kind.value:9s} -> {s.target_group:10s} "
          f"rate {s.rate_per_hour:.0e}/h  response {s.response_time:.2f} h  {s.technique or '-'}")""",
        ),
        ("md", "Sampled episode lengths against the exact $E[\\min(D, c)]$:"),
        (
            "code",
            """\
from cyberrel.attack_to_metric_translation import episode_means

rng = np.random.default_rng(1)
for s in lib.values():
    deny, length = s.sample_episodes(rng, 100_000)
    l_deny, l_degrade = episode_means(s)
    sampled = length[deny].mean() if deny.any() else 0.0
    print(f"{s.name:22s} P(deny) {deny.mean():.3f}  mean deny {sampled:.3f} h  exact {l_deny:.3f} h")""",
        ),
        ("md", "A delay below the deadline only degrades:"),
        (
            "code",
            """\
slow = lib["message_delay_replay"].with_changes(added_latency_ms=45.0)
print(slow.exceeds_deadline, slow.deny_probability)""",
        ),
    ],
    "03_translation.ipynb": [
        (
            "md",
            """\
# 3 · A cyber attack as a failure event

Each scenario as a failure mode, its impact, and the common-mode identity. See
[Lesson 3](../docs/lessons/03-a-cyber-attack-as-a-failure-event.md).""",
        ),
        ("code", SETUP),
        (
            "code",
            """\
from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.attack_to_metric_translation import combined_steady_state, rank_scenarios
from cyberrel.system_model import navigation_system

system = navigation_system()
scenarios = list(load_scenarios().values())
for i in rank_scenarios(system, scenarios):
    print(f"{i.scenario:22s} eq. MTBF {i.equivalent_mtbf:8.0f} h  eq. MTTR {i.equivalent_mttr:.2f} h  "
          f"+{i.unavailability_multiple:.2f} x physical 1-A   MTBF ratio {i.mtbf_ratio:.3f}")
every = combined_steady_state(system, scenarios)
print(f"all four: A {every.availability:.5f}  MTBF {every.mtbf:,.0f} h  NMC cyber {every.status.nmc_cyber:.2e}")""",
        ),
        ("md", "Redundancy divides physical risk, not common-mode cyber risk:"),
        (
            "code",
            """\
from cyberrel.attack_to_metric_translation import common_mode_factor, scenario_process

dos = load_scenarios()["bus_flood_dos"]
for n in (1, 2, 3):
    f = common_mode_factor(navigation_system(bus_channels=n), dos)
    print(n, "channels: A ratio", f, " 1 - P(deny) =", 1 - scenario_process(dos).p_deny)""",
        ),
    ],
    "04_fleet.ipynb": [
        (
            "md",
            """\
# 4 · The total risk picture

A 24-platform fleet over ten years, physical failures and attacks on one timeline. See
[Lesson 4](../docs/lessons/04-the-total-risk-picture.md).""",
        ),
        ("code", SETUP),
        (
            "code",
            """\
from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.attack_to_metric_translation import combined_steady_state
from cyberrel.combined_monte_carlo_simulation import simulate_fleet
from cyberrel.system_model import navigation_system

system = navigation_system()
scenarios = list(load_scenarios().values())
fleet = simulate_fleet(system, scenarios, platforms=24, horizon=10 * 8760.0, seed=20261115)
k = fleet.kpis()
print(f"{k.failure_count} losses  MTBF {k.mtbf:,.0f} h  MTTR {k.mttr:.2f} h  A {k.availability:.5f}")
for cause in ("physical", "cyber", "both"):
    c = fleet.kpis({cause})
    print(f"  {cause:8s} {c.failure_count:5d} outages, {c.down_hours:7.1f} h down")""",
        ),
        ("md", "Simulation against the exact steady state (95 % intervals across platforms):"),
        (
            "code",
            """\
exact = combined_steady_state(system, scenarios)
for metric, value in (("availability", exact.availability),
                      ("failure_frequency", exact.failure_frequency),
                      ("nmc_cyber", exact.status.nmc_cyber)):
    e = fleet.estimate(metric)
    print(f"{metric:18s} exact {value:.4e}  sim {e.mean:.4e}  [{e.low:.4e}, {e.high:.4e}]")
fig = plotting.status_bars({"exact": exact.status, "simulated": fleet.status})""",
        ),
    ],
    "05_mitigations.ipynb": [
        (
            "md",
            """\
# 5 · Where mitigation money matters

Mitigations on one scale, and the tornado. See
[Lesson 5](../docs/lessons/05-where-mitigation-money-matters.md).""",
        ),
        (
            "code",
            """\
from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.sensitivity_analysis import evaluate_mitigations, tornado
from cyberrel.system_model import navigation_system

scenarios = list(load_scenarios().values())
for r in evaluate_mitigations(scenarios):
    print(f"{r.name:36s} {100 * r.unavailability_reduction:5.1f} %  MTBF x{r.mtbf_gain:.2f}  "
          f"FMC {r.fmc_gain:+.1e}")""",
        ),
        (
            "code",
            """\
for b in tornado(navigation_system(), scenarios)[:6]:
    print(f"{b.parameter:40s} {b.low:.3e} .. {b.high:.3e}")""",
        ),
        ("md", "Detection shortens outages but leaves MTBF where it is:"),
        (
            "code",
            """\
from cyberrel.sensitivity_analysis import Design

for k in (0.0, 0.5, 1.0, 2.0):
    r = Design(detect_scale=k).evaluate(scenarios)
    print(f"detect x{k:<4} 1-A {r.unavailability:.3e}  MTBF {r.mtbf:,.0f} h")""",
        ),
    ],
    "06_your_inputs.ipynb": [
        (
            "md",
            """\
# 6 · Your own inputs, and what survives them

Replace the illustrative attack parameters and check which conclusions hold. See
[Lesson 6](../docs/lessons/06-cie-in-numbers-and-what-is-new.md).""",
        ),
        (
            "code",
            """\
from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.sensitivity_analysis import evaluate_mitigations

base = list(load_scenarios().values())
for scale in (0.1, 1.0, 10.0):
    scenarios = [s.with_changes(rate_per_hour=s.rate_per_hour * scale) for s in base]
    results = {r.name: r for r in evaluate_mitigations(scenarios)}
    order = [r.name for r in evaluate_mitigations(scenarios)][:3]
    print(f"attack rates x{scale:<4} third bus channel: "
          f"{100 * results['third bus channel'].unavailability_reduction:.4f} %   top three: {order}")""",
        ),
        (
            "md",
            """\
The percentages and the order move with the rates; the third bus channel's value against a
common-mode denial stays at essentially zero. That is the difference between a worked example
and a structural result.""",
        ),
    ],
}


def build(name: str, cells: list[Cell]) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.metadata["kernelspec"] = {
        "name": "python3",
        "display_name": "Python 3",
        "language": "python",
    }
    nb.cells = [
        nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src)
        for kind, src in cells
    ]
    for i, cell in enumerate(nb.cells):
        cell["id"] = f"{Path(name).stem}-{i}"
    NotebookClient(
        nb,
        timeout=600,
        kernel_name="python3",
        record_timing=False,  # no timestamps: rebuilds are byte-identical
        resources={"metadata": {"path": str(HERE)}},
    ).execute()
    return nb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="execute without writing")
    ap.add_argument("names", nargs="*", help="notebooks to build (default: all)")
    args = ap.parse_args()
    for name in args.names or list(NOTEBOOKS):
        print(f"== {name}", flush=True)
        nb = build(name, NOTEBOOKS[name])
        if not args.check:
            nbformat.write(nb, HERE / name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
