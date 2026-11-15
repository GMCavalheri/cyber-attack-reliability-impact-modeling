"""Each attack scenario expressed in reliability units, and the scenarios compared.

For one scenario on top of the physical baseline, :func:`translate` reports:

* the scenario *as a failure mode*: its equivalent MTBF (mean time between denials) and
  equivalent MTTR (mean denial length), the two numbers a reliability engineer would put in a
  failure-mode table;
* its **impact** on the system: the changes in availability, system MTBF, MC rate and FMC
  rate relative to the physical baseline, and the multiple of the physical unavailability it
  adds.

:func:`common_mode_factor` checks the structural claim behind the numbers. When a scenario
denies a whole group that the function needs (every channel of the bus, say), the attacked
availability is exactly ``A_physical * (1 - P(deny))``: the attack acts as one extra block in
series, whatever the redundancy inside the group.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from cyberrel.attack_scenario_library.scenarios import AttackScenario
from cyberrel.attack_to_metric_translation.combined import (
    CombinedSteadyState,
    combined_steady_state,
)
from cyberrel.attack_to_metric_translation.episodes import scenario_process
from cyberrel.system_model.structure import evaluate
from cyberrel.system_model.system import System


@dataclass(frozen=True)
class ScenarioImpact:
    """One scenario's impact on the system, in reliability units."""

    scenario: str
    equivalent_mtbf: float
    equivalent_mttr: float
    p_deny: float
    p_degrade: float
    baseline: CombinedSteadyState
    attacked: CombinedSteadyState

    @property
    def delta_availability(self) -> float:
        """Availability lost to the scenario, ``A_baseline - A_attacked`` (>= 0)."""
        return self.baseline.availability - self.attacked.availability

    @property
    def unavailability_multiple(self) -> float:
        """Added unavailability as a multiple of the physical unavailability."""
        return self.delta_availability / self.baseline.unavailability

    @property
    def delta_mtbf(self) -> float:
        """Change in system MTBF (negative: failures become more frequent)."""
        return self.attacked.mtbf - self.baseline.mtbf

    @property
    def mtbf_ratio(self) -> float:
        """Attacked system MTBF over the baseline's."""
        return self.attacked.mtbf / self.baseline.mtbf

    @property
    def delta_mc_rate(self) -> float:
        """MC rate lost to the scenario."""
        return self.baseline.mc_rate - self.attacked.mc_rate

    @property
    def delta_fmc_rate(self) -> float:
        """FMC rate lost to the scenario (denial *and* degradation count)."""
        return self.baseline.fmc_rate - self.attacked.fmc_rate


def translate(
    system: System, scenario: AttackScenario, baseline: CombinedSteadyState | None = None
) -> ScenarioImpact:
    """The scenario's reliability-unit description and its impact on ``system``."""
    base = combined_steady_state(system) if baseline is None else baseline
    proc = scenario_process(scenario)
    attacked = combined_steady_state(system, [scenario])
    return ScenarioImpact(
        scenario.name,
        proc.equivalent_mtbf,
        proc.equivalent_mttr,
        proc.p_deny,
        proc.p_degrade,
        base,
        attacked,
    )


def rank_scenarios(
    system: System, scenarios: Sequence[AttackScenario], key: str = "delta_availability"
) -> list[ScenarioImpact]:
    """Impacts of each scenario alone, largest first by ``key`` (a ScenarioImpact property)."""
    base = combined_steady_state(system)
    impacts = [translate(system, s, base) for s in scenarios]
    return sorted(impacts, key=lambda i: float(getattr(i, key)), reverse=True)


def group_is_necessary(system: System, group: str) -> bool:
    """True if the function cannot work with every component of ``group`` down."""
    members = set(system.members(group))
    states = {n: np.array([n not in members]) for n in system.names}
    return not bool(evaluate(system.structure, states)[0])


def common_mode_factor(system: System, scenario: AttackScenario) -> float:
    """``A_attacked / A_physical``; equals ``1 - P(deny)`` when the target group is necessary.

    Raises if the target group is not necessary for the function, since the series-block
    identity does not hold then.
    """
    if not group_is_necessary(system, scenario.target_group):
        raise ValueError(f"group {scenario.target_group!r} is not necessary for the function")
    base = combined_steady_state(system).availability
    attacked = combined_steady_state(system, [scenario]).availability
    return math.nan if base == 0 else attacked / base
