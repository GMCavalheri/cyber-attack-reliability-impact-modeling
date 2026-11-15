"""The effect-level scenario library: validation, loading and episode sampling."""

from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from cyberrel.attack_scenario_library import (
    VERIFIED_TECHNIQUES,
    AttackScenario,
    Duration,
    EffectKind,
    check_targets,
    fixed,
    load_scenarios,
)
from cyberrel.system_model import RepairKind, navigation_system


def dos(**changes: object) -> AttackScenario:
    base = AttackScenario(
        "dos", EffectKind.DENIAL, "data_bus", 1e-3, Duration(2.0, RepairKind.EXPONENTIAL), 0.25, 1.0
    )
    return base.with_changes(**changes)


def test_library_loads_and_targets_existing_groups() -> None:
    lib = load_scenarios()
    assert set(lib) == {
        "bus_flood_dos",
        "gnss_spoofing",
        "false_nav_injection",
        "message_delay_replay",
    }
    assert {s.kind for s in lib.values()} == set(EffectKind)
    check_targets(navigation_system(), lib)
    for s in lib.values():
        assert s.basis.startswith("assumption"), s.name
        assert s.rate_per_hour > 0


def test_technique_tags_are_verified() -> None:
    # Every tag must be one whose name was checked on attack.mitre.org (VERIFIED_TECHNIQUES).
    for s in load_scenarios().values():
        assert s.technique == "" or s.technique in VERIFIED_TECHNIQUES, s.name
    assert load_scenarios()["gnss_spoofing"].technique == ""  # RF domain: no ICS technique


def test_cps02_miss_probability_is_reused() -> None:
    # CPS-02's integrity_monitor_miss = 0.1 per spoofing episode.
    assert load_scenarios()["gnss_spoofing"].catch_probability == pytest.approx(0.9)


def test_deny_probability_by_kind() -> None:
    lib = load_scenarios()
    assert lib["bus_flood_dos"].deny_probability == 1.0
    assert lib["gnss_spoofing"].deny_probability == pytest.approx(0.1)
    assert lib["message_delay_replay"].exceeds_deadline
    assert lib["message_delay_replay"].deny_probability == 1.0
    slow = lib["message_delay_replay"].with_changes(added_latency_ms=40.0)
    assert slow.deny_probability == 0.0


def test_transient_episode_is_min_of_duration_and_response() -> None:
    s = dos(duration=fixed(3.0), time_to_detect=0.5, time_to_recover=1.0)
    deny, length = s.sample_episodes(np.random.default_rng(0), 5)
    assert deny.all()
    assert np.allclose(length, 1.5)
    short = s.with_changes(duration=fixed(0.2))
    assert np.allclose(short.sample_episodes(np.random.default_rng(0), 5)[1], 0.2)


def test_persistent_episode_lasts_the_whole_response() -> None:
    s = dos(duration=fixed(0.2), persistent=True)
    _, length = s.sample_episodes(np.random.default_rng(0), 3)
    assert np.allclose(length, s.response_time)


def test_caught_integrity_episodes_degrade_for_the_attack_duration() -> None:
    s = AttackScenario(
        "spoof",
        EffectKind.INTEGRITY,
        "nav_source",
        1e-3,
        fixed(0.7),
        0.5,
        2.0,
        persistent=True,
        catch_probability=0.9,
    )
    deny, length = s.sample_episodes(np.random.default_rng(3), 100_000)
    assert np.allclose(length[~deny], 0.7)
    assert np.allclose(length[deny], 2.5)
    # Binomial fraction of missed spoofs within 5 standard errors of 0.1.
    se = (0.1 * 0.9 / len(deny)) ** 0.5
    assert abs(deny.mean() - 0.1) < 5 * se


@given(
    d=st.floats(0.01, 50),
    td=st.floats(0, 10),
    tr=st.floats(0, 10),
    extra=st.floats(0, 10),
)
def test_episode_length_is_monotone_in_every_time(
    d: float, td: float, tr: float, extra: float
) -> None:
    def length(**kw: float) -> float:
        params = {"duration": fixed(d), "time_to_detect": td, "time_to_recover": tr} | kw
        s = dos(**params)
        return float(s.sample_episodes(np.random.default_rng(0), 1)[1][0])

    base = length()
    assert length(duration=fixed(d + extra)) >= base
    assert length(time_to_detect=td + extra) >= base
    assert length(time_to_recover=tr + extra) >= base


def test_validation_errors() -> None:
    with pytest.raises(ValueError):
        dos(name="not valid")
    with pytest.raises(ValueError):
        dos(rate_per_hour=-1.0)
    with pytest.raises(ValueError):
        dos(time_to_detect=float("inf"))
    with pytest.raises(ValueError):
        dos(catch_probability=0.5)  # denial cannot be caught at onset
    with pytest.raises(ValueError):
        dos(kind=EffectKind.INTEGRITY, catch_probability=1.5)
    with pytest.raises(ValueError):
        dos(added_latency_ms=10.0)
    with pytest.raises(ValueError):
        dos(technique="ICS-1")
    with pytest.raises(ValueError):
        check_targets(navigation_system(), {"x": dos(target_group="radar")})


def test_loader_rejects_bad_flags(tmp_path: Path) -> None:
    text = (Path(__file__).parents[1] / "src/cyberrel/data/attack_scenarios.csv").read_text()
    bad = tmp_path / "bad.csv"
    bad.write_text(text.replace(",false,", ",maybe,", 1))
    with pytest.raises(ValueError):
        load_scenarios(bad)
    good = tmp_path / "good.csv"
    good.write_text(text)
    assert load_scenarios(good) == load_scenarios()
