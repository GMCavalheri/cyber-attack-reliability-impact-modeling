"""Exact steady-state and mission results for a system of independent components.

Everything here is exact for the model's assumptions: components fail and are repaired
independently (each has its own repair resource), failure times are exponential, and the
system is observed in steady state (long-run averages).

* **Availability.** Each component is up with probability ``A_i = MTBF_i / (MTBF_i + MTTR_i)``,
  independently, so the system availability is ``P(phi(X) = 1)``, computed by enumerating all
  ``2**n`` component states. Enumeration handles shared components exactly.
* **System failure frequency.** In steady state the system fails when a component fails while
  it is *critical* (the system works with it and not without it):
  ``omega = sum_i nu_i * P(phi(1_i, X) - phi(0_i, X) = 1)``, with ``nu_i = 1 / (MTBF_i +
  MTTR_i)`` the failure frequency of component i. The bracket is the Birnbaum importance.
  (Rausand & Høyland, *System Reliability Theory*, 2nd ed., 2004, ch. 13.)
* **System MTBF and MDT.** Up and down periods alternate, so the mean up time is
  ``A / omega`` and the mean down time ``(1 - A) / omega``; their ratio reproduces ``A``.
* **Mission reliability.** With no repair during a mission of ``t`` hours, component i
  survives with probability ``exp(-lambda_i t)`` and the system with ``P(phi(X) = 1)``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from cyberrel.metrics.readiness import StatusHours, classify, status_hours
from cyberrel.system_model.components import component_availability
from cyberrel.system_model.structure import BoolArray, evaluate
from cyberrel.system_model.system import System


def enumerate_states(names: list[str]) -> dict[str, BoolArray]:
    """Every combination of up/down states: ``2**len(names)`` rows, one column per name."""
    n = len(names)
    rows = np.arange(2**n, dtype=np.int64)
    return {name: ((rows >> i) & 1).astype(bool) for i, name in enumerate(names)}


def state_weights(
    states: Mapping[str, BoolArray], p_up: Mapping[str, float]
) -> NDArray[np.float64]:
    """Probability of each enumerated state for independent components."""
    names = list(states)
    size = len(states[names[0]]) if names else 1
    w = np.ones(size)
    for name in names:
        p = float(p_up[name])
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"{name}: probability {p} outside [0, 1]")
        w = w * np.where(states[name], p, 1.0 - p)
    return w


def works_probability(system: System, p_up: Mapping[str, float]) -> float:
    """``P(phi(X) = 1)`` for independent components with up-probabilities ``p_up``."""
    states = enumerate_states(system.names)
    w = state_weights(states, p_up)
    return float(w[evaluate(system.structure, states)].sum())


def availabilities(system: System) -> dict[str, float]:
    """Steady-state availability of each component."""
    return {c.name: component_availability(c) for c in system.components}


def system_availability(system: System) -> float:
    """Steady-state availability of the system function."""
    return works_probability(system, availabilities(system))


def birnbaum_importance(system: System, p_up: Mapping[str, float]) -> dict[str, float]:
    """``P(phi(1_i, X) = 1) - P(phi(0_i, X) = 1)`` for every component i."""
    out = {}
    for name in system.names:
        hi = works_probability(system, {**p_up, name: 1.0})
        lo = works_probability(system, {**p_up, name: 0.0})
        out[name] = hi - lo
    return out


def failure_frequencies(system: System) -> dict[str, float]:
    """Steady-state failure frequency ``1 / (MTBF + MTTR)`` of each component (per hour)."""
    return {
        c.name: 0.0 if c.failure_rate == 0 else 1.0 / (c.mtbf + c.mttr) for c in system.components
    }


@dataclass(frozen=True)
class SteadyState:
    """Long-run metrics of the system function."""

    availability: float
    failure_frequency: float
    mtbf: float
    mdt: float

    @property
    def unavailability(self) -> float:
        """``1 - availability``."""
        return 1.0 - self.availability


def steady_state(system: System) -> SteadyState:
    """Availability, failure frequency, MTBF (mean up time) and MDT of the system function."""
    p_up = availabilities(system)
    a = works_probability(system, p_up)
    ib = birnbaum_importance(system, p_up)
    nu = failure_frequencies(system)
    omega = sum(nu[n] * ib[n] for n in system.names)
    if omega == 0:
        return SteadyState(a, 0.0, math.inf, 0.0)
    return SteadyState(a, omega, a / omega, (1.0 - a) / omega)


def mission_reliability(system: System, hours: float) -> float:
    """Probability that the function survives ``hours`` with no repair during the mission."""
    if hours < 0:
        raise ValueError(f"mission length must be >= 0, got {hours}")
    p_up = {c.name: math.exp(-c.failure_rate * hours) for c in system.components}
    return works_probability(system, p_up)


def k_out_of_n_identical(k: int, n: int, p: float) -> float:
    """``P(at least k of n independent units work)`` with each working with probability p."""
    return sum(math.comb(n, j) * p**j * (1 - p) ** (n - j) for j in range(k, n + 1))


def steady_state_status(system: System) -> StatusHours:
    """Long-run fraction of time in each mission-capable status, physical failures only.

    FMC when every component is up, PMC when the function is up with something down, and
    NMC (all of it maintenance) when the function is down. The result is a
    :class:`~cyberrel.metrics.readiness.StatusHours` whose entries are probabilities, so its
    ``possessed`` total is 1.
    """
    states = enumerate_states(system.names)
    w = state_weights(states, availabilities(system))
    up = evaluate(system.structure, states)
    all_up = np.all(np.stack([states[n] for n in system.names]), axis=0)
    status = classify(up, all_up, up, np.ones_like(up))
    return status_hours(status, w)
