"""Sensitivity of the combined metrics to redundancy, detection time and every parameter.

Three views, all on the exact steady state of :mod:`cyberrel.attack_to_metric_translation`:

* :func:`redundancy_detection_grid` sweeps the number of bus channels, navigation units and
  mission computers against a common multiplier on every scenario's time to detect: the
  plan's "redundancy and detection time" study.
* :func:`tornado` moves each parameter (attack rates, durations, response times, miss
  probabilities, component failure rates and repair times) down and up by a factor and
  records the change in a metric.
* :func:`evaluate_mitigations` compares named design changes (a :class:`Design` each) by what
  they buy in availability, system MTBF and mission-capable rates.

A mitigation's *cost* is deliberately absent: costs are programme-specific, and inventing them
would turn a structural result into a fake business case. The outputs are the "benefit" half
of a cost-benefit analysis, in reliability units.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, replace

from cyberrel.attack_scenario_library.scenarios import AttackScenario, EffectKind
from cyberrel.attack_to_metric_translation.combined import (
    CombinedSteadyState,
    combined_steady_state,
)
from cyberrel.system_model.navigation import navigation_system
from cyberrel.system_model.system import System


@dataclass(frozen=True)
class Design:
    """A system configuration plus changes to the defenders' side of every scenario.

    ``detect_scale`` and ``recover_scale`` multiply every scenario's response times,
    ``rate_scale`` every attack rate (hardening or reduced exposure), and ``miss_scale`` the
    missed-detection probability ``1 - catch_probability`` of integrity scenarios (a better
    monitor). ``deadline_ms`` replaces delay scenarios' timeliness deadline (more timing
    margin designed into the consumer).
    """

    egi_units: int = 2
    bus_channels: int = 2
    mission_computers: int = 1
    detect_scale: float = 1.0
    recover_scale: float = 1.0
    rate_scale: float = 1.0
    miss_scale: float = 1.0
    deadline_ms: float | None = None

    def __post_init__(self) -> None:
        for name in ("detect_scale", "recover_scale", "rate_scale", "miss_scale"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be >= 0")

    def system(self) -> System:
        """The navigation system with this redundancy."""
        return navigation_system(
            self.egi_units, self.bus_channels, mission_computers=self.mission_computers
        )

    def scenarios(self, base: Sequence[AttackScenario]) -> list[AttackScenario]:
        """The scenarios as this design's defences change them."""
        out = []
        for s in base:
            changes: dict[str, object] = {
                "time_to_detect": s.time_to_detect * self.detect_scale,
                "time_to_recover": s.time_to_recover * self.recover_scale,
                "rate_per_hour": s.rate_per_hour * self.rate_scale,
            }
            if s.kind is EffectKind.INTEGRITY:
                miss = min(1.0, (1.0 - s.catch_probability) * self.miss_scale)
                changes["catch_probability"] = 1.0 - miss
            if s.kind is EffectKind.DELAY and self.deadline_ms is not None:
                changes["deadline_ms"] = self.deadline_ms
            out.append(s.with_changes(**changes))
        return out

    def evaluate(self, base: Sequence[AttackScenario]) -> CombinedSteadyState:
        """Exact combined steady state of this design under the (modified) scenarios."""
        return combined_steady_state(self.system(), self.scenarios(base))


@dataclass(frozen=True)
class GridPoint:
    """One cell of the redundancy x detection grid."""

    design: Design
    physical: CombinedSteadyState
    combined: CombinedSteadyState


def redundancy_detection_grid(
    base: Sequence[AttackScenario],
    bus_channels: Sequence[int] = (1, 2, 3),
    detect_scales: Sequence[float] = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0),
    egi_units: int = 2,
    mission_computers: int = 1,
) -> list[GridPoint]:
    """Exact metrics for every (bus channels, detection multiplier) pair."""
    out = []
    for n in bus_channels:
        physical = combined_steady_state(
            navigation_system(egi_units, n, mission_computers=mission_computers)
        )
        for k in detect_scales:
            d = Design(egi_units, n, mission_computers, detect_scale=k)
            out.append(GridPoint(d, physical, d.evaluate(base)))
    return out


Metric = Callable[[CombinedSteadyState], float]

METRICS: dict[str, Metric] = {
    "unavailability": lambda r: r.unavailability,
    "failure_frequency": lambda r: r.failure_frequency,
    "non_fmc": lambda r: 1.0 - r.fmc_rate,
}


def scale_group(system: System, group: str, rate: float = 1.0, mttr: float = 1.0) -> System:
    """A copy of ``system`` with the failure rate and mean repair time of a group scaled."""
    comps = tuple(
        replace(
            c,
            failure_rate=c.failure_rate * rate,
            repair=replace(c.repair, mean=c.repair.mean * mttr),
        )
        if c.group == group
        else c
        for c in system.components
    )
    return replace(system, components=comps)


@dataclass(frozen=True)
class TornadoBar:
    """A parameter moved down and up by ``factor``, and the metric at each end."""

    parameter: str
    origin: str
    low: float
    base: float
    high: float

    @property
    def swing(self) -> float:
        """``|high - low|``: the bar's length."""
        return abs(self.high - self.low)


@dataclass(frozen=True)
class _Knob:
    name: str
    origin: str
    apply: Callable[[float], CombinedSteadyState] = field(repr=False)


def _knobs(system: System, base: Sequence[AttackScenario]) -> list[_Knob]:
    knobs: list[_Knob] = []
    scen = list(base)

    def scenario_knob(
        i: int, label: str, change: Callable[[AttackScenario, float], AttackScenario]
    ) -> None:
        def apply(f: float) -> CombinedSteadyState:
            modified = [*scen]
            modified[i] = change(scen[i], f)
            return combined_steady_state(system, modified)

        knobs.append(_Knob(f"{scen[i].name}: {label}", "cyber", apply))

    for i, s in enumerate(scen):
        scenario_knob(
            i, "attack rate", lambda s, f: s.with_changes(rate_per_hour=s.rate_per_hour * f)
        )
        scenario_knob(
            i,
            "sustained duration",
            lambda s, f: s.with_changes(duration=replace(s.duration, mean=s.duration.mean * f)),
        )
        scenario_knob(
            i, "time to detect", lambda s, f: s.with_changes(time_to_detect=s.time_to_detect * f)
        )
        scenario_knob(
            i,
            "time to recover",
            lambda s, f: s.with_changes(time_to_recover=s.time_to_recover * f),
        )
        if s.kind is EffectKind.INTEGRITY:
            scenario_knob(
                i,
                "miss probability",
                lambda s, f: s.with_changes(
                    catch_probability=1.0 - min(1.0, (1.0 - s.catch_probability) * f)
                ),
            )
    for group in system.groups():

        def rate_apply(f: float, g: str = group) -> CombinedSteadyState:
            return combined_steady_state(scale_group(system, g, rate=f), scen)

        def mttr_apply(f: float, g: str = group) -> CombinedSteadyState:
            return combined_steady_state(scale_group(system, g, mttr=f), scen)

        knobs.append(_Knob(f"{group}: failure rate", "physical", rate_apply))
        knobs.append(_Knob(f"{group}: repair time", "physical", mttr_apply))
    return knobs


def tornado(
    system: System,
    base: Sequence[AttackScenario],
    metric: str = "unavailability",
    factor: float = 0.5,
) -> list[TornadoBar]:
    """Each parameter scaled by ``1 - factor`` and ``1 + factor``; bars sorted longest first."""
    if not 0 < factor < 1:
        raise ValueError("factor must be in (0, 1)")
    m = METRICS[metric]
    centre = m(combined_steady_state(system, list(base)))
    bars = [
        TornadoBar(k.name, k.origin, m(k.apply(1 - factor)), centre, m(k.apply(1 + factor)))
        for k in _knobs(system, base)
    ]
    return sorted(bars, key=lambda b: b.swing, reverse=True)


@dataclass(frozen=True)
class MitigationResult:
    """A design change and what it buys, relative to the baseline design."""

    name: str
    kind: str
    design: Design
    baseline: CombinedSteadyState
    result: CombinedSteadyState

    @property
    def unavailability_reduction(self) -> float:
        """Share of the baseline unavailability removed (0 to 1)."""
        return 1.0 - self.result.unavailability / self.baseline.unavailability

    @property
    def mtbf_gain(self) -> float:
        """System MTBF multiplier."""
        return self.result.mtbf / self.baseline.mtbf

    @property
    def fmc_gain(self) -> float:
        """Change in FMC rate (percentage points / 100)."""
        return self.result.fmc_rate - self.baseline.fmc_rate


DEFAULT_MITIGATIONS: tuple[tuple[str, str, Design], ...] = (
    ("third bus channel", "physical redundancy", Design(bus_channels=3)),
    ("third navigation unit", "physical redundancy", Design(egi_units=3)),
    ("second mission computer", "physical redundancy", Design(mission_computers=2)),
    ("detect twice as fast", "cyber: detection", Design(detect_scale=0.5)),
    ("recover twice as fast", "cyber: recovery", Design(recover_scale=0.5)),
    ("halve attack opportunities", "cyber: hardening", Design(rate_scale=0.5)),
    ("integrity monitor misses 10x less", "cyber: engineered control", Design(miss_scale=0.1)),
    ("timing margin above the delay", "cyber: engineered control", Design(deadline_ms=100.0)),
)
"""Candidate changes. "Timing margin" raises the consumer's deadline from 50 to 100 ms, so
the library's 80 ms delay no longer defeats the function (a design change, not a defence)."""


def evaluate_mitigations(
    base: Sequence[AttackScenario],
    mitigations: Sequence[tuple[str, str, Design]] = DEFAULT_MITIGATIONS,
    baseline: Design | None = None,
) -> list[MitigationResult]:
    """Each mitigation alone against the baseline design, largest unavailability cut first."""
    reference = Design() if baseline is None else baseline
    ref = reference.evaluate(base)
    results = [MitigationResult(n, k, d, ref, d.evaluate(base)) for n, k, d in mitigations]
    return sorted(results, key=lambda r: r.unavailability_reduction, reverse=True)
