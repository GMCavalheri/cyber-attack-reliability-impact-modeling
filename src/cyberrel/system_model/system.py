"""A system: repairable components plus the structure that says when its function works."""

from __future__ import annotations

from dataclasses import dataclass

from cyberrel.system_model.components import Component
from cyberrel.system_model.structure import Block, components_in, describe

MAX_ENUMERATED_COMPONENTS = 20
"""Exact results enumerate every component state, so systems are kept small (2**20 states)."""


@dataclass(frozen=True)
class System:
    """Components and the success structure of one system function.

    The function is up when :func:`cyberrel.system_model.structure.evaluate` of ``structure``
    is True. Construction checks that every component is used by the structure and every name
    in the structure is a component.
    """

    name: str
    function: str
    components: tuple[Component, ...]
    structure: Block

    def __post_init__(self) -> None:
        names = [c.name for c in self.components]
        if len(set(names)) != len(names):
            raise ValueError("component names must be unique")
        used = components_in(self.structure)
        missing = sorted(set(used) - set(names))
        if missing:
            raise ValueError(f"structure uses unknown components: {missing}")
        unused = sorted(set(names) - set(used))
        if unused:
            raise ValueError(f"components not used by the structure: {unused}")
        if len(names) > MAX_ENUMERATED_COMPONENTS:
            raise ValueError(f"at most {MAX_ENUMERATED_COMPONENTS} components are supported")

    @property
    def names(self) -> list[str]:
        """Component names in declaration order."""
        return [c.name for c in self.components]

    def component(self, name: str) -> Component:
        """The component called ``name``."""
        for c in self.components:
            if c.name == name:
                return c
        raise KeyError(name)

    def groups(self) -> dict[str, list[str]]:
        """Component names by redundancy group, in declaration order."""
        out: dict[str, list[str]] = {}
        for c in self.components:
            out.setdefault(c.group, []).append(c.name)
        return out

    def members(self, group: str) -> list[str]:
        """Names of the components in ``group``."""
        try:
            return self.groups()[group]
        except KeyError:
            raise KeyError(f"no component group {group!r} in {self.name}") from None

    def summary(self) -> str:
        """One-line description of the structure."""
        return f"{self.name}: {describe(self.structure)}"
