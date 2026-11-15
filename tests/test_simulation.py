"""Combined Monte Carlo: exact reduction, convergence to the closed forms, and accounting.

Statistical checks use fixed seeds and 99.9 % Student-t intervals across platforms, so each
check is deterministic. The interval is wide enough that a correct simulation fails it about
once in a thousand seeds, and narrow enough to catch a biased one.
"""

import math

import numpy as np
import pytest

from cyberrel.attack_scenario_library import load_scenarios
from cyberrel.attack_to_metric_translation import combined_steady_state
from cyberrel.combined_monte_carlo_simulation import (
    FleetResult,
    down_intervals,
    simulate_fleet,
    simulate_platform,
    t_interval,
)
from cyberrel.system_model import Component, RepairDistribution, RepairKind, navigation_system

LIB = load_scenarios()
SCENARIOS = list(LIB.values())
SYSTEM = navigation_system()
CONFIDENCE = 0.999


@pytest.fixture(scope="module")
def physical_fleet() -> FleetResult:
    return simulate_fleet(SYSTEM, [], platforms=60, horizon=2e5, seed=11)


@pytest.fixture(scope="module")
def attacked_fleet() -> FleetResult:
    return simulate_fleet(SYSTEM, SCENARIOS, platforms=60, horizon=2e5, seed=11)


def test_down_intervals_are_an_alternating_renewal_process() -> None:
    c = Component("u", 1e-2, RepairDistribution(5.0, RepairKind.LOGNORMAL), "g")
    start, end = down_intervals(c, 1e6, np.random.default_rng(2))
    assert np.all(start > 0) and np.all(end > start) and np.all(start[1:] >= end[:-1])
    up_times = start - np.concatenate([[0.0], end[:-1]])
    # Exponential up times: mean MTBF = 100 h within 4 standard errors (std = mean).
    assert abs(up_times.mean() - 100.0) < 4 * 100.0 / math.sqrt(len(up_times))
    never = Component("p", 0.0, RepairDistribution(1.0), "g")
    assert len(down_intervals(never, 10.0, np.random.default_rng(0))[0]) == 0


def test_zero_rate_scenarios_do_not_perturb_the_physical_history() -> None:
    # Streams are keyed per process, so adding a scenario that never fires leaves every
    # physical draw, and hence the whole outage log, identical.
    silent = [s.with_changes(rate_per_hour=0.0) for s in SCENARIOS]
    a = simulate_fleet(SYSTEM, [], platforms=5, horizon=5e4, seed=3)
    b = simulate_fleet(SYSTEM, silent, platforms=5, horizon=5e4, seed=3)
    assert a.outages == b.outages
    assert a.status == b.status


def test_physical_history_is_unchanged_by_attacks(
    physical_fleet: FleetResult, attacked_fleet: FleetResult
) -> None:
    # Exact reduction: in the attacked run, the hours in which physical failures alone take
    # the function down equal the physical-only run's down hours, platform by platform.
    for p, a in zip(physical_fleet.runs, attacked_fleet.runs, strict=True):
        assert a.physical_down_hours == pytest.approx(p.status.nmc, rel=1e-12, abs=1e-9)


@pytest.mark.parametrize(
    "metric", ["availability", "failure_frequency", "fmc", "pmc", "nmc_maintenance"]
)
def test_physical_only_converges_to_closed_form(physical_fleet: FleetResult, metric: str) -> None:
    exact = combined_steady_state(SYSTEM)
    value = {
        "availability": exact.availability,
        "failure_frequency": exact.failure_frequency,
    }.get(metric, getattr(exact.status, metric, None))
    assert physical_fleet.estimate(metric, CONFIDENCE).contains(value)


@pytest.mark.parametrize(
    "metric", ["availability", "failure_frequency", "fmc", "pmc", "nmc_maintenance", "nmc_cyber"]
)
def test_attacked_fleet_converges_to_closed_form(attacked_fleet: FleetResult, metric: str) -> None:
    exact = combined_steady_state(SYSTEM, SCENARIOS)
    value = {
        "availability": exact.availability,
        "failure_frequency": exact.failure_frequency,
    }.get(metric, getattr(exact.status, metric, None))
    assert attacked_fleet.estimate(metric, CONFIDENCE).contains(value)


def test_downtime_accounting(attacked_fleet: FleetResult) -> None:
    for run in attacked_fleet.runs:
        assert run.status.possessed == pytest.approx(run.horizon, rel=1e-12)
        down = sum(o.duration for o in run.outages)
        assert down == pytest.approx(run.status.nmc, rel=1e-12)
    by_cause = {
        c: sum(o.duration for o in attacked_fleet.outages if o.cause == c)
        for c in ("physical", "cyber", "both")
    }
    assert sum(by_cause.values()) == pytest.approx(attacked_fleet.status.nmc, rel=1e-12)
    assert by_cause["cyber"] > by_cause["physical"] > 0


def test_dashboard_kpis_from_the_simulated_log(attacked_fleet: FleetResult) -> None:
    k = attacked_fleet.kpis()
    assert k.failure_count == len(attacked_fleet.outages)
    assert k.availability == pytest.approx(attacked_fleet.status.mc_rate, rel=1e-12)
    cyber = attacked_fleet.kpis({"cyber"})
    physical = attacked_fleet.kpis({"physical"})
    assert cyber.failure_count > physical.failure_count
    assert cyber.mttr < physical.mttr  # cyber outages are short (Lesson 3)


def test_platforms_are_independent_and_reproducible() -> None:
    a = simulate_platform(SYSTEM, SCENARIOS, 5e4, seed=4, platform=0)
    b = simulate_platform(SYSTEM, SCENARIOS, 5e4, seed=4, platform=1)
    again = simulate_platform(SYSTEM, SCENARIOS, 5e4, seed=4, platform=0)
    assert a.outages != b.outages
    assert a == again


def test_t_interval_and_validation() -> None:
    one = t_interval(np.array([0.5]))
    assert one.mean == 0.5 and math.isinf(one.low) and math.isinf(one.high)
    e = t_interval(np.array([1.0, 2.0, 3.0]))
    assert e.contains(2.0) and not e.contains(10.0)
    fleet = simulate_fleet(SYSTEM, [], platforms=2, horizon=100.0, seed=0)
    assert fleet.possessed_hours == 200.0
    with pytest.raises(ValueError):
        fleet.estimate("nope")
    with pytest.raises(ValueError):
        simulate_fleet(SYSTEM, [], platforms=0)
    with pytest.raises(ValueError):
        simulate_fleet(SYSTEM, [SCENARIOS[0], SCENARIOS[0]])
    with pytest.raises(ValueError):
        simulate_platform(SYSTEM, [], 0.0, seed=0)
