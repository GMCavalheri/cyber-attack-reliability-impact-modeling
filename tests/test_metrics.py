"""The metric language: dashboard KPIs and mission-capable statuses."""

import math

import numpy as np
import pytest

from cyberrel.metrics import (
    Outage,
    StatusHours,
    classify,
    kpis_from_outages,
    reliability_kpis,
    status_hours,
)


def test_dashboard_known_answer_fleet_kpis() -> None:
    # The Fleet Reliability Dashboard's own known-answer fixture (tests/test_metrics.py
    # there): three failures with 4, 2 and 6 repair hours over 150 flight hours give
    # MTBF 150/3, MTTR (4+2+6)/3 and availability 50/(50+4).
    k = reliability_kpis([4.0, 2.0, 6.0], 150.0)
    assert k.failure_count == 3
    assert k.mtbf == pytest.approx(150 / 3, rel=1e-12)
    assert k.mttr == pytest.approx(4.0, rel=1e-12)
    assert k.availability == pytest.approx(50 / 54, rel=1e-12)


def test_dashboard_known_answer_per_component() -> None:
    # Same fixture, by component: C1 failed twice (4 h, 2 h), C2 once (6 h).
    c1 = reliability_kpis([4.0, 2.0], 150.0)
    c2 = reliability_kpis([6.0], 150.0)
    assert c1.availability == pytest.approx(75 / 78, rel=1e-12)
    assert c2.availability == pytest.approx(150 / 156, rel=1e-12)


def test_no_failures() -> None:
    k = reliability_kpis([], 100.0)
    assert math.isnan(k.mtbf) and math.isnan(k.mttr)
    assert k.availability == 1.0


def test_availability_equals_up_fraction_when_operating_hours_are_up_time() -> None:
    # MTBF/(MTBF+MTTR) = up/(up+down): both share the factor 1/n.
    outages = [Outage(0, 10.0, 12.5, "physical"), Outage(0, 40.0, 41.0, "cyber")]
    k = kpis_from_outages(outages, 100.0)
    assert k.operating_hours == pytest.approx(96.5, rel=1e-12)
    assert k.availability == pytest.approx(96.5 / 100.0, rel=1e-12)


def test_by_cause_view_keeps_all_downtime_out_of_operating_hours() -> None:
    outages = [Outage(0, 10.0, 12.5, "physical"), Outage(0, 40.0, 41.0, "cyber")]
    cyber = kpis_from_outages(outages, 100.0, causes={"cyber"})
    assert cyber.failure_count == 1
    assert cyber.mtbf == pytest.approx(96.5, rel=1e-12)
    assert cyber.mttr == pytest.approx(1.0, rel=1e-12)


def test_invalid_inputs() -> None:
    with pytest.raises(ValueError):
        Outage(0, 5.0, 4.0, "physical")
    with pytest.raises(ValueError):
        reliability_kpis([1.0], -1.0)
    with pytest.raises(ValueError):
        reliability_kpis([-1.0], 1.0)
    with pytest.raises(ValueError):
        kpis_from_outages([Outage(0, 0.0, 20.0, "physical")], 10.0)
    with pytest.raises(ValueError):
        StatusHours(-1.0, 0, 0, 0, 0)


def test_status_rates_follow_the_public_definitions() -> None:
    # MC = FMC + PMC (GAO-03-300); rates are hours over possessed hours.
    h = StatusHours(fmc=600, pmc=200, nmc_maintenance=150, nmc_cyber=40, nmc_both=10)
    assert h.possessed == 1000
    assert h.mc_rate == pytest.approx(0.8, rel=1e-12)
    assert h.fmc_rate == pytest.approx(0.6, rel=1e-12)
    assert h.pmc_rate == pytest.approx(0.2, rel=1e-12)
    assert h.nmc_rate == pytest.approx(0.2, rel=1e-12)
    total = h + h
    assert total.mc_rate == pytest.approx(0.8, rel=1e-12)
    assert math.isnan(StatusHours(0, 0, 0, 0, 0).mc_rate)


def test_classify_every_case() -> None:
    # columns: up, all_up, up_without_cyber, up_without_physical -> expected status
    cases = [
        (True, True, True, True, 0),  # FMC
        (True, False, True, True, 1),  # PMC: degraded but up
        (False, False, False, True, 2),  # physical alone: NMCM
        (False, False, True, False, 3),  # cyber alone
        (False, False, False, False, 4),  # each alone suffices
        (False, False, True, True, 4),  # only the combination takes it down
    ]
    cols = [np.array([c[i] for c in cases]) for i in range(4)]
    assert classify(*cols).tolist() == [c[4] for c in cases]
    hours = status_hours(classify(*cols), np.arange(1.0, 7.0))
    assert (hours.fmc, hours.pmc, hours.nmc_maintenance, hours.nmc_cyber, hours.nmc_both) == (
        1.0,
        2.0,
        3.0,
        4.0,
        11.0,
    )
