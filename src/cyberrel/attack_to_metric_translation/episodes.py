"""Each scenario as an alternating process: idle, episode, idle, episode...

While no episode is active, attacks of a scenario arrive at ``rate_per_hour`` (exponential
idle periods). Each arrival starts an episode that either **denies** the target group or only
**degrades** it (see :mod:`cyberrel.attack_scenario_library.scenarios`). This is the same
alternating renewal structure as a repairable component, with two kinds of "down". So the
renewal-reward theorem gives the long-run share of time in each state from *means* alone:

    cycle   = 1 / rate + p_deny * L_deny + (1 - p_deny) * L_degrade
    P(deny) = p_deny * L_deny / cycle,   P(degrade) = (1 - p_deny) * L_degrade / cycle

and denial episodes start with frequency ``p_deny / cycle`` per hour. ``L_deny`` and
``L_degrade`` are the mean episode lengths, which need ``E[min(D, c)]`` for the duration
distribution (:func:`mean_min`).

:func:`episode_timeline` samples the same process over a time horizon, for the Monte Carlo
checks and for the combined simulation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.stats import norm

from cyberrel.attack_scenario_library.scenarios import AttackScenario, Duration, EffectKind
from cyberrel.system_model.components import RepairKind


def mean_min(dist: Duration, c: float) -> float:
    """``E[min(D, c)]`` for a duration distribution and a cap ``c >= 0``.

    ``E[min(D, c)] = integral of P(D > t) from 0 to c``. For exponential D with mean m this is
    ``m (1 - exp(-c / m))``. For lognormal ``ln D ~ N(mu, sigma^2)`` it is the partial
    expectation ``m Phi((ln c - mu - sigma^2) / sigma) + c (1 - Phi((ln c - mu) / sigma))``.
    """
    if c < 0:
        raise ValueError(f"cap must be >= 0, got {c}")
    if c == 0:
        return 0.0
    m = dist.mean
    if dist.kind is RepairKind.EXPONENTIAL:
        return m * -math.expm1(-c / m)
    if dist.kind is RepairKind.FIXED:
        return min(m, c)
    s = dist.sigma
    mu = math.log(m) - s**2 / 2
    z = (math.log(c) - mu) / s
    return float(m * norm.cdf(z - s) + c * norm.sf(z))


@dataclass(frozen=True)
class ScenarioProcess:
    """Long-run behaviour of one scenario's alternating process."""

    scenario: AttackScenario
    mean_deny: float
    """Mean length of a denying episode (h)."""
    mean_degrade: float
    """Mean length of a degrading episode (h)."""
    p_idle: float
    p_degrade: float
    p_deny: float
    deny_frequency: float
    """Denial episodes started per hour, in the long run."""

    @property
    def equivalent_mtbf(self) -> float:
        """Mean time between denials: the MTBF of the attack seen as a failure mode."""
        return math.inf if self.deny_frequency == 0 else (1 - self.p_deny) / self.deny_frequency

    @property
    def equivalent_mttr(self) -> float:
        """Mean denial length: the MTTR of the attack seen as a failure mode."""
        return self.mean_deny

    @property
    def state_probabilities(self) -> tuple[float, float, float]:
        """``(P(idle), P(degrade), P(deny))``, summing to 1."""
        return (self.p_idle, self.p_degrade, self.p_deny)


def episode_means(s: AttackScenario) -> tuple[float, float]:
    """Mean lengths of denying and degrading episodes, ``(L_deny, L_degrade)``."""
    response = s.response_time
    effect = response if s.persistent else mean_min(s.duration, response)
    if s.kind is EffectKind.INTEGRITY:
        return effect, s.duration.mean  # missed: effect rule; caught: the attack's duration
    if s.kind is EffectKind.DELAY and not s.exceeds_deadline:
        return 0.0, effect
    return effect, 0.0


def scenario_process(s: AttackScenario) -> ScenarioProcess:
    """Stationary state probabilities and denial frequency of a scenario."""
    l_deny, l_degrade = episode_means(s)
    p = s.deny_probability
    if s.rate_per_hour == 0:
        return ScenarioProcess(s, l_deny, l_degrade, 1.0, 0.0, 0.0, 0.0)
    cycle = 1.0 / s.rate_per_hour + p * l_deny + (1.0 - p) * l_degrade
    p_deny = p * l_deny / cycle
    p_degrade = (1.0 - p) * l_degrade / cycle
    p_idle = (1.0 / s.rate_per_hour) / cycle
    frequency = p / cycle if l_deny > 0 else 0.0
    return ScenarioProcess(s, l_deny, l_degrade, p_idle, p_degrade, p_deny, frequency)


@dataclass(frozen=True)
class Timeline:
    """Sampled episodes of one scenario on ``[0, horizon)``: start, end and mode."""

    start: NDArray[np.float64]
    end: NDArray[np.float64]
    deny: NDArray[np.bool_]
    horizon: float

    def time_in(self, deny: bool) -> float:
        """Total time spent in denying (or degrading) episodes, clipped to the horizon."""
        mask = self.deny == deny
        return float((np.minimum(self.end[mask], self.horizon) - self.start[mask]).sum())


def episode_timeline(s: AttackScenario, horizon: float, rng: np.random.Generator) -> Timeline:
    """Sample the scenario's episodes over ``[0, horizon)``, starting idle at time 0.

    Episodes of zero length (a denial with no duration and no response time) are dropped.
    """
    if horizon <= 0:
        raise ValueError(f"horizon must be > 0, got {horizon}")
    empty = np.empty(0)
    if s.rate_per_hour == 0:
        return Timeline(empty, empty, np.empty(0, dtype=bool), horizon)
    starts: list[NDArray[np.float64]] = []
    ends: list[NDArray[np.float64]] = []
    denies: list[NDArray[np.bool_]] = []
    t = 0.0
    mean_cycle = 1.0 / s.rate_per_hour + max(episode_means(s))
    while t < horizon:
        n = int(1.2 * (horizon - t) / mean_cycle) + 16
        idle = rng.exponential(1.0 / s.rate_per_hour, n)
        deny, length = s.sample_episodes(rng, n)
        cycle_end = t + np.cumsum(idle + length)
        start = cycle_end - length
        keep = start < horizon
        starts.append(start[keep])
        ends.append(cycle_end[keep])
        denies.append(deny[keep])
        t = float(cycle_end[-1])
    start = np.concatenate(starts)
    end = np.concatenate(ends)
    deny = np.concatenate(denies)
    keep = end > start
    return Timeline(start[keep], end[keep], deny[keep], horizon)
