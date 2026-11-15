"""The scenario library: load the effect-level scenarios from their parameter table."""

from __future__ import annotations

import csv
from importlib import resources
from pathlib import Path

from cyberrel.attack_scenario_library.scenarios import AttackScenario, Duration, EffectKind
from cyberrel.system_model.components import RepairKind
from cyberrel.system_model.system import System


def _flag(text: str) -> bool:
    if text.strip().lower() not in {"true", "false"}:
        raise ValueError(f"expected true or false, got {text!r}")
    return text.strip().lower() == "true"


def load_scenarios(path: Path | None = None) -> dict[str, AttackScenario]:
    """Read ``data/attack_scenarios.csv`` (or ``path``), keyed by scenario name."""
    if path is None:
        text = resources.files("cyberrel.data").joinpath("attack_scenarios.csv").read_text()
    else:
        text = path.read_text()
    out = {}
    for r in csv.DictReader(text.splitlines()):
        out[r["name"]] = AttackScenario(
            name=r["name"],
            kind=EffectKind(r["kind"]),
            target_group=r["target_group"],
            rate_per_hour=float(r["rate_per_hour"]),
            duration=Duration(float(r["duration_mean_hours"]), RepairKind(r["duration_kind"])),
            time_to_detect=float(r["time_to_detect_hours"]),
            time_to_recover=float(r["time_to_recover_hours"]),
            persistent=_flag(r["persistent"]),
            catch_probability=float(r["catch_probability"]),
            added_latency_ms=float(r["added_latency_ms"]),
            deadline_ms=float(r["deadline_ms"]),
            technique=r["technique"],
            description=r["description"],
            basis=r["basis"],
        )
    return out


def check_targets(system: System, scenarios: dict[str, AttackScenario]) -> None:
    """Raise if a scenario targets a component group the system does not have."""
    groups = system.groups()
    for s in scenarios.values():
        if s.target_group not in groups:
            raise ValueError(f"{s.name} targets unknown group {s.target_group!r}")
