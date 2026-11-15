"""Smoke tests: the figures build without error and show what they claim."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

from cyberrel import plotting  # noqa: E402
from cyberrel.metrics import StatusHours  # noqa: E402


def test_status_bars_stack_non_fmc_shares() -> None:
    plotting.use_style()
    cases = {
        "physical": StatusHours(90, 8, 2, 0, 0),
        "with attacks": StatusHours(80, 10, 2, 7, 1),
    }
    fig = plotting.status_bars(cases, title="t")
    ax = fig.axes[0]
    widths = sorted(round(p.get_width(), 9) for p in ax.patches)
    assert max(widths) == 10.0  # PMC share of the second case, in percent
    assert len(ax.patches) == 4 * len(cases)
    plt.close(fig)
