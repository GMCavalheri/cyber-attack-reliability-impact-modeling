"""Phase 2: tabulate the effect-level scenario library and the episodes it produces."""

from __future__ import annotations

import numpy as np

from cyberrel.attack_scenario_library import VERIFIED_TECHNIQUES, check_targets, load_scenarios
from cyberrel.system_model import navigation_system

from common import table, write_result

SEED = 20261115
SAMPLES = 200_000


def main() -> None:
    system = navigation_system()
    lib = load_scenarios()
    check_targets(system, lib)

    params = table(
        [
            "scenario",
            "effect",
            "target group",
            "rate (/h)",
            "mean duration (h)",
            "detect (h)",
            "recover (h)",
            "persistent",
            "caught at onset",
            "ATT&CK for ICS",
        ],
        [
            [
                s.name,
                s.kind.value,
                f"{s.target_group} ({', '.join(system.members(s.target_group))})",
                s.rate_per_hour,
                s.duration.mean,
                s.time_to_detect,
                s.time_to_recover,
                "yes" if s.persistent else "no",
                s.catch_probability,
                f"{s.technique} {VERIFIED_TECHNIQUES[s.technique]}" if s.technique else "—",
            ]
            for s in lib.values()
        ],
    )
    descriptions = table(
        ["scenario", "effect on the system", "basis"],
        [[s.name, s.description, s.basis] for s in lib.values()],
    )
    rng = np.random.default_rng(SEED)
    rows = []
    for s in lib.values():
        deny, length = s.sample_episodes(rng, SAMPLES)
        rows.append(
            [
                s.name,
                s.deny_probability,
                float(deny.mean()),
                float(length[deny].mean()) if deny.any() else 0.0,
                float(length[~deny].mean()) if (~deny).any() else 0.0,
            ]
        )
    episodes = table(
        [
            "scenario",
            "P(deny) by definition",
            "P(deny) sampled",
            "mean deny length (h)",
            "mean degrade length (h)",
        ],
        rows,
    )
    write_result(
        "scenarios",
        "Phase 2 · The effect-level attack scenario library",
        [
            ("Parameters", params),
            ("What each scenario does", descriptions),
            (f"Episodes ({SAMPLES} samples per scenario, seed {SEED})", episodes),
        ],
    )


if __name__ == "__main__":
    main()
