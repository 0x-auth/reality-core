from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Reading:
    step: int
    value: float
    source: str = "self"  # "self" or a traded-from identifier


def own_sequence(readings: list[Reading], looks: int) -> list[float] | None:
    """Self-observed values in step order — or None unless their steps are
    exactly 0..n-1 with n >= looks (gaps would let forged values go unchecked)."""
    own = sorted((r for r in readings if r.source == "self"), key=lambda r: r.step)
    if len(own) < looks or [r.step for r in own] != list(range(len(own))):
        return None
    return [r.value for r in own]
