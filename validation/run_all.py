"""Rerun every validation script, in phase order, and report the time each took.

    uv run python validation/run_all.py

Everything is exact or seeded, so a rerun reproduces the tables in ``validation/results/``
byte for byte; CI checks that with ``git diff --exit-code validation/results``. Figures go to
``docs/figures/`` (their pixels can differ slightly between platforms' font setups).
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = [
    ("baseline.py", "Phase 1: physical reliability baseline"),
    ("scenarios.py", "Phase 2: attack scenario library"),
    ("translation.py", "Phase 3: attack-to-metric translation"),
    ("combined.py", "Phase 4: combined Monte Carlo"),
    ("sensitivity.py", "Phase 5: sensitivity and mitigations"),
]


def main() -> int:
    for name, title in SCRIPTS:
        print(f"== {title}", flush=True)
        t0 = time.perf_counter()
        done = subprocess.run([sys.executable, str(HERE / name)], cwd=HERE.parent)
        if done.returncode:
            print(f"   {name} failed (exit {done.returncode})", flush=True)
            return done.returncode
        print(f"   done in {time.perf_counter() - t0:.1f} s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
