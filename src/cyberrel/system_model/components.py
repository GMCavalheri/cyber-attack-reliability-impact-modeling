"""Repairable components: a constant failure rate and a repair-time distribution.

Each component alternates between *up* periods, exponentially distributed with rate
``failure_rate`` (a constant hazard, the usual model for electronic line-replaceable units in
their useful-life period), and *down* periods drawn from its :class:`RepairDistribution`. That
is an **alternating renewal process**; its long-run fraction of time up is
``MTBF / (MTBF + MTTR)`` whatever the repair distribution (Rausand & Høyland, *System
Reliability Theory*, 2nd ed., 2004, ch. 7), which :func:`component_availability` returns.

Time is in hours throughout.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from numpy.typing import NDArray


class RepairKind(Enum):
    """Shape of the repair-time distribution."""

    EXPONENTIAL = "exponential"
    LOGNORMAL = "lognormal"
    FIXED = "fixed"


@dataclass(frozen=True)
class RepairDistribution:
    """Repair (down) time with a given mean.

    ``LOGNORMAL`` is parameterised by its mean and the standard deviation ``sigma`` of the
    underlying normal, so ``mu = ln(mean) - sigma**2 / 2``. Lognormal corrective-maintenance
    times are the conventional choice in maintainability prediction; ``EXPONENTIAL`` gives the
    Markov model and ``FIXED`` a deterministic delay.
    """

    mean: float
    kind: RepairKind = RepairKind.LOGNORMAL
    sigma: float = 0.8

    def __post_init__(self) -> None:
        if not (self.mean > 0 and math.isfinite(self.mean)):
            raise ValueError(f"mean repair time must be positive and finite, got {self.mean}")
        if self.kind is RepairKind.LOGNORMAL and not self.sigma > 0:
            raise ValueError(f"lognormal sigma must be positive, got {self.sigma}")

    def sample(self, rng: np.random.Generator, size: int) -> NDArray[np.float64]:
        """Draw ``size`` repair times."""
        if self.kind is RepairKind.EXPONENTIAL:
            return rng.exponential(self.mean, size)
        if self.kind is RepairKind.LOGNORMAL:
            mu = math.log(self.mean) - self.sigma**2 / 2
            return rng.lognormal(mu, self.sigma, size)
        return np.full(size, self.mean)


@dataclass(frozen=True)
class Component:
    """A repairable component of the system.

    ``group`` names the redundancy group the component belongs to (``"data_bus"``,
    ``"nav_source"``...). Cyber scenarios target groups, not individual units, so a scenario
    that denies the data bus still denies it when a third channel is added.
    """

    name: str
    failure_rate: float
    repair: RepairDistribution
    group: str
    description: str = ""
    basis: str = field(default="assumption", compare=False)

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"component name must be an identifier, got {self.name!r}")
        if not (self.failure_rate >= 0 and math.isfinite(self.failure_rate)):
            raise ValueError(f"{self.name}: failure rate must be >= 0, got {self.failure_rate}")

    @property
    def mtbf(self) -> float:
        """Mean time between failures, ``1 / failure_rate`` (infinite if it never fails)."""
        return math.inf if self.failure_rate == 0 else 1.0 / self.failure_rate

    @property
    def mttr(self) -> float:
        """Mean time to repair."""
        return self.repair.mean


def component_availability(component: Component) -> float:
    """Steady-state availability ``MTBF / (MTBF + MTTR)`` of one component."""
    if component.failure_rate == 0:
        return 1.0
    return component.mtbf / (component.mtbf + component.mttr)


def mission_reliability(component: Component, hours: float) -> float:
    """Probability that the component does not fail during ``hours`` of operation."""
    if hours < 0:
        raise ValueError(f"mission length must be >= 0, got {hours}")
    return math.exp(-component.failure_rate * hours)
