"""Fields that ship with the mirror layer. Each is a forward step, its mirror
and a way to measure the miss. Zero dependencies. Anything else (an OCR
engine, a language model, a reading of a person) plugs in the same way
through CallableField; see the README.

    exact    bytes -> compressed -> bytes          both directions exact
    memory   t -> dx = t - 1/t -> rebuilt t        undecidable on |t| = 1
    law      readings -> fitted law -> replayed    4 looks fit any law; the 5th checks it
    text     source -> note -> claims found back   for summaries, notes, LLM output
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import Callable, Optional

from . import textcheck
from .reading import Reading, own_sequence
from .state import State


class ExactField:
    name = "exact"

    def forward(self, x: bytes) -> bytes:
        return zlib.compress(x)

    def mirror(self, y: bytes) -> bytes:
        return zlib.decompress(y)

    def compare(self, x: bytes, back: bytes) -> float:
        if len(x) != len(back):
            return 1.0
        return sum(a != b for a, b in zip(x, back)) / max(1, len(x))


class MemoryField:
    """Store only the difference dx = t - 1/t; the fixed rule rebuilds the rest."""
    name = "memory"

    def forward(self, t: complex) -> complex:
        return State(t).dx

    def mirror(self, dx: complex) -> complex:
        s = 0.3 + 0.7j
        for _ in range(400):
            s = dx + 1 / s
        return s

    def compare(self, t: complex, back: complex) -> float:
        return abs(t - back)


class LawField:
    """readings -> the law they imply -> the readings that law would give.

    With exactly `looks` readings every transcript fits some law, so the
    round trip cannot fail: the check only has power from the next look on.
    """
    name = "law"

    def __init__(self, law_type: str = "mobius"):
        from . import LAWS
        self.rec = LAWS[law_type]

    def _values(self, readings):
        xs = own_sequence([r if isinstance(r, Reading) else Reading(**r) for r in readings], self.rec.looks)
        if xs is None:
            raise ValueError(f"need self readings at steps 0..{self.rec.looks - 1} or more")
        return xs

    def forward(self, readings):
        xs = self._values(readings)
        law = self.rec.fit([Reading(i, v) for i, v in enumerate(xs)])
        start = (xs[0], xs[1]) if law.name == "linear" else xs[0]
        return law, start, len(xs)

    def mirror(self, y):
        law, state, n = y
        out = []
        for _ in range(n):
            out.append(law.observe(state))
            state = law.step(state)
        return out

    def compare(self, readings, back) -> float:
        xs = self._values(readings)
        return max(abs(a - b) / max(1.0, abs(a)) for a, b in zip(xs, back))


@dataclass
class TextField:
    """x = the source text. forward makes the note (a summary, a memory, an
    LLM answer), given as a function or a ready dict. The mirror looks every
    claim of the note back up in the source; the miss is the worst claim's."""
    note_for: Callable[[str], str]
    name: str = "text"

    def forward(self, source: str) -> str:
        return self.note_for(source)

    def mirror(self, note: str) -> str:
        return note

    def compare(self, source: str, note: str) -> float:
        return max((c["residual"] for c in self.claims(source, note)), default=0.0)

    @staticmethod
    def claims(source: str, note: str) -> list:
        """Per-claim residuals, skipping lines with nothing to check (rules, bare labels)."""
        return [c for c in textcheck.check(source, note)["claims"] if c["matched"] or c["missing"]]
