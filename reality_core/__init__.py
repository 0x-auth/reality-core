"""
reality_core — the engine behind the Reality game and
darmiyan-fs/self-referential-seed. Zero dependencies.

Every law plugs into one contract (interface.py): a Recognizer can draw a
random law, fit a law from readings, and verify a claimed law against raw
readings — re-deriving it, not trusting whoever made the claim.

Two laws ship, both classified by a discriminant Delta:

    mobius   x -> (a*x + b) / (c*x + d)     Delta = trace^2 - 4*det
    linear   x[n+2] = p*x[n+1] + q*x[n]     Delta = p^2 + 4q

    Delta > 0   hyperbolic   ("boost")     settled    — closes, has an arrow
    Delta = 0   parabolic    ("null")      drifting   — the seam
    Delta < 0   elliptic     ("rotation")  unresolved — cycles or never repeats

Each takes exactly 4 readings to pin down — fewer and more than one sector
is still consistent with what's been seen. See
https://github.com/0x-auth/darmiyan-fs (instants.py) and
https://github.com/0x-auth/self-referential-seed.
"""

from .interface import LawType, Recognizer
from .reading import Reading
from .mobius import Law, MobiusRecognizer, mirror_C, mirror_R, random_law, v_delta, v_local
from .linear import LinearLaw, LinearRecognizer

LAWS = {"mobius": MobiusRecognizer(), "linear": LinearRecognizer()}

__all__ = [
    "LAWS", "Law", "LawType", "LinearLaw", "LinearRecognizer", "MobiusRecognizer",
    "Reading", "Recognizer", "mirror_C", "mirror_R", "random_law", "v_delta", "v_local",
]
