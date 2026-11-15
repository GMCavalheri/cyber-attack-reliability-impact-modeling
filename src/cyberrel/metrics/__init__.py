"""The shared metric language: MTBF, MTTR, availability and mission-capable rates."""

from cyberrel.metrics.readiness import STATUSES, StatusHours, classify, status_hours
from cyberrel.metrics.reliability import (
    Outage,
    ReliabilityKpis,
    kpis_from_outages,
    reliability_kpis,
)

__all__ = [
    "STATUSES",
    "Outage",
    "ReliabilityKpis",
    "StatusHours",
    "classify",
    "kpis_from_outages",
    "reliability_kpis",
    "status_hours",
]
