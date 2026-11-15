"""MTBF, MTTR and availability from an event log: the Fleet Reliability Dashboard definitions.

The definitions are those of the portfolio's Fleet Reliability Dashboard
(GMCavalheri/Aircraft-Fleet-Reliability-Dashboard, ``sql/02_views_metrics.sql`` and
``app/metrics.py``), re-implemented here because that project is an application, not an
importable package:

* ``MTBF = operating hours / number of failures``
* ``MTTR = mean repair (down) duration of the failures``
* ``A = MTBF / (MTBF + MTTR)``

Here "operating hours" are the hours the function was up. Then ``A`` equals
``up / (up + down)`` exactly, the fraction of time the function was available, whenever every
failure's down time is in the log (:func:`reliability_kpis` docstring).

A cyber outage enters the same log as a physical failure, with its own ``cause``, so the same
three numbers describe physical failures, cyber attacks, or both.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Outage:
    """One interval in which the system function was down.

    ``cause`` is ``"physical"``, ``"cyber"`` or ``"both"`` (an outage that started for one
    reason and was extended by the other); ``platform`` identifies the unit in a fleet.
    """

    platform: int
    start: float
    end: float
    cause: str

    def __post_init__(self) -> None:
        if not self.end >= self.start:
            raise ValueError(f"outage ends before it starts: {self.start} > {self.end}")

    @property
    def duration(self) -> float:
        """Length of the outage in hours."""
        return self.end - self.start


@dataclass(frozen=True)
class ReliabilityKpis:
    """The dashboard's three headline numbers, plus the inputs that produced them."""

    operating_hours: float
    failure_count: int
    down_hours: float
    mtbf: float
    mttr: float
    availability: float


def reliability_kpis(repair_hours: Sequence[float], operating_hours: float) -> ReliabilityKpis:
    """MTBF, MTTR and availability with the Fleet Reliability Dashboard formulas.

    With no failures MTBF and MTTR are undefined (NaN in the dashboard); here availability is
    then 1 if there were operating hours, which is the limit the formulas approach.
    When ``operating_hours`` is the up time and ``repair_hours`` lists every down interval,
    ``MTBF / (MTBF + MTTR) = up / (up + down)`` because both share the factor
    ``1 / failure_count``.
    """
    if operating_hours < 0:
        raise ValueError(f"operating hours must be >= 0, got {operating_hours}")
    if any(r < 0 for r in repair_hours):
        raise ValueError("repair hours must be >= 0")
    n = len(repair_hours)
    down = float(sum(repair_hours))
    if n == 0:
        return ReliabilityKpis(operating_hours, 0, 0.0, math.nan, math.nan, 1.0)
    mtbf = operating_hours / n
    mttr = down / n
    availability = mtbf / (mtbf + mttr) if mtbf + mttr > 0 else math.nan
    return ReliabilityKpis(operating_hours, n, down, mtbf, mttr, availability)


def kpis_from_outages(
    outages: Iterable[Outage], possessed_hours: float, causes: set[str] | None = None
) -> ReliabilityKpis:
    """Dashboard KPIs of the function over ``possessed_hours`` of calendar time.

    Operating hours are the possessed hours minus all down hours. ``causes`` keeps only the
    outages with those causes in the failure count and MTTR (for a by-cause view); the
    operating hours always use every outage.
    """
    outages = list(outages)
    down_all = sum(o.duration for o in outages)
    if down_all > possessed_hours + 1e-9:
        raise ValueError("outages last longer than the possessed hours")
    kept = [o.duration for o in outages if causes is None or o.cause in causes]
    return reliability_kpis(kept, max(possessed_hours - down_all, 0.0))
