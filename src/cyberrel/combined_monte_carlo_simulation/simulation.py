"""Discrete-event Monte Carlo of a fleet under physical failures and cyber attacks.

Each platform of the fleet is simulated independently over ``[0, horizon)`` hours:

1. **Physical timelines.** Every component alternates exponential up periods and down periods
   drawn from its repair distribution, starting up at time 0.
2. **Attack timelines.** Every scenario alternates exponential idle periods and episodes
   (:func:`cyberrel.attack_to_metric_translation.episode_timeline`), starting idle.
3. **System state.** The union of all interval boundaries cuts the horizon into segments on
   which every state is constant. On each segment the function is evaluated with denials
   applied to whole groups (the same :func:`~cyberrel.attack_to_metric_translation.combined.
   function_up` as the closed form) and the time is classified FMC / PMC / NMC by cause.
4. **Event log.** Maximal runs of "function down" segments become :class:`Outage` records,
   with cause ``physical``, ``cyber`` or ``both``. The Fleet Reliability Dashboard formulas
   then turn the log into MTBF, MTTR and availability, the same way they would turn a
   maintenance log into them.

Random streams are keyed by ``(seed, platform, kind, index)`` through NumPy's
``SeedSequence``. A component's draws therefore never depend on which scenarios are present,
and with no scenarios the physical history is exactly the physical-only run's, segment for
segment. That is the reduction check of the plan.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy import stats

from cyberrel.attack_scenario_library.library import check_targets
from cyberrel.attack_scenario_library.scenarios import AttackScenario
from cyberrel.attack_to_metric_translation.combined import DEGRADE, DENY, IDLE, function_up
from cyberrel.attack_to_metric_translation.episodes import episode_timeline
from cyberrel.metrics.readiness import STATUSES, StatusHours, classify, status_hours
from cyberrel.metrics.reliability import Outage, ReliabilityKpis, kpis_from_outages
from cyberrel.system_model.components import Component
from cyberrel.system_model.system import System

PHYSICAL_STREAM, CYBER_STREAM = 0, 1
CAUSES = {2: "physical", 3: "cyber", 4: "both"}


def stream(seed: int, platform: int, kind: int, index: int) -> np.random.Generator:
    """An independent random stream for one process of one platform."""
    return np.random.default_rng(np.random.SeedSequence(seed, spawn_key=(platform, kind, index)))


def down_intervals(
    component: Component, horizon: float, rng: np.random.Generator
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Start and end of every down period of a component on ``[0, horizon)``."""
    if component.failure_rate == 0:
        return np.empty(0), np.empty(0)
    starts: list[NDArray[np.float64]] = []
    ends: list[NDArray[np.float64]] = []
    t = 0.0
    cycle = component.mtbf + component.mttr
    while t < horizon:
        n = int(1.2 * (horizon - t) / cycle) + 16
        up = rng.exponential(component.mtbf, n)
        down = component.repair.sample(rng, n)
        end = t + np.cumsum(up + down)
        start = end - down
        keep = start < horizon
        starts.append(start[keep])
        ends.append(end[keep])
        t = float(end[-1])
    return np.concatenate(starts), np.concatenate(ends)


def _inside(
    starts: NDArray[np.float64], ends: NDArray[np.float64], t: NDArray[np.float64]
) -> NDArray[np.bool_]:
    """For sorted, disjoint intervals: is each time point inside one of them?"""
    if len(starts) == 0:
        return np.zeros(t.shape, dtype=bool)
    idx = np.searchsorted(starts, t, side="right") - 1
    safe = np.clip(idx, 0, None)
    return (idx >= 0) & (t < ends[safe])


@dataclass(frozen=True)
class PlatformRun:
    """One platform's simulated history."""

    platform: int
    horizon: float
    status: StatusHours
    outages: tuple[Outage, ...]
    physical_down_hours: float
    """Hours in which physical failures alone took the function down (attacks ignored)."""

    @property
    def availability(self) -> float:
        """Share of the horizon with the function up."""
        return self.status.mc_rate

    @property
    def failures(self) -> int:
        """Function-loss events that started inside the horizon."""
        return len(self.outages)


def simulate_platform(
    system: System,
    scenarios: Sequence[AttackScenario],
    horizon: float,
    seed: int,
    platform: int = 0,
) -> PlatformRun:
    """Simulate one platform (see the module docstring)."""
    if horizon <= 0:
        raise ValueError(f"horizon must be > 0, got {horizon}")
    phys = {
        c.name: down_intervals(c, horizon, stream(seed, platform, PHYSICAL_STREAM, i))
        for i, c in enumerate(system.components)
    }
    attacks = {
        s.name: episode_timeline(s, horizon, stream(seed, platform, CYBER_STREAM, j))
        for j, s in enumerate(scenarios)
    }
    cuts = [np.array([0.0, horizon])]
    cuts += [x for st, en in phys.values() for x in (st, en)]
    cuts += [x for tl in attacks.values() for x in (tl.start, tl.end)]
    edges = np.unique(np.clip(np.concatenate(cuts), 0.0, horizon))
    left, right = edges[:-1], edges[1:]
    mid = (left + right) / 2
    length = right - left

    comps = {n: ~_inside(st, en, mid) for n, (st, en) in phys.items()}
    scen = {}
    for name, tl in attacks.items():
        state = np.full(mid.shape, IDLE, dtype=np.int64)
        for deny, value in ((False, DEGRADE), (True, DENY)):
            mask = tl.deny == deny
            state[_inside(tl.start[mask], tl.end[mask], mid)] = value
        scen[name] = state
    targets = {s.name: s.target_group for s in scenarios}

    up = function_up(system, comps, scen, targets)
    idle = {n: np.zeros_like(s) for n, s in scen.items()}
    perfect = {n: np.ones_like(c) for n, c in comps.items()}
    up_physical_only = function_up(system, comps, idle, targets)
    up_cyber_only = function_up(system, perfect, scen, targets)
    nothing_down = np.all(np.stack(list(comps.values())), axis=0)
    for s in scen.values():
        nothing_down = nothing_down & (s == IDLE)
    status_index = classify(up, nothing_down, up_physical_only, up_cyber_only)
    status = status_hours(status_index, length)

    outages = []
    down = ~up
    if down.any():
        change = np.flatnonzero(np.diff(np.concatenate([[False], down, [False]]).astype(np.int8)))
        for a, b in zip(change[::2], change[1::2], strict=True):
            kinds = set(status_index[a:b].tolist())
            cause = CAUSES[kinds.pop()] if len(kinds) == 1 else "both"
            outages.append(Outage(platform, float(left[a]), float(right[b - 1]), cause))
    physical_down = float(length[~up_physical_only].sum())
    return PlatformRun(platform, horizon, status, tuple(outages), physical_down)


@dataclass(frozen=True)
class Estimate:
    """A fleet mean with a two-sided Student-t confidence interval across platforms."""

    mean: float
    low: float
    high: float

    def contains(self, value: float) -> bool:
        """Is ``value`` inside the interval?"""
        return self.low <= value <= self.high


def t_interval(samples: NDArray[np.float64], confidence: float = 0.95) -> Estimate:
    """Mean and t confidence interval of independent per-platform values."""
    n = len(samples)
    mean = float(samples.mean())
    if n < 2:
        return Estimate(mean, -math.inf, math.inf)
    half = float(stats.t.ppf(0.5 + confidence / 2, n - 1) * samples.std(ddof=1) / math.sqrt(n))
    return Estimate(mean, mean - half, mean + half)


@dataclass(frozen=True)
class FleetResult:
    """A simulated fleet: every platform's run, and fleet-level metrics."""

    system: str
    scenarios: tuple[str, ...]
    horizon: float
    seed: int
    runs: tuple[PlatformRun, ...]

    @property
    def possessed_hours(self) -> float:
        """Platform-hours simulated."""
        return self.horizon * len(self.runs)

    @property
    def status(self) -> StatusHours:
        """Fleet status hours (the sum over platforms)."""
        total = StatusHours(0.0, 0.0, 0.0, 0.0, 0.0)
        for r in self.runs:
            total = total + r.status
        return total

    @property
    def outages(self) -> list[Outage]:
        """The fleet's outage log."""
        return [o for r in self.runs for o in r.outages]

    def kpis(self, causes: set[str] | None = None) -> ReliabilityKpis:
        """Dashboard MTBF, MTTR and availability from the outage log (optionally by cause)."""
        return kpis_from_outages(self.outages, self.possessed_hours, causes)

    def estimate(self, metric: str, confidence: float = 0.95) -> Estimate:
        """Confidence interval across platforms for ``availability``, ``failure_frequency``
        (function losses per hour) or a status share (``fmc``, ``pmc``, ``nmc_cyber``...)."""
        if metric == "availability":
            x = [r.availability for r in self.runs]
        elif metric == "failure_frequency":
            x = [r.failures / r.horizon for r in self.runs]
        elif metric in STATUSES:
            x = [getattr(r.status, metric) / r.horizon for r in self.runs]
        else:
            raise ValueError(f"unknown metric {metric!r}")
        return t_interval(np.asarray(x, dtype=float), confidence)


def simulate_fleet(
    system: System,
    scenarios: Sequence[AttackScenario] = (),
    platforms: int = 20,
    horizon: float = 1e5,
    seed: int = 0,
) -> FleetResult:
    """Simulate ``platforms`` independent copies of the system for ``horizon`` hours each."""
    check_targets(system, {s.name: s for s in scenarios})
    if len({s.name for s in scenarios}) != len(scenarios):
        raise ValueError("scenario names must be unique")
    if platforms < 1:
        raise ValueError("at least one platform is needed")
    runs = tuple(simulate_platform(system, scenarios, horizon, seed, p) for p in range(platforms))
    return FleetResult(system.name, tuple(s.name for s in scenarios), horizon, seed, runs)
