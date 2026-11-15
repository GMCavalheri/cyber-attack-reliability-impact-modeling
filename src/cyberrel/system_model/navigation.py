"""The synthetic system: navigation data delivered to a mission computer.

This is the architecture of the CPS-02 case study (``cpsrbd``, GMCavalheri/cyber-physical-
rbd-attack-trees), so the CPS series analyses one system. A generic, defense-representative
platform (no real system is modelled) carries two embedded GNSS/INS navigation units (EGI),
each powered from its own electrical bus, that publish navigation solutions on a dual-channel
data bus to a mission computer fed from both power buses.

The function is **"trusted navigation data reaches the mission computer"**. In success logic::

    series(
        parallel(series(egi_1, power_bus_1), series(egi_2, power_bus_2)),  # a source
        parallel(bus_ch_a, bus_ch_b),                                      # a data path
        mission_computer,                                                  # the consumer
        parallel(power_bus_1, power_bus_2),                                # its power
    )

The power buses appear twice, which is why exact results enumerate states. Failure rates are
CPS-02's; repair times are added here. Every value in ``data/system_parameters.csv`` states its
basis, and all of them are assumptions, not data from any real platform.

``egi_units`` and ``bus_channels`` change the redundancy for the Phase 5 sensitivity study:
extra units copy unit 1's parameters, and EGI ``i`` is powered from bus ``1 + (i - 1) % 2``.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, replace
from importlib import resources
from pathlib import Path

from cyberrel.system_model.components import Component, RepairDistribution, RepairKind
from cyberrel.system_model.structure import Block, Parallel, Series
from cyberrel.system_model.system import System

FUNCTION = "Trusted navigation data reaches the mission computer"
MISSION_HOURS = 10.0
"""One mission, as in CPS-02 (assumption)."""
CHANNEL_LETTERS = "abcdefgh"


@dataclass(frozen=True)
class ComponentRow:
    """One row of the parameter table."""

    name: str
    group: str
    description: str
    failure_rate_per_hour: float
    mttr_hours: float
    repair_kind: str
    repair_sigma: float
    basis: str

    def to_component(self, name: str | None = None) -> Component:
        """The component described by this row (optionally renamed)."""
        repair = RepairDistribution(
            self.mttr_hours, RepairKind(self.repair_kind), self.repair_sigma
        )
        return Component(
            name or self.name,
            self.failure_rate_per_hour,
            repair,
            self.group,
            self.description,
            self.basis,
        )


def load_parameters(path: Path | None = None) -> dict[str, ComponentRow]:
    """Read the system parameter table, keyed by component name."""
    if path is None:
        text = resources.files("cyberrel.data").joinpath("system_parameters.csv").read_text()
    else:
        text = path.read_text()
    rows = {}
    for r in csv.DictReader(text.splitlines()):
        rows[r["name"]] = ComponentRow(
            name=r["name"],
            group=r["group"],
            description=r["description"],
            failure_rate_per_hour=float(r["failure_rate_per_hour"]),
            mttr_hours=float(r["mttr_hours"]),
            repair_kind=r["repair_kind"],
            repair_sigma=float(r["repair_sigma"]),
            basis=r["basis"],
        )
    return rows


def navigation_system(
    egi_units: int = 2,
    bus_channels: int = 2,
    parameters: Path | None = None,
) -> System:
    """Build the navigation system with the given redundancy (default: CPS-02's 2 and 2)."""
    if not 1 <= egi_units <= 8 or not 1 <= bus_channels <= len(CHANNEL_LETTERS):
        raise ValueError("egi_units and bus_channels must be between 1 and 8")
    rows = load_parameters(parameters)
    egis = [rows["egi_1"].to_component(f"egi_{i}") for i in range(1, egi_units + 1)]
    if egi_units >= 2:
        egis[1] = rows["egi_2"].to_component()
    egis = [replace(e, description=f"Embedded GNSS/INS navigation unit {e.name[4:]}") for e in egis]
    channels = [
        rows["bus_ch_a"].to_component(f"bus_ch_{CHANNEL_LETTERS[j]}") for j in range(bus_channels)
    ]
    if bus_channels >= 2:
        channels[1] = rows["bus_ch_b"].to_component()
    channels = [
        replace(c, description=f"Data bus channel {c.name[-1].upper()} (cable and transceivers)")
        for c in channels
    ]
    power = [rows["power_bus_1"].to_component(), rows["power_bus_2"].to_component()]
    computer = rows["mission_computer"].to_component()

    sources: list[Block] = [Series(e.name, f"power_bus_{1 + (i % 2)}") for i, e in enumerate(egis)]
    structure = Series(
        Parallel(*sources),
        Parallel(*(c.name for c in channels)),
        computer.name,
        Parallel(*(p.name for p in power)),
    )
    return System(
        name=f"navigation ({egi_units} EGI, {bus_channels} bus channels)",
        function=FUNCTION,
        components=(*egis, *power, *channels, computer),
        structure=structure,
    )
