"""The mirror layer: one contract for any field, one state for every output.

A field is any step that turns one thing into another and is sometimes
wrong: reading a page, summarising a chat, fitting a law, remembering.
It plugs in by giving three functions (and optionally a fourth):

    forward(x)        -> y       the becoming: cause to effect
    mirror(y)         -> back    the other side: effect back toward the cause
    compare(x, back)  -> float   how far the round trip misses (0 = whole)
    view(x, y)        -> float   optional: how much an independent second
                                 view disagrees (0 = agrees)

The core never looks inside a field. It runs the round trip, places the
line between trusted and review once from a few known-right examples,
and turns every output into a State (state.py):

    |t|   = line / residual          > 1: our side of the line
    arg t = 45 degrees * view / view_line
    trusted  <=>  |t| > 1 and the state is observable (|dx| < |dt|)

so a small miss puts the output on our side, and a second view that
disagrees past its own line turns it over the 45-degree edge.
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional, Protocol

from .state import State


class Field(Protocol):
    name: str

    def forward(self, x: Any) -> Any: ...
    def mirror(self, y: Any) -> Any: ...
    def compare(self, x: Any, back: Any) -> float: ...


@dataclass
class CallableField:
    """Wrap any functions as a field: an LLM call, an OCR engine, a parser."""
    name: str
    forward: Callable[[Any], Any]
    mirror: Callable[[Any], Any]
    compare: Callable[[Any, Any], float]
    view: Optional[Callable[[Any, Any], float]] = None


@dataclass
class Check:
    y: Any
    residual: float
    view: float = 0.0


@dataclass
class Routed:
    y: Any
    residual: float
    state: State
    status: str  # "trusted" or "review"


def best_line(scores: list, wrong: list) -> float:
    """The line that best separates wrong outputs from right ones (largest
    catch rate minus false-alarm rate). Lines sit between observed scores,
    so a perfect score of 0 never becomes the line itself."""
    u = sorted(set(scores))
    cands = [(a + b) / 2 for a, b in zip(u, u[1:])] + [math.inf]
    nb = sum(1 for w in wrong if w) or 1
    ng = sum(1 for w in wrong if not w) or 1

    def gain(c):
        return (sum(1 for s, w in zip(scores, wrong) if w and s >= c) / nb
                - sum(1 for s, w in zip(scores, wrong) if not w and s >= c) / ng)

    return max(cands, key=gain)


class Mirror:
    def __init__(self, field: Any, line: Optional[float] = None, view_line: Optional[float] = None):
        self.field = field
        self.line = line
        self.view_line = view_line

    def check(self, x: Any) -> Check:
        f = self.field
        y = f.forward(x)
        r = float(f.compare(x, f.mirror(y)))
        v = getattr(f, "view", None)
        return Check(y, r, float(v(x, y)) if callable(v) else 0.0)

    def calibrate(self, anchors: Iterable, same: Callable[[Any, Any], bool] = lambda a, b: a == b) -> float:
        """anchors: [(x, y_true)]. Run once; after this no labels are needed."""
        checks, wrong = [], []
        for x, y_true in anchors:
            c = self.check(x)
            checks.append(c)
            wrong.append(not same(c.y, y_true))
        self.line = best_line([c.residual for c in checks], wrong)
        views = [c.view for c in checks]
        self.view_line = best_line(views, wrong) if any(views) else None
        if self.view_line is not None and not math.isfinite(self.view_line):
            self.view_line = None
        return self.line

    def state(self, c: Check) -> State:
        if self.line is None:
            raise ValueError("calibrate first, or pass line= to Mirror")
        size = 1e9 if not math.isfinite(self.line) else self.line / max(c.residual, 1e-12)
        size = min(max(size, 1e-9), 1e9)
        turn = 0.0 if not self.view_line else (math.pi / 4) * c.view / self.view_line
        return State(size * cmath.exp(1j * turn))

    def route(self, x: Any) -> Routed:
        c = self.check(x)
        s = self.state(c)
        ok = abs(s.t) > 1 and s.observable()
        return Routed(c.y, c.residual, s, "trusted" if ok else "review")
