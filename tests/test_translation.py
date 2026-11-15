"""Attack-to-metric translation: closed forms, reductions, common mode and monotonicity."""

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy import integrate, stats

from cyberrel.attack_scenario_library import (
    AttackScenario,
    Duration,
    EffectKind,
    fixed,
    load_scenarios,
)
from cyberrel.attack_to_metric_translation import (
    combined_steady_state,
    common_mode_factor,
    episode_means,
    episode_timeline,
    group_is_necessary,
    mean_min,
    rank_scenarios,
    scenario_process,
    translate,
)
from cyberrel.attack_to_metric_translation.combined import joint_states
from cyberrel.system_model import (
    Component,
    Parallel,
    RepairDistribution,
    RepairKind,
    System,
    component_availability,
    navigation_system,
    steady_state,
    steady_state_status,
)

EXACT = 1e-12
LIB = load_scenarios()


def dos(group: str = "data_bus", **changes: object) -> AttackScenario:
    base = AttackScenario(
        "dos", EffectKind.DENIAL, group, 1e-3, Duration(2.0, RepairKind.EXPONENTIAL), 0.25, 1.0
    )
    return base.with_changes(**changes)


def unit(name: str, group: str, rate: float = 1e-3, mttr: float = 10.0) -> Component:
    return Component(name, rate, RepairDistribution(mttr, RepairKind.EXPONENTIAL), group)


# --- E[min(D, c)] -------------------------------------------------------------------------


@pytest.mark.parametrize("kind", list(RepairKind))
@pytest.mark.parametrize("c", [0.1, 1.0, 2.5, 40.0])
def test_mean_min_against_numerical_integration(kind: RepairKind, c: float) -> None:
    # Independent oracle: E[min(D, c)] = integral of the survival function from 0 to c.
    dist = Duration(2.0, kind, 0.8)
    if kind is RepairKind.EXPONENTIAL:
        survival = stats.expon(scale=2.0).sf
    elif kind is RepairKind.LOGNORMAL:
        survival = stats.lognorm(s=0.8, scale=math.exp(math.log(2.0) - 0.32)).sf
    else:

        def survival(t: float) -> float:
            return 1.0 if t < 2.0 else 0.0

    expected, _ = integrate.quad(survival, 0, c, points=[2.0] if c > 2.0 else None, limit=200)
    assert mean_min(dist, c) == pytest.approx(expected, rel=1e-9)


def test_mean_min_edges() -> None:
    assert mean_min(Duration(2.0), 0.0) == 0.0
    with pytest.raises(ValueError):
        mean_min(Duration(2.0), -1.0)


# --- one scenario as an alternating process ------------------------------------------------


@pytest.mark.parametrize("name", sorted(LIB))
def test_state_probabilities_sum_to_one(name: str) -> None:
    proc = scenario_process(LIB[name])
    assert sum(proc.state_probabilities) == pytest.approx(1.0, abs=EXACT)
    # Equivalent MTBF/(MTBF+MTTR) reproduces the non-denied share (renewal identity).
    if proc.deny_frequency:
        a = proc.equivalent_mtbf / (proc.equivalent_mtbf + proc.equivalent_mttr)
        assert a == pytest.approx(1 - proc.p_deny, rel=EXACT)


def test_denial_closed_form() -> None:
    # One idle period of mean 1/rate, then an outage of mean m(1 - exp(-c/m)).
    s = LIB["bus_flood_dos"]
    outage = 2.0 * -math.expm1(-1.25 / 2.0)
    proc = scenario_process(s)
    assert proc.mean_deny == pytest.approx(outage, rel=EXACT)
    assert proc.p_deny == pytest.approx(outage / (1 / 5e-4 + outage), rel=EXACT)
    assert proc.equivalent_mtbf == pytest.approx(1 / 5e-4, rel=EXACT)


def test_episode_means_by_kind() -> None:
    assert episode_means(LIB["gnss_spoofing"]) == pytest.approx((2.5, 1.0))
    benign = LIB["message_delay_replay"].with_changes(added_latency_ms=10.0)
    assert episode_means(benign)[0] == 0.0
    assert scenario_process(benign).deny_frequency == 0.0
    assert scenario_process(benign).equivalent_mtbf == math.inf
    idle = scenario_process(dos(rate_per_hour=0.0))
    assert idle.state_probabilities == (1.0, 0.0, 0.0)


@pytest.mark.parametrize("name", sorted(LIB))
def test_timeline_matches_the_renewal_formula(name: str) -> None:
    # 200 independent 2e5 h timelines; the mean share of time denied (and degraded) must lie
    # within 4 standard errors of the closed form. Seeded, so the check is deterministic.
    s, proc = LIB[name], scenario_process(LIB[name])
    rng = np.random.default_rng(7)
    horizon = 2e5
    deny, degrade = [], []
    for _ in range(200):
        tl = episode_timeline(s, horizon, rng)
        deny.append(tl.time_in(True) / horizon)
        degrade.append(tl.time_in(False) / horizon)
    for sample, expected in ((deny, proc.p_deny), (degrade, proc.p_degrade)):
        x = np.asarray(sample)
        se = x.std(ddof=1) / math.sqrt(len(x))
        assert abs(x.mean() - expected) <= 4 * se + 1e-15


def test_timeline_edges() -> None:
    rng = np.random.default_rng(0)
    assert len(episode_timeline(dos(rate_per_hour=0.0), 10.0, rng).start) == 0
    with pytest.raises(ValueError):
        episode_timeline(dos(), 0.0, rng)
    tl = episode_timeline(dos(rate_per_hour=1.0), 50.0, rng)
    assert np.all(tl.start < 50.0) and np.all(np.diff(tl.start) > 0)


# --- the combined steady state --------------------------------------------------------------


@pytest.mark.parametrize("egi,channels", [(1, 1), (2, 2), (3, 2)])
def test_no_scenarios_reduces_to_the_physical_baseline(egi: int, channels: int) -> None:
    system = navigation_system(egi, channels)
    combined, physical = combined_steady_state(system), steady_state(system)
    assert combined.availability == pytest.approx(physical.availability, rel=EXACT)
    assert combined.mtbf == pytest.approx(physical.mtbf, rel=EXACT)
    assert combined.mdt == pytest.approx(physical.mdt, rel=EXACT)
    status = steady_state_status(system)
    assert combined.fmc_rate == pytest.approx(status.fmc_rate, rel=EXACT)
    assert combined.status.nmc_cyber == 0.0


@pytest.mark.parametrize("channels", [1, 2, 3])
@pytest.mark.parametrize("name", ["bus_flood_dos", "false_nav_injection", "message_delay_replay"])
def test_common_mode_denial_is_one_series_block(channels: int, name: str) -> None:
    # A denial of a whole necessary group multiplies availability by 1 - P(deny), with no
    # credit for the redundancy inside the group.
    system = navigation_system(2, channels)
    s = LIB[name]
    assert group_is_necessary(system, s.target_group)
    factor = common_mode_factor(system, s)
    assert factor == pytest.approx(1 - scenario_process(s).p_deny, rel=EXACT)


def test_redundancy_does_not_dilute_a_common_mode_attack() -> None:
    # With perfect hardware the attacked availability is 1 - P(deny) for any channel count,
    # while physical-only data-path unavailability falls by orders of magnitude.
    s = LIB["bus_flood_dos"]
    for channels in (1, 2, 3):
        system = navigation_system(2, channels)
        perfect = System(
            system.name,
            system.function,
            tuple(c.__class__(c.name, 0.0, c.repair, c.group) for c in system.components),
            system.structure,
        )
        a = combined_steady_state(perfect, [s]).availability
        assert a == pytest.approx(1 - scenario_process(s).p_deny, rel=EXACT)


def test_partial_group_denial_by_hand() -> None:
    # Parallel(a, b) with a scenario denying only a's group: a is effectively up with
    # probability A_a (1 - q), so A = 1 - (1 - A_a (1 - q)) (1 - A_b).
    a, b = unit("a", "ga"), unit("b", "gb", 2e-3, 5.0)
    system = System("pair", "f", (a, b), Parallel("a", "b"))
    s = dos("ga")
    q = scenario_process(s).p_deny
    expected = 1 - (1 - component_availability(a) * (1 - q)) * (1 - component_availability(b))
    assert combined_steady_state(system, [s]).availability == pytest.approx(expected, rel=EXACT)
    assert not group_is_necessary(system, "ga")
    with pytest.raises(ValueError):
        common_mode_factor(system, s)


def test_failure_frequency_of_two_processes_in_series() -> None:
    # Function = component a AND not denied. It fails when a fails while not denied, or when
    # a denial starts while a is up: omega = nu_a (1 - q) + nu_s A_a.
    a = unit("a", "ga")
    system = System("one", "f", (a,), "a")
    s = dos("ga")
    proc = scenario_process(s)
    nu_a = 1 / (a.mtbf + a.mttr)
    a_a = component_availability(a)
    result = combined_steady_state(system, [s])
    expected = nu_a * (1 - proc.p_deny) + proc.deny_frequency * a_a
    assert result.failure_frequency == pytest.approx(expected, rel=EXACT)
    assert result.availability == pytest.approx(a_a * (1 - proc.p_deny), rel=EXACT)
    assert result.mtbf / (result.mtbf + result.mdt) == pytest.approx(result.availability)


def test_statuses_with_attacks() -> None:
    system = navigation_system()
    result = combined_steady_state(system, list(LIB.values()))
    assert result.status.possessed == pytest.approx(1.0, abs=EXACT)
    assert result.mc_rate == pytest.approx(result.availability, rel=EXACT)
    assert result.status.nmc_cyber > result.status.nmc_maintenance > result.status.nmc_both > 0
    # A degrading-only scenario costs FMC but not MC.
    benign = LIB["message_delay_replay"].with_changes(added_latency_ms=10.0)
    impact = translate(system, benign)
    assert impact.delta_availability == pytest.approx(0.0, abs=EXACT)
    assert impact.delta_fmc_rate > 0


def test_joint_state_weights_sum_to_one() -> None:
    procs = [scenario_process(s) for s in LIB.values()]
    js = joint_states(navigation_system(), procs)
    assert js.weight.sum() == pytest.approx(1.0, abs=EXACT)


def test_input_validation() -> None:
    system = navigation_system()
    with pytest.raises(ValueError):
        combined_steady_state(system, [dos("radar")])
    with pytest.raises(ValueError):
        combined_steady_state(system, [dos(), dos()])
    big = [dos(name=f"s{i}") for i in range(9)]
    with pytest.raises(ValueError):
        combined_steady_state(navigation_system(3, 3), big)


def test_ranking_is_sorted_and_impacts_consistent() -> None:
    system = navigation_system()
    ranked = rank_scenarios(system, list(LIB.values()))
    deltas = [i.delta_availability for i in ranked]
    assert deltas == sorted(deltas, reverse=True)
    for i in ranked:
        assert i.delta_availability > 0 and i.delta_mc_rate == pytest.approx(i.delta_availability)
        assert i.mtbf_ratio < 1 and i.delta_mtbf < 0
        assert i.unavailability_multiple == pytest.approx(
            i.delta_availability / i.baseline.unavailability
        )


# --- monotonicity (Hypothesis) --------------------------------------------------------------


def loss(**changes: object) -> float:
    return translate(navigation_system(), dos(**changes)).delta_availability


@settings(max_examples=40, deadline=None)
@given(
    mean=st.floats(0.05, 20),
    td=st.floats(0, 5),
    tr=st.floats(0, 5),
    rate=st.floats(1e-5, 1e-2),
    extra=st.floats(0.01, 5),
)
def test_impact_is_monotone(mean: float, td: float, tr: float, rate: float, extra: float) -> None:
    base = {"duration": Duration(mean), "time_to_detect": td, "time_to_recover": tr}
    b = loss(rate_per_hour=rate, **base)
    tol = 1e-15
    assert loss(rate_per_hour=rate, **(base | {"duration": Duration(mean + extra)})) >= b - tol
    assert loss(rate_per_hour=rate, **(base | {"time_to_detect": td + extra})) >= b - tol
    assert loss(rate_per_hour=rate, **(base | {"time_to_recover": tr + extra})) >= b - tol
    assert loss(rate_per_hour=rate * (1 + extra), **base) >= b - tol


def test_zero_rate_means_zero_impact() -> None:
    assert loss(rate_per_hour=0.0) == 0.0


@given(latency=st.floats(0, 200), extra=st.floats(0, 100))
def test_delay_impact_is_a_monotone_step_in_latency(latency: float, extra: float) -> None:
    s = LIB["message_delay_replay"]

    def p(lat: float) -> float:
        return scenario_process(s.with_changes(added_latency_ms=lat)).p_deny

    assert p(latency + extra) >= p(latency)
    assert (p(latency) > 0) == (latency > s.deadline_ms)


def test_fixed_duration_episode() -> None:
    s = dos(duration=fixed(0.5))
    assert scenario_process(s).mean_deny == pytest.approx(0.5, rel=EXACT)
