"""Cyber attack scenarios described by their effect on the system, not by how they are done.

A scenario says *what an attack does to the system's function, how often, for how long, and
how long the defenders take to notice and recover*. It never says how the attack is carried
out (see ``docs/scope.md``). Three kinds of effect cover the plan's library:

* :attr:`EffectKind.DENIAL`: the target group stops delivering data (denial of service on a
  data bus). Every component in the group is unavailable at once: a **common-mode** effect.
* :attr:`EffectKind.INTEGRITY`: the target group delivers *false* data (sensor spoofing,
  injected messages). An integrity monitor may catch it at onset, with probability
  ``catch_probability``. Then the false data are rejected and the function continues degraded
  for as long as the attack lasts. Otherwise the false data are used, the function counts as
  lost (it no longer delivers *trusted* data), and the loss lasts until detection and
  recovery.
* :attr:`EffectKind.DELAY`: messages through the target group are delayed (injection or
  replay that adds latency). The function is lost while the added latency exceeds the
  timeliness deadline; below the deadline the effect only degrades margins.

Each attack starts an **episode**. ``duration`` is how long the adversary sustains the effect,
``time_to_detect`` and ``time_to_recover`` the defenders' response. A *transient* effect ends
when the adversary stops or when the response completes, whichever is first:
``min(D, T_detect + T_recover)``. A *persistent* effect, such as a corrupted navigation
solution that must be re-validated, lasts until the response completes: ``T_detect +
T_recover``. Attacks arrive at ``rate_per_hour`` while no episode of the same scenario is
active.

All rates and times are illustrative assumptions, never field data.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field, replace
from enum import Enum

import numpy as np
from numpy.typing import NDArray

from cyberrel.system_model.components import RepairDistribution, RepairKind

Duration = RepairDistribution
"""A positive random duration with a stated mean (same parameterisation as repair times)."""

VERIFIED_TECHNIQUES = {
    "T0814": "Denial of Service",
    "T0830": "Adversary-in-the-Middle",
    "T0856": "Spoof Reporting Message",
}
"""MITRE ATT&CK for ICS techniques used by the library, names checked on attack.mitre.org
(2026-11-15). Tags are for orientation only: the model works at the effect level."""

TECHNIQUE_ID = re.compile(r"T0\d{3}")


class EffectKind(Enum):
    """What the attack does to the target group."""

    DENIAL = "denial"
    INTEGRITY = "integrity"
    DELAY = "delay"


class EpisodeMode(Enum):
    """How an episode affects the function."""

    DENY = "deny"
    """The target group is unusable: its components count as down."""
    DEGRADE = "degrade"
    """The function continues, with margins or redundancy reduced (PMC, not NMC)."""


@dataclass(frozen=True)
class AttackScenario:
    """One effect-level attack scenario."""

    name: str
    kind: EffectKind
    target_group: str
    rate_per_hour: float
    duration: Duration
    time_to_detect: float
    time_to_recover: float
    persistent: bool = False
    catch_probability: float = 0.0
    added_latency_ms: float = 0.0
    deadline_ms: float = 0.0
    technique: str = ""
    description: str = ""
    basis: str = field(default="assumption", compare=False)

    def __post_init__(self) -> None:
        if not self.name.isidentifier():
            raise ValueError(f"scenario name must be an identifier, got {self.name!r}")
        for label, value in (
            ("rate_per_hour", self.rate_per_hour),
            ("time_to_detect", self.time_to_detect),
            ("time_to_recover", self.time_to_recover),
            ("added_latency_ms", self.added_latency_ms),
            ("deadline_ms", self.deadline_ms),
        ):
            if not (value >= 0 and math.isfinite(value)):
                raise ValueError(f"{self.name}: {label} must be >= 0 and finite, got {value}")
        if not 0.0 <= self.catch_probability <= 1.0:
            raise ValueError(f"{self.name}: catch_probability must be in [0, 1]")
        if self.catch_probability > 0 and self.kind is not EffectKind.INTEGRITY:
            raise ValueError(f"{self.name}: only integrity effects can be caught at onset")
        if self.kind is not EffectKind.DELAY and (self.added_latency_ms or self.deadline_ms):
            raise ValueError(f"{self.name}: latency and deadline apply to delay effects only")
        if self.technique and not TECHNIQUE_ID.fullmatch(self.technique):
            raise ValueError(f"{self.name}: technique must look like T0nnn, got {self.technique}")

    @property
    def response_time(self) -> float:
        """``time_to_detect + time_to_recover``: how long the defenders need."""
        return self.time_to_detect + self.time_to_recover

    @property
    def exceeds_deadline(self) -> bool:
        """For delay effects: does the added latency break the timeliness requirement?"""
        return self.added_latency_ms > self.deadline_ms

    @property
    def deny_probability(self) -> float:
        """Probability that an episode takes the target group down (DENY mode)."""
        if self.kind is EffectKind.DENIAL:
            return 1.0
        if self.kind is EffectKind.INTEGRITY:
            return 1.0 - self.catch_probability
        return 1.0 if self.exceeds_deadline else 0.0

    def with_changes(self, **changes: object) -> AttackScenario:
        """A copy with some fields changed (for sensitivity studies)."""
        return replace(self, **changes)  # type: ignore[arg-type]

    def sample_episodes(
        self, rng: np.random.Generator, size: int
    ) -> tuple[NDArray[np.bool_], NDArray[np.float64]]:
        """Draw ``size`` episodes: whether each denies the target, and how long it lasts.

        Integrity effects caught at onset degrade the function for the attack's own duration;
        everything else follows the transient/persistent rule in the module docstring.
        """
        d = self.duration.sample(rng, size)
        response = np.full(size, self.response_time)
        effect = response if self.persistent else np.minimum(d, response)
        if self.kind is EffectKind.INTEGRITY:
            caught = rng.random(size) < self.catch_probability
            return ~caught, np.where(caught, d, effect)
        return np.full(size, self.deny_probability == 1.0), effect


def fixed(hours: float) -> Duration:
    """A deterministic duration."""
    return Duration(hours, RepairKind.FIXED)
