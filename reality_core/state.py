"""The state of one event, for any field: z = t + i/t.

A field only has to say what its cause t is (mirror.py gives a default
built from the round trip). Everything below follows from t alone, and
every identity is exact (tests/test_mirror.py):

    z = t + i/t,  z' = t - i/t        the event and its mirror view
    z^2 - z'^2 = 4i                   for every t
    t = (z + z') / 2                  the two views together give the cause back
    dt = t + 1/t,  dx = t - 1/t       dt^2 - dx^2 = 4 for every t
    u = ln|t|, turn = arg t           the clock: moving part and turning part
    observable  <=>  |dx| < |dt|      the edge is the 45-degree line

The self-seeding rule S -> dx + 1/S is the Mobius law Law(dx, 1, 1, 0).
For real t its Delta (trace^2 - 4*det) is exactly dt^2, and its error
multiplier is -1/t^2, which decides the sector for any t:

    |-1/t^2| != 1   hyperbolic   settled      (it rebuilds t, or -1/t)
    -1/t^2 == 1     parabolic    drifting     (t = +-i: dt = 0, the seam)
    otherwise       elliptic     unresolved   (|t| = 1: it only turns)
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass

from .mobius import FATE, Law

SIDE_NAMES = ("you", "retro", "twin", "retro_twin")


@dataclass(frozen=True)
class State:
    t: complex

    def __post_init__(self):
        if self.t == 0:
            raise ValueError("t = 0 has no state: it is the centre every mirror sends infinity to")

    # the event and its mirror view
    @property
    def z(self) -> complex:
        return self.t + 1j / self.t

    @property
    def z_mirror(self) -> complex:
        return self.t - 1j / self.t

    @classmethod
    def from_views(cls, z: complex, z_mirror: complex) -> "State":
        """Either view alone fits two causes; together they fit one."""
        return cls((z + z_mirror) / 2)

    # the two separations
    @property
    def dt(self) -> complex:
        return self.t + 1 / self.t

    @property
    def dx(self) -> complex:
        return self.t - 1 / self.t

    @property
    def speed(self) -> complex:
        """dx/dt. Below 1 in size: observable from here."""
        return self.dx / self.dt if self.dt != 0 else complex(math.inf)

    def observable(self) -> bool:
        """|dx| < |dt|. Since |dt|^2 - |dx|^2 = 4 cos(2*turn), this depends on
        the turn alone: within 45 degrees of the real axis, at every size."""
        return math.cos(2 * self.turn) > 1e-12

    # the clock
    @property
    def u(self) -> float:
        return math.log(abs(self.t))

    @property
    def turn(self) -> float:
        return cmath.phase(self.t)

    @classmethod
    def from_clock(cls, u: float, turn: float = 0.0) -> "State":
        return cls(cmath.exp(complex(u, turn)))

    # the four sides of one event
    def side(self, name: str) -> "State":
        t = self.t
        return State({"you": t, "retro": -1 / t, "twin": 1j / t, "retro_twin": -1j * t}[name])

    def sides(self) -> dict:
        return {n: self.side(n) for n in SIDE_NAMES}

    # the fixed rule that rebuilds the cause from the stored difference
    @property
    def multiplier(self) -> complex:
        """Each step of S -> dx + 1/S multiplies the error by this."""
        return -1 / self.t ** 2

    def sector(self, tol: float = 1e-9) -> str:
        lam = self.multiplier
        if abs(lam - 1) < tol:
            return "parabolic"
        if abs(abs(lam) - 1) < tol:
            return "elliptic"
        return "hyperbolic"

    def fate(self) -> str:
        return FATE[self.sector()]

    def law(self) -> Law:
        """The rebuilding rule as a reality-core Law (real dx only)."""
        dx = self.dx
        if abs(dx.imag) > 1e-12 * max(1.0, abs(dx)):
            raise ValueError("Law takes real coefficients; this t has a complex dx")
        return Law(dx.real, 1.0, 1.0, 0.0)

    def rebuild(self, start: complex = 0.3 + 0.7j, steps: int = 400) -> complex:
        """Run S -> dx + 1/S. Off the circle |t| = 1 it lands on whichever of
        t and -1/t lies outside the circle; on the circle it keeps turning."""
        s, b = start, self.dx
        for _ in range(steps):
            s = b + 1 / s
        return s

    def to_dict(self) -> dict:
        return {"t": [self.t.real, self.t.imag]}

    @classmethod
    def from_dict(cls, d: dict) -> "State":
        return cls(complex(*d["t"]))
