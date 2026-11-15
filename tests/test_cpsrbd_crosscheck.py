"""Cross-check with CPS-02: the same synthetic system, computed by a different model.

CPS-02 (``cpsrbd`` v1.0.0, GMCavalheri/cyber-physical-rbd-attack-trees) models this system as
a unified RBD + attack-tree DAG in failure logic and computes the probability of losing
trusted navigation in one mission exactly (Shannon decomposition). With every cyber step
switched off (``origin_overrides(model, Origin.PHYSICAL)``) its result is the classical
reliability view. This project's success-logic structure, evaluated by state enumeration,
must give the same number: two independent implementations of one system.
"""

import pytest

from cyberrel.system_model import MISSION_HOURS, mission_reliability, navigation_system

cpsrbd = pytest.importorskip("cpsrbd")

from cpsrbd.consequence_driven_analysis import navigation_case_study  # noqa: E402
from cpsrbd.probability_likelihood_propagation import (  # noqa: E402
    exact_probability,
    origin_overrides,
)
from cpsrbd.unified_graph_model import Origin  # noqa: E402

# CPS-02 basic event -> this project's component (same failure rates, see the CSVs).
NAME_MAP = {
    "egi_1_hw": "egi_1",
    "egi_2_hw": "egi_2",
    "power_bus_1": "power_bus_1",
    "power_bus_2": "power_bus_2",
    "bus_ch_a": "bus_ch_a",
    "bus_ch_b": "bus_ch_b",
    "mc_hw": "mission_computer",
}


def test_pinned_version() -> None:
    assert cpsrbd.__version__ == "1.0.0"


def test_failure_rates_match_cps02() -> None:
    model = navigation_case_study()
    system = navigation_system()
    for event in model.basic_events():
        if event.name in NAME_MAP:
            rate = event.attributes["failure_rate"]
            assert system.component(NAME_MAP[event.name]).failure_rate == rate


@pytest.mark.parametrize("hours", [1.0, MISSION_HOURS, 100.0])
def test_physical_mission_unreliability_matches_cps02(hours: float) -> None:
    model = navigation_case_study(mission_hours=hours)
    expected = exact_probability(model, origin_overrides(model, Origin.PHYSICAL))
    got = 1.0 - mission_reliability(navigation_system(), hours)
    assert got == pytest.approx(expected, rel=1e-12)
