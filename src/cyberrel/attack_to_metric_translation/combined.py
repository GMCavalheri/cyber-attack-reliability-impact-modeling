"""Exact steady-state metrics of the system under physical failures *and* attack scenarios.

This is the core of the translation: a cyber attack is treated exactly as reliability
engineering treats a failure mode.

* Every physical component is an independent alternating renewal process, up with
  probability ``A_i``.
* Every scenario is an independent alternating process (:mod:`.episodes`) that is idle,
  degrading or denying, with stationary probabilities from the renewal-reward theorem.
* While a scenario denies its target group, every component in the group counts as down. The
  function is then ``phi`` of the *effective* states, so a common-mode denial of a whole
  redundancy group defeats the redundancy.

Because all the processes are independent, the stationary distribution of the joint state is
the product of the marginals. Enumerating the joint states (``2**n_components *
3**n_scenarios``) gives the exact availability, the mission-capable statuses and, through
criticality, the failure frequency:

    omega = sum_i nu_i P(i critical) + sum_s nu_s P(s critical)

with ``nu_i`` the failure frequency of component i and ``nu_s`` the frequency of denial
onsets of scenario s, the same Birnbaum argument as in
:mod:`cyberrel.system_model.closed_form`. System MTBF and MDT follow as ``A / omega`` and
``(1 - A) / omega``. With no scenarios every number reduces exactly to the physical
baseline.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from cyberrel.attack_scenario_library.library import check_targets
from cyberrel.attack_scenario_library.scenarios import AttackScenario
from cyberrel.attack_to_metric_translation.episodes import ScenarioProcess, scenario_process
from cyberrel.metrics.readiness import StatusHours, classify, status_hours
from cyberrel.system_model.closed_form import availabilities, failure_frequencies
from cyberrel.system_model.structure import BoolArray, evaluate
from cyberrel.system_model.system import System

IDLE, DEGRADE, DENY = 0, 1, 2
MAX_JOINT_STATES = 2_000_000


@dataclass(frozen=True)
class JointStates:
    """Every joint state of components and scenarios, with its stationary probability."""

    components: dict[str, BoolArray]
    scenarios: dict[str, NDArray[np.int64]]
    weight: NDArray[np.float64]


def joint_states(
    system: System, processes: Sequence[ScenarioProcess], p_up: Mapping[str, float] | None = None
) -> JointStates:
    """Enumerate the product state space: component up/down times scenario idle/degrade/deny."""
    names = system.names
    n_phys, n_scen = 2 ** len(names), 3 ** len(processes)
    if n_phys * n_scen > MAX_JOINT_STATES:
        raise ValueError(f"{n_phys * n_scen} joint states is too many to enumerate")
    p_up = availabilities(system) if p_up is None else p_up
    phys_index = np.repeat(np.arange(n_phys, dtype=np.int64), n_scen)
    scen_index = np.tile(np.arange(n_scen, dtype=np.int64), n_phys)
    components = {n: ((phys_index >> i) & 1).astype(bool) for i, n in enumerate(names)}
    weight = np.ones(n_phys * n_scen)
    for n in names:
        weight = weight * np.where(components[n], p_up[n], 1.0 - p_up[n])
    scenarios = {}
    for j, proc in enumerate(processes):
        state = (scen_index // 3**j) % 3
        scenarios[proc.scenario.name] = state
        weight = weight * np.asarray(proc.state_probabilities)[state]
    return JointStates(components, scenarios, weight)


def function_up(
    system: System,
    components: Mapping[str, BoolArray],
    scenarios: Mapping[str, NDArray[np.int64]],
    targets: Mapping[str, str],
) -> BoolArray:
    """The function given component states and scenario states (denials knock out groups)."""
    groups = {c.name: c.group for c in system.components}
    denied: dict[str, BoolArray] = {}
    for name, state in scenarios.items():
        g = targets[name]
        denied[g] = denied.get(g, np.zeros(state.shape, dtype=bool)) | (state == DENY)
    effective = {
        n: up & ~denied[groups[n]] if groups[n] in denied else up for n, up in components.items()
    }
    return evaluate(system.structure, effective)


@dataclass(frozen=True)
class CombinedSteadyState:
    """Long-run metrics of the function with physical failures and attack scenarios."""

    availability: float
    failure_frequency: float
    mtbf: float
    mdt: float
    status: StatusHours
    """Stationary probabilities of FMC, PMC and NMC by cause (``possessed`` is 1)."""
    processes: tuple[ScenarioProcess, ...]

    @property
    def unavailability(self) -> float:
        """``1 - availability``."""
        return 1.0 - self.availability

    @property
    def mc_rate(self) -> float:
        """Mission-capable rate, equal to the function's availability in this model."""
        return self.status.mc_rate

    @property
    def fmc_rate(self) -> float:
        """Full-mission-capable rate."""
        return self.status.fmc_rate


def combined_steady_state(
    system: System, scenarios: Sequence[AttackScenario] = ()
) -> CombinedSteadyState:
    """Exact availability, failure frequency, MTBF, MDT and MC statuses (see module doc)."""
    check_targets(system, {s.name: s for s in scenarios})
    if len({s.name for s in scenarios}) != len(scenarios):
        raise ValueError("scenario names must be unique")
    processes = tuple(scenario_process(s) for s in scenarios)
    targets = {s.name: s.target_group for s in scenarios}
    js = joint_states(system, processes)
    comps, scens, w = js.components, js.scenarios, js.weight

    up = function_up(system, comps, scens, targets)
    idle = {n: np.zeros_like(s) for n, s in scens.items()}
    perfect = {n: np.ones_like(c) for n, c in comps.items()}
    up_physical_only = function_up(system, comps, idle, targets)
    up_cyber_only = function_up(system, perfect, scens, targets)
    nothing_down = np.all(np.stack(list(comps.values())), axis=0)
    for s in scens.values():
        nothing_down = nothing_down & (s == IDLE)
    status = status_hours(classify(up, nothing_down, up_physical_only, up_cyber_only), w)
    availability = float(w[up].sum())

    omega = 0.0
    nu = failure_frequencies(system)
    for n in system.names:
        if nu[n] == 0:
            continue
        works = function_up(system, {**comps, n: np.ones_like(comps[n])}, scens, targets)
        fails = function_up(system, {**comps, n: np.zeros_like(comps[n])}, scens, targets)
        omega += nu[n] * float(w[works & ~fails].sum())
    for proc in processes:
        if proc.deny_frequency == 0:
            continue
        name = proc.scenario.name
        works = function_up(system, comps, {**scens, name: np.zeros_like(scens[name])}, targets)
        fails = function_up(
            system, comps, {**scens, name: np.full_like(scens[name], DENY)}, targets
        )
        omega += proc.deny_frequency * float(w[works & ~fails].sum())

    if omega == 0:
        return CombinedSteadyState(availability, 0.0, math.inf, 0.0, status, processes)
    return CombinedSteadyState(
        availability,
        omega,
        availability / omega,
        (1.0 - availability) / omega,
        status,
        processes,
    )
