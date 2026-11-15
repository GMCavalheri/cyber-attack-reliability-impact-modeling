"""Mission-capable status and rates, from the public U.S. readiness definitions.

Public definitions (GAO-03-300, *Military Readiness: DOD Needs a Clear and Defined Process for
Setting Aircraft Availability Goals in the New Security Environment*, April 2003; GAO-23-106217,
*Weapon System Sustainment: Aircraft Mission Capable Goals Were Generally Not Met...*,
November 2022). U.S. Air Force status reporting itself is governed by DAFI 21-103,
*Equipment Inventory, Status and Utilization Reporting*.

* **FMC**, full mission capable: has all the mission-essential systems it needs to perform
  *all* of its missions.
* **PMC**, partial mission capable: can perform at least one of its missions, but not all.
* **MC = FMC + PMC.** The MC rate is the share of time the unit can perform at least one
  mission; rates are hours in the status divided by the hours the unit could have been
  available (*possessed hours* in USAF reporting).
* **NMC**, not mission capable, is the rest. Services split it into maintenance (NMCM) and
  supply (NMCS).

How this project maps its model onto those statuses (a modelling choice, stated in the docs):

* FMC: every component is up and no cyber effect is active.
* PMC: the function is up, but redundancy is degraded (a component is down or a cyber effect
  is active without defeating the function).
* NMC: the function is down. Spares are assumed always available, so there is no NMCS. NMC
  time is attributed to its cause: ``nmc_maintenance`` (physical failures alone would have
  taken the function down), ``nmc_cyber`` (a cyber effect alone would have), and
  ``nmc_both``. The cyber split is this project's attribution, **not** an official status
  code.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class StatusHours:
    """Hours spent in each status over ``possessed`` hours."""

    fmc: float
    pmc: float
    nmc_maintenance: float
    nmc_cyber: float
    nmc_both: float

    def __post_init__(self) -> None:
        if min(self.fmc, self.pmc, self.nmc_maintenance, self.nmc_cyber, self.nmc_both) < 0:
            raise ValueError("status hours must be >= 0")

    @property
    def possessed(self) -> float:
        """All hours: FMC + PMC + NMC."""
        return self.fmc + self.pmc + self.nmc

    @property
    def nmc(self) -> float:
        """Not-mission-capable hours, all causes."""
        return self.nmc_maintenance + self.nmc_cyber + self.nmc_both

    def rate(self, hours: float) -> float:
        """``hours / possessed``."""
        return hours / self.possessed if self.possessed > 0 else float("nan")

    @property
    def mc_rate(self) -> float:
        """Mission-capable rate, ``(FMC + PMC) / possessed``."""
        return self.rate(self.fmc + self.pmc)

    @property
    def fmc_rate(self) -> float:
        """Full-mission-capable rate, ``FMC / possessed``."""
        return self.rate(self.fmc)

    @property
    def pmc_rate(self) -> float:
        """Partial-mission-capable rate."""
        return self.rate(self.pmc)

    @property
    def nmc_rate(self) -> float:
        """Not-mission-capable rate, ``1 - MC rate``."""
        return self.rate(self.nmc)

    def __add__(self, other: StatusHours) -> StatusHours:
        return StatusHours(
            self.fmc + other.fmc,
            self.pmc + other.pmc,
            self.nmc_maintenance + other.nmc_maintenance,
            self.nmc_cyber + other.nmc_cyber,
            self.nmc_both + other.nmc_both,
        )


STATUSES = ("fmc", "pmc", "nmc_maintenance", "nmc_cyber", "nmc_both")


def classify(
    function_up: BoolArray,
    all_up: BoolArray,
    up_without_cyber: BoolArray,
    up_without_physical: BoolArray,
) -> NDArray[np.int64]:
    """Index into :data:`STATUSES` for each state or interval.

    ``function_up`` is the function with every effect applied, ``all_up`` says nothing at all
    is degraded, and the two ``up_without_*`` arrays are the function with only physical
    failures (no cyber effect) or only cyber effects (perfect hardware).

    A down function is ``nmc_maintenance`` when the physical failures alone take it down and
    the cyber effects alone would not, ``nmc_cyber`` in the mirror case, and ``nmc_both``
    otherwise: either both alone would, or only their combination does.
    """
    down = ~function_up
    physical_alone = ~up_without_cyber
    cyber_alone = ~up_without_physical
    status = np.full(function_up.shape, 4, dtype=np.int64)  # nmc_both
    status[down & physical_alone & ~cyber_alone] = 2
    status[down & cyber_alone & ~physical_alone] = 3
    status[function_up] = 1
    status[function_up & all_up] = 0
    return status


def status_hours(status: NDArray[np.int64], weights: NDArray[np.float64]) -> StatusHours:
    """Sum ``weights`` (hours or probabilities) by status index."""
    totals = np.bincount(status, weights=weights, minlength=len(STATUSES))
    return StatusHours(*(float(t) for t in totals))
