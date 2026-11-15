"""Sensitivity to redundancy and detection time, the tornado and the mitigation comparison."""

import math

import pytest

from cyberrel.attack_scenario_library import EffectKind, load_scenarios
from cyberrel.attack_to_metric_translation import combined_steady_state, scenario_process
from cyberrel.combined_monte_carlo_simulation import simulate_fleet
from cyberrel.sensitivity_analysis import (
    Design,
    GridPoint,
    evaluate_mitigations,
    redundancy_detection_grid,
    scale_group,
    tornado,
)
from cyberrel.system_model import navigation_system, system_availability

EXACT = 1e-12
LIB = load_scenarios()
SCENARIOS = list(LIB.values())


@pytest.fixture(scope="module")
def grid() -> list[GridPoint]:
    return redundancy_detection_grid(SCENARIOS)


def test_design_transforms_only_what_it_says() -> None:
    d = Design(detect_scale=0.5, recover_scale=2.0, rate_scale=0.1, miss_scale=0.1, deadline_ms=90)
    out = {s.name: s for s in d.scenarios(SCENARIOS)}
    for name, s in LIB.items():
        t = out[name]
        assert t.time_to_detect == pytest.approx(0.5 * s.time_to_detect)
        assert t.time_to_recover == pytest.approx(2.0 * s.time_to_recover)
        assert t.rate_per_hour == pytest.approx(0.1 * s.rate_per_hour)
        assert t.duration == s.duration
        if s.kind is EffectKind.INTEGRITY:
            assert 1 - t.catch_probability == pytest.approx(0.1 * (1 - s.catch_probability))
        if s.kind is EffectKind.DELAY:
            assert t.deadline_ms == 90
    capped = Design(miss_scale=100.0).scenarios(SCENARIOS)
    assert all(s.catch_probability >= 0 for s in capped)
    with pytest.raises(ValueError):
        Design(detect_scale=-1.0)


def test_attacked_availability_is_physical_times_each_scenarios_share(
    grid: list[GridPoint],
) -> None:
    # Every library scenario denies a whole necessary group (data bus or navigation sources),
    # and the processes are independent, so A = A_physical * prod_s (1 - P_s(deny)) exactly,
    # at every point of the grid (the series-block identity of Lesson 3, for several blocks).
    for p in grid:
        factor = math.prod(1 - scenario_process(s).p_deny for s in p.design.scenarios(SCENARIOS))
        assert p.combined.availability == pytest.approx(p.physical.availability * factor, rel=EXACT)


def test_redundancy_never_lowers_physical_availability() -> None:
    base = system_availability(navigation_system())
    kws: list[dict[str, int]] = [{"egi_units": 3}, {"bus_channels": 3}, {"mission_computers": 2}]
    for kw in kws:
        assert system_availability(navigation_system(**kw)) >= base
    assert system_availability(navigation_system(mission_computers=3)) >= system_availability(
        navigation_system(mission_computers=2)
    )


def test_faster_detection_never_lowers_availability(grid: list[GridPoint]) -> None:
    by_channels: dict[int, list[tuple[float, float]]] = {}
    for p in grid:
        by_channels.setdefault(p.design.bus_channels, []).append(
            (p.design.detect_scale, p.combined.unavailability)
        )
    for points in by_channels.values():
        points.sort()
        values = [u for _, u in points]
        assert values == sorted(values)


def test_closed_form_grid_point_matches_a_monte_carlo_spot_check() -> None:
    # The corner with one bus channel and four times slower detection, simulated
    # independently (99.9 % interval across 40 platforms).
    d = Design(bus_channels=1, detect_scale=4.0)
    exact = d.evaluate(SCENARIOS)
    fleet = simulate_fleet(d.system(), d.scenarios(SCENARIOS), platforms=40, horizon=2e5, seed=5)
    assert fleet.estimate("availability", 0.999).contains(exact.availability)
    assert fleet.estimate("failure_frequency", 0.999).contains(exact.failure_frequency)


def test_scale_group() -> None:
    system = navigation_system()
    scaled = scale_group(system, "data_bus", rate=2.0, mttr=3.0)
    for c, s in zip(system.components, scaled.components, strict=True):
        if c.group == "data_bus":
            assert s.failure_rate == 2 * c.failure_rate and s.mttr == 3 * c.mttr
        else:
            assert s == c


def test_tornado_bars_are_ordered_and_monotone() -> None:
    bars = tornado(navigation_system(), SCENARIOS)
    swings = [b.swing for b in bars]
    assert swings == sorted(swings, reverse=True)
    base = combined_steady_state(navigation_system(), SCENARIOS).unavailability
    # The sustained duration of a *persistent integrity* scenario only lengthens its caught
    # (degrading) episodes. Attacks pause during an episode, so a longer one lengthens the
    # cycle and slightly *reduces* denials: an artifact of the alternating-process assumption,
    # tiny here, documented in Lesson 5. Every other knob makes things worse as it grows.
    artifact = {
        f"{s.name}: sustained duration"
        for s in SCENARIOS
        if s.kind is EffectKind.INTEGRITY and s.persistent
    }
    for b in bars:
        assert b.base == pytest.approx(base, rel=EXACT)
        if b.parameter in artifact:
            assert b.high <= b.base <= b.low and b.swing < 1e-4 * base, b.parameter
        else:
            assert b.low <= b.base + EXACT and b.base <= b.high + EXACT, b.parameter
    names = {b.parameter for b in bars}
    assert "bus_flood_dos: attack rate" in names and "mission_computer: repair time" in names
    assert {b.origin for b in bars} == {"physical", "cyber"}
    with pytest.raises(ValueError):
        tornado(navigation_system(), SCENARIOS, factor=1.5)


def test_tornado_other_metrics() -> None:
    for metric in ("failure_frequency", "non_fmc"):
        bars = tornado(navigation_system(), SCENARIOS, metric=metric)
        assert bars[0].swing > 0


def test_a_third_bus_channel_buys_nothing_against_the_attacks() -> None:
    results = {r.name: r for r in evaluate_mitigations(SCENARIOS)}
    assert results["third bus channel"].unavailability_reduction < 1e-4
    assert results["detect twice as fast"].unavailability_reduction > 0.05
    ranked = list(results.values())
    cuts = [r.unavailability_reduction for r in evaluate_mitigations(SCENARIOS)]
    assert cuts == sorted(cuts, reverse=True)
    assert len(ranked) == 8


def test_timing_margin_removes_exactly_the_delay_scenarios_denial() -> None:
    # With a 100 ms deadline the 80 ms delay only degrades, so availability equals that of
    # the system attacked by the other three scenarios alone.
    results = {r.name: r for r in evaluate_mitigations(SCENARIOS)}
    others = [s for s in SCENARIOS if s.kind is not EffectKind.DELAY]
    expected = combined_steady_state(navigation_system(), others).availability
    assert results["timing margin above the delay"].result.availability == pytest.approx(
        expected, rel=EXACT
    )


def test_mitigation_gains_are_relative_to_the_baseline() -> None:
    r = evaluate_mitigations(SCENARIOS, [("none", "none", Design())])[0]
    assert r.unavailability_reduction == pytest.approx(0.0, abs=EXACT)
    assert r.mtbf_gain == pytest.approx(1.0, rel=EXACT)
    assert r.fmc_gain == pytest.approx(0.0, abs=EXACT)
