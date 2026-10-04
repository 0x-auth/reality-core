"""
reality_core — the Mobius-dynamics engine behind the Reality game and
darmiyan-fs/self-referential-seed. Zero dependencies.

A "law" is a Mobius transformation x -> (a*x + b) / (c*x + d), classified by
the scale-invariant discriminant Delta = trace^2 - 4*det (the same Delta
used in darmiyan-fs/chain/verify.py):

    Delta > 0   hyperbolic   ("boost")     settled    — closes, has an arrow
    Delta = 0   parabolic    ("null")      drifting   — the seam
    Delta < 0   elliptic     ("rotation")  unresolved — cycles or never repeats

A Mobius law has exactly 3 degrees of freedom (up to scale), so it takes
exactly 4 observed states (3 transitions) to pin one down with certainty —
fewer than that and multiple sectors remain consistent with what's been
seen. That result is exact, not a game-design choice: see
https://github.com/0x-auth/darmiyan-fs (instants.py) and
https://github.com/0x-auth/self-referential-seed.
"""

from dataclasses import dataclass, field
from typing import Optional
import math
import random


@dataclass(frozen=True)
class Law:
    a: float
    b: float
    c: float
    d: float

    def step(self, x: float) -> float:
        denom = self.c * x + self.d
        if denom == 0:
            raise ZeroDivisionError("state hit the pole of this law")
        return (self.a * x + self.b) / denom

    @property
    def trace(self) -> float:
        return self.a + self.d

    @property
    def det(self) -> float:
        return self.a * self.d - self.b * self.c

    @property
    def delta(self) -> float:
        """Scale-invariant discriminant: Delta = trace^2 - 4*det.
        Scaling the matrix by k multiplies Delta by k^2, so its SIGN (not its
        value) is what classifies the sector, regardless of how the law's
        a,b,c,d happen to be scaled."""
        return self.trace ** 2 - 4 * self.det

    def sector(self, tol: float = 1e-9) -> str:
        d = self.delta
        if abs(d) < tol:
            return "parabolic"
        return "hyperbolic" if d > 0 else "elliptic"

    def fate(self) -> str:
        return {
            "hyperbolic": "settled",
            "parabolic": "drifting",
            "elliptic": "unresolved",
        }[self.sector()]


def mirror_C(x: float) -> float:
    """C(x) = 1 - x"""
    return 1 - x


def mirror_R(x: float) -> float:
    """R(x) = -1/x"""
    if x == 0:
        raise ZeroDivisionError("R(x) undefined at x = 0")
    return -1 / x


def random_law(rng: random.Random, sector: Optional[str] = None) -> Law:
    """Build a random normalized (det=1) Mobius law, optionally constrained
    to a given sector ('hyperbolic' | 'parabolic' | 'elliptic')."""
    if sector == "hyperbolic":
        t = rng.choice([1, -1]) * rng.uniform(2.1, 4.0)
    elif sector == "parabolic":
        t = rng.choice([2.0, -2.0])
    elif sector == "elliptic":
        t = rng.uniform(-1.99, 1.99)
    else:
        t = rng.uniform(-4.0, 4.0)

    # Build a,b,c,d with a+d = t and ad-bc = 1.
    a = t / 2 + rng.uniform(-0.5, 0.5)
    d = t - a
    c = rng.uniform(0.3, 1.5) * rng.choice([1, -1])
    # ad - bc = 1  =>  b = (ad - 1) / c
    b = (a * d - 1) / c
    return Law(a, b, c, d)


@dataclass
class Reading:
    step: int
    value: float
    source: str = "self"  # "self" or a traded-from identifier


def v_local(law: Law, readings: list[Reading], tol: float = 1e-6) -> bool:
    """Does every consecutive pair of self-observed readings satisfy the law?"""
    own = [r for r in readings if r.source == "self"]
    own.sort(key=lambda r: r.step)
    for a, b in zip(own, own[1:]):
        if b.step != a.step + 1:
            continue  # not consecutive, nothing to check
        if abs(b.value - law.step(a.value)) > tol:
            return False
    return True


def v_delta(claimed_law: Law, true_law: Law, tol: float = 1e-6) -> bool:
    """Does the claimed law sit in the same conjugacy class as the true one?
    Assumes both laws are det=1 normalized (as random_law produces).
    Note (from darmiyan-fs/chain/verify.py): this fixes the CONJUGACY CLASS,
    not the individual member — a valid chain from a different seed, or the
    same class run at a different tick rate, both pass this check too."""
    return abs(claimed_law.delta - true_law.delta) < tol
