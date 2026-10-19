from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional

from .reading import Reading, own_sequence

FATE = {"hyperbolic": "settled", "parabolic": "drifting", "elliptic": "unresolved"}


def classify(delta: float, tol: float = 1e-9) -> str:
    if abs(delta) < tol:
        return "parabolic"
    return "hyperbolic" if delta > 0 else "elliptic"


@dataclass(frozen=True)
class Law:
    a: float
    b: float
    c: float
    d: float

    name = "mobius"
    looks = 4  # 3 degrees of freedom -> 3 transitions -> 4 states

    def step(self, x: float) -> float:
        denom = self.c * x + self.d
        if denom == 0:
            raise ZeroDivisionError("state hit the pole of this law")
        return (self.a * x + self.b) / denom

    def observe(self, state: float) -> float:
        return state

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
        return classify(self.delta, tol)

    def fate(self) -> str:
        return FATE[self.sector()]

    def to_dict(self) -> dict:
        return {"a": self.a, "b": self.b, "c": self.c, "d": self.d}


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


def v_local(law: Law, readings: list[Reading], tol: float = 1e-6) -> bool:
    """Does every consecutive pair of self-observed readings satisfy the law?
    Pairwise only: gaps and missing readings are skipped, not rejected —
    use MobiusRecognizer.verify to check a whole transcript."""
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


def _det3(m: list[list[float]]) -> float:
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def _null_vector(rows: list[list[float]]) -> list[float]:
    """The vector orthogonal to three rows in R^4 (generalized cross product)."""
    return [(-1) ** j * _det3([[r[k] for k in range(4) if k != j] for r in rows])
            for j in range(4)]


class MobiusRecognizer:
    law_type = "mobius"
    looks = Law.looks

    def random_law(self, rng: random.Random, sector: Optional[str] = None) -> Law:
        return random_law(rng, sector)

    def initial_state(self, rng: random.Random) -> float:
        return rng.uniform(0.5, 3.0)

    def fit(self, readings: list[Reading]) -> Law:
        """The unique law (det normalized to +-1) through the first 4 readings.
        Each transition y = (a*x + b)/(c*x + d) is one linear equation
        a*x + b - c*x*y - d*y = 0; three of them fix (a, b, c, d) up to scale."""
        xs = own_sequence(readings, self.looks)
        if xs is None:
            raise ValueError(f"need self readings at steps 0..{self.looks - 1}")
        rows = [[x, 1.0, -x * y, -y] for x, y in zip(xs, xs[1:])][:3]
        a, b, c, d = _null_vector(rows)
        size = max(abs(a), abs(b), abs(c), abs(d))
        det = a * d - b * c
        if size == 0 or abs(det) < 1e-12 * size * size:
            raise ValueError("readings do not determine a unique law")
        k = 1 / math.sqrt(abs(det))
        return Law(a * k, b * k, c * k, d * k)

    def verify(self, claimed_law: Law, readings: list[Reading], tol: float = 1e-6) -> bool:
        xs = own_sequence(readings, self.looks)
        if xs is None:
            return False
        try:
            return all(abs(y - claimed_law.step(x)) <= tol for x, y in zip(xs, xs[1:]))
        except ZeroDivisionError:
            return False

    def from_dict(self, d: dict) -> Law:
        return Law(*(float(d[k]) for k in "abcd"))
