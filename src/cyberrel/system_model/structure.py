"""Reliability block structures in success logic.

A structure is a tree of :class:`Series`, :class:`Parallel` and :class:`KOutOfN` blocks whose
leaves are component names. A component may appear under several blocks (a power bus that
feeds both a sensor and the computer), so the structure is a *coherent* Boolean function of
the component states, not necessarily a series-parallel one with disjoint parts. That is why
exact probabilities are computed by enumeration in :mod:`cyberrel.system_model.closed_form`
rather than by multiplying block reliabilities.

:func:`evaluate` works on NumPy boolean arrays, so one call evaluates the structure for every
state of an enumeration or every interval of a simulation.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

BoolArray = NDArray[np.bool_]


@dataclass(frozen=True)
class KOutOfN:
    """Works when at least ``k`` of its children work."""

    k: int
    children: tuple[Block, ...]

    def __post_init__(self) -> None:
        if not self.children:
            raise ValueError("a block needs at least one child")
        if not 1 <= self.k <= len(self.children):
            raise ValueError(f"k must be in 1..{len(self.children)}, got {self.k}")


def Series(*children: Block) -> KOutOfN:
    """Works when every child works (n-out-of-n)."""
    return KOutOfN(len(children), tuple(children))


def Parallel(*children: Block) -> KOutOfN:
    """Works when at least one child works (1-out-of-n)."""
    return KOutOfN(1, tuple(children))


Block = KOutOfN | str
"""A block or a component name."""


def components_in(block: Block) -> list[str]:
    """Component names under ``block``, each once, in first-seen order."""
    if isinstance(block, str):
        return [block]
    seen: dict[str, None] = {}
    for child in block.children:
        for name in components_in(child):
            seen.setdefault(name, None)
    return list(seen)


def evaluate(block: Block, states: Mapping[str, BoolArray]) -> BoolArray:
    """Structure function: True where the block works, given each component's up-state."""
    if isinstance(block, str):
        return np.asarray(states[block], dtype=bool)
    working = sum(evaluate(child, states).astype(np.int64) for child in block.children)
    return np.asarray(working >= block.k, dtype=bool)


def describe(block: Block) -> str:
    """Compact text form, e.g. ``series(parallel(a, b), c)``."""
    if isinstance(block, str):
        return block
    n = len(block.children)
    inner = ", ".join(describe(c) for c in block.children)
    if block.k == n:
        return inner if n == 1 else f"series({inner})"
    if block.k == 1:
        return f"parallel({inner})"
    return f"{block.k}-of-{n}({inner})"
