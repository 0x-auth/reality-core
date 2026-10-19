from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Optional, Tuple

from .mobius import FATE, classify
from .reading import Reading, own_sequence


@dataclass(frozen=True)
class LinearLaw:
    """x[n+2] = p*x[n+1] + q*x[n].

    On the ratio r = x[n+1]/x[n] this is the Mobius law r -> (p*r + q)/r,
    i.e. Law(p, q, 1, 0) — so Delta = p^2 + 4q and the three sectors carry
    over exactly. Fibonacci (p = q = 1) gives Delta = 5, like Law(1, 1, 1, 0)."""
    p: float
    q: float

    name = "linear"
    looks = 4  # 2 unknowns, one equation per reading after the first two

    def step(self, state: Tuple[float, float]) -> Tuple[float, float]:
        x0, x1 = state
        return (x1, self.p * x1 + self.q * x0)

    def observe(self, state: Tuple[float, float]) -> float:
        return state[0]

    @property
    def delta(self) -> float:
        return self.p ** 2 + 4 * self.q

    def sector(self, tol: float = 1e-9) -> str:
        return classify(self.delta, tol)

    def fate(self) -> str:
        return FATE[self.sector()]

    def to_dict(self) -> dict:
        return {"p": self.p, "q": self.q}


class LinearRecognizer:
    law_type = "linear"
    looks = LinearLaw.looks

    def random_law(self, rng: random.Random, sector: Optional[str] = None) -> LinearLaw:
        """Unconstrained: q < 0 and |p| / 2*sqrt(-q) uniform in (0, 2), so the
        hyperbolic/elliptic split is 50/50, as in the Mobius game."""
        if sector is None:
            q = -rng.uniform(0.5, 1.5)
            return LinearLaw(rng.uniform(-2.0, 2.0) * 2 * math.sqrt(-q), q)
        if sector == "hyperbolic":
            q = rng.choice([1, -1]) * rng.uniform(0.5, 1.5)
            edge = 2 * math.sqrt(-q) if q < 0 else 0.0
            return LinearLaw(rng.choice([1, -1]) * (edge + rng.uniform(0.1, 1.5)), q)
        if sector in ("parabolic", "elliptic"):
            q = -rng.uniform(0.5, 1.5)
            edge = 2 * math.sqrt(-q)
            if sector == "parabolic":
                return LinearLaw(rng.choice([1, -1]) * edge, q)
            return LinearLaw(rng.uniform(-0.95, 0.95) * edge, q)
        raise ValueError(f"unknown sector: {sector}")

    def initial_state(self, rng: random.Random) -> Tuple[float, float]:
        return (rng.uniform(0.5, 3.0), rng.uniform(0.5, 3.0))

    def fit(self, readings: list[Reading]) -> LinearLaw:
        """Solve [x1 x0; x2 x1] [p; q] = [x2; x3] from the first 4 readings."""
        xs = own_sequence(readings, self.looks)
        if xs is None:
            raise ValueError(f"need self readings at steps 0..{self.looks - 1}")
        x0, x1, x2, x3 = xs[:4]
        det = x1 * x1 - x0 * x2
        if abs(det) <= 1e-12 * max(x1 * x1, abs(x0 * x2)):
            raise ValueError("readings do not determine a unique law")
        return LinearLaw((x2 * x1 - x0 * x3) / det, (x1 * x3 - x2 * x2) / det)

    def verify(self, claimed_law: LinearLaw, readings: list[Reading], tol: float = 1e-9) -> bool:
        """Relative tolerance: hyperbolic sequences grow geometrically."""
        xs = own_sequence(readings, self.looks)
        if xs is None:
            return False
        p, q = claimed_law.p, claimed_law.q
        return all(abs(z - (p * y + q * x)) <= tol * max(1.0, abs(z))
                   for x, y, z in zip(xs, xs[1:], xs[2:]))

    def from_dict(self, d: dict) -> LinearLaw:
        return LinearLaw(float(d["p"]), float(d["q"]))
