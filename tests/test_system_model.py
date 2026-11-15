"""System model and physical baseline, against closed forms.

Reference for the formulas: Rausand & Høyland, *System Reliability Theory*, 2nd ed. (2004):
alternating renewal availability (ch. 7), structure functions and k-out-of-n (ch. 3-4), and
system failure frequency via Birnbaum importance (ch. 13).
"""

import math

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from cyberrel.system_model import (
    MISSION_HOURS,
    Component,
    KOutOfN,
    Parallel,
    RepairDistribution,
    RepairKind,
    Series,
    System,
    availabilities,
    component_availability,
    k_out_of_n_identical,
    mission_reliability,
    navigation_system,
    steady_state,
    steady_state_status,
    system_availability,
)
from cyberrel.system_model.components import mission_reliability as unit_mission_reliability
from cyberrel.system_model.navigation import load_parameters
from cyberrel.system_model.structure import components_in, describe

EXACT = 1e-12


def unit(name: str, rate: float = 1e-3, mttr: float = 10.0, group: str = "g") -> Component:
    return Component(name, rate, RepairDistribution(mttr, RepairKind.EXPONENTIAL), group)


def test_component_availability_closed_form() -> None:
    c = unit("a", 1e-3, 10.0)
    assert c.mtbf == 1000.0
    assert component_availability(c) == pytest.approx(1000 / 1010, rel=EXACT)
    assert component_availability(unit("p", 0.0)) == 1.0
    assert unit("p", 0.0).mtbf == math.inf
    assert unit_mission_reliability(c, 100.0) == pytest.approx(math.exp(-0.1), rel=EXACT)


def test_series_and_parallel_closed_forms() -> None:
    comps = (unit("a", 1e-3, 10), unit("b", 2e-3, 5))
    a, b = (component_availability(c) for c in comps)
    series = System("s", "f", comps, Series("a", "b"))
    parallel = System("p", "f", comps, Parallel("a", "b"))
    assert system_availability(series) == pytest.approx(a * b, rel=EXACT)
    assert system_availability(parallel) == pytest.approx(1 - (1 - a) * (1 - b), rel=EXACT)


@given(
    n=st.integers(1, 6),
    data=st.data(),
    rate=st.floats(1e-5, 1e-1),
    mttr=st.floats(0.1, 100),
)
def test_k_out_of_n_matches_binomial(n: int, data: st.DataObject, rate: float, mttr: float) -> None:
    k = data.draw(st.integers(1, n))
    comps = tuple(unit(f"u{i}", rate, mttr) for i in range(n))
    system = System("k", "f", comps, KOutOfN(k, tuple(c.name for c in comps)))
    p = component_availability(comps[0])
    assert system_availability(system) == pytest.approx(k_out_of_n_identical(k, n, p), abs=EXACT)


def test_single_component_system_mtbf_is_component_mtbf() -> None:
    s = steady_state(System("one", "f", (unit("a", 1e-3, 10),), "a"))
    assert s.mtbf == pytest.approx(1000.0, rel=EXACT)
    assert s.mdt == pytest.approx(10.0, rel=EXACT)
    assert s.unavailability == pytest.approx(10 / 1010, rel=EXACT)


def test_parallel_pair_markov_result() -> None:
    # Two identical units, each with its own repair crew and exponential repair (rate mu):
    # the system is down only when both are, and leaves that state at rate 2 mu, so the mean
    # down time is 1 / (2 mu) = MTTR / 2 (Markov model of a parallel pair).
    lam, mttr = 1e-3, 10.0
    comps = (unit("a", lam, mttr), unit("b", lam, mttr))
    s = steady_state(System("pair", "f", comps, Parallel("a", "b")))
    a = component_availability(comps[0])
    assert s.mdt == pytest.approx(mttr / 2, rel=EXACT)
    assert s.failure_frequency == pytest.approx(2 * lam * a * (1 - a), rel=EXACT)
    assert s.mtbf / (s.mtbf + s.mdt) == pytest.approx(s.availability, rel=EXACT)


def test_perfect_system_never_fails() -> None:
    s = steady_state(System("p", "f", (unit("a", 0.0),), "a"))
    assert s.availability == 1.0 and s.mtbf == math.inf and s.mdt == 0.0


def test_navigation_availability_by_conditioning_on_the_power_buses() -> None:
    # Independent oracle: the power buses are the only shared components, so condition on
    # them (total probability) and the rest is series-parallel.
    system = navigation_system()
    a = availabilities(system)
    e1, e2, p1, p2 = a["egi_1"], a["egi_2"], a["power_bus_1"], a["power_bus_2"]
    path = 1 - (1 - a["bus_ch_a"]) * (1 - a["bus_ch_b"])
    source = p1 * p2 * (1 - (1 - e1) * (1 - e2)) + p1 * (1 - p2) * e1 + (1 - p1) * p2 * e2
    expected = a["mission_computer"] * path * source
    assert system_availability(system) == pytest.approx(expected, rel=EXACT)


def test_navigation_mission_reliability_by_conditioning() -> None:
    system = navigation_system()
    t = MISSION_HOURS
    r = {c.name: math.exp(-c.failure_rate * t) for c in system.components}
    path = 1 - (1 - r["bus_ch_a"]) * (1 - r["bus_ch_b"])
    p1, p2, e1, e2 = r["power_bus_1"], r["power_bus_2"], r["egi_1"], r["egi_2"]
    source = p1 * p2 * (1 - (1 - e1) * (1 - e2)) + p1 * (1 - p2) * e1 + (1 - p1) * p2 * e2
    expected = r["mission_computer"] * path * source
    assert mission_reliability(system, t) == pytest.approx(expected, rel=EXACT)
    assert mission_reliability(system, 0.0) == 1.0


def test_status_probabilities() -> None:
    system = navigation_system()
    status = steady_state_status(system)
    assert status.possessed == pytest.approx(1.0, abs=EXACT)
    assert status.fmc == pytest.approx(math.prod(availabilities(system).values()), rel=EXACT)
    assert status.mc_rate == pytest.approx(system_availability(system), rel=EXACT)
    assert status.nmc_cyber == 0.0 and status.nmc_both == 0.0


@pytest.mark.parametrize("egi,channels", [(1, 1), (2, 2), (3, 3), (1, 3)])
def test_redundancy_variants(egi: int, channels: int) -> None:
    system = navigation_system(egi, channels)
    assert len(system.members("nav_source")) == egi
    assert len(system.members("data_bus")) == channels
    assert system.members("power") == ["power_bus_1", "power_bus_2"]


def test_more_redundancy_never_lowers_availability() -> None:
    base = system_availability(navigation_system(2, 2))
    assert system_availability(navigation_system(3, 2)) >= base
    assert system_availability(navigation_system(2, 3)) >= base
    assert system_availability(navigation_system(1, 2)) <= base


def test_parameter_table_states_its_basis() -> None:
    rows = load_parameters()
    assert set(rows) == {
        "egi_1",
        "egi_2",
        "power_bus_1",
        "power_bus_2",
        "bus_ch_a",
        "bus_ch_b",
        "mission_computer",
    }
    for row in rows.values():
        assert "assumption" in row.basis, row.name
        assert row.mttr_hours > 0 and row.failure_rate_per_hour > 0


def test_structure_helpers() -> None:
    s = Series(Parallel("a", "b"), "c", KOutOfN(2, ("a", "b", "d")))
    assert components_in(s) == ["a", "b", "c", "d"]
    assert describe(s) == "series(parallel(a, b), c, 2-of-3(a, b, d))"
    assert describe(Series("a")) == "a"
    system = navigation_system()
    assert system.summary().startswith("navigation (2 EGI, 2 bus channels): series(")
    assert system.component("egi_1").group == "nav_source"
    with pytest.raises(KeyError):
        system.component("nope")
    with pytest.raises(KeyError):
        system.members("nope")


def test_validation_errors() -> None:
    with pytest.raises(ValueError):
        KOutOfN(1, ())
    with pytest.raises(ValueError):
        KOutOfN(3, ("a", "b"))
    with pytest.raises(ValueError):
        RepairDistribution(0.0)
    with pytest.raises(ValueError):
        RepairDistribution(1.0, RepairKind.LOGNORMAL, 0.0)
    with pytest.raises(ValueError):
        unit("not a name")
    with pytest.raises(ValueError):
        unit("a", -1.0)
    a = unit("a")
    with pytest.raises(ValueError):
        System("s", "f", (a, a), "a")
    with pytest.raises(ValueError):
        System("s", "f", (a,), Series("a", "b"))
    with pytest.raises(ValueError):
        System("s", "f", (a, unit("b")), "a")
    with pytest.raises(ValueError):
        navigation_system(0, 2)
    with pytest.raises(ValueError):
        mission_reliability(navigation_system(), -1.0)
    with pytest.raises(ValueError):
        unit_mission_reliability(unit("x"), -1.0)


@pytest.mark.parametrize("kind", list(RepairKind))
def test_repair_samples_have_the_stated_mean(kind: RepairKind) -> None:
    # Sample mean within 5 standard errors (deterministic seed; the bound is statistical).
    dist = RepairDistribution(4.0, kind, 0.8)
    x = dist.sample(np.random.default_rng(1), 200_000)
    se = x.std() / math.sqrt(len(x))
    assert abs(x.mean() - 4.0) <= 5 * se + EXACT
