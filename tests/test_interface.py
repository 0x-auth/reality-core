"""Plain-assertion tests, no pytest dependency. Run: python tests/test_interface.py"""

import json
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reality_core import LAWS, MobiusRecognizer, Reading
from reality_core.cli import main as cli_main

MOB = MobiusRecognizer()
SECTORS = ("hyperbolic", "parabolic", "elliptic")


def test_v01_imports_still_work():
    from reality_core import Law, random_law, v_local, v_delta  # noqa: F401


def test_every_registered_law_has_the_contract():
    for name, rec in LAWS.items():
        assert rec.law_type == name
        for attr in ("random_law", "initial_state", "fit", "verify", "from_dict"):
            assert callable(getattr(rec, attr)), (name, attr)
        law = rec.random_law(random.Random(0))
        assert law.name == name and law.looks == rec.looks
        for attr in ("step", "observe", "sector", "to_dict"):
            assert callable(getattr(law, attr)), (name, attr)
        assert rec.from_dict(law.to_dict()) == law


def test_mobius_fit_recovers_the_law():
    rng = random.Random(9)
    for _ in range(200):
        for sector in SECTORS:
            law = MOB.random_law(rng, sector)
            x = MOB.initial_state(rng)
            readings = []
            for i in range(4):
                readings.append(Reading(i, x))
                x = law.step(x)
            fitted = MOB.fit(readings)
            assert MOB.verify(fitted, readings)
            assert abs(abs(fitted.det) - 1) < 1e-9
            for probe in (0.37, 1.9, -2.4):
                assert abs(fitted.step(probe) - law.step(probe)) < 1e-6 * max(1, abs(law.step(probe)))


def test_verify_rejects_gaps_and_short_transcripts():
    rng = random.Random(1)
    law = MOB.random_law(rng)
    forged = [Reading(0, 1.0), Reading(2, 999.0), Reading(4, -5.0), Reading(6, 42.0)]
    assert MOB.verify(law, forged) is False
    assert MOB.verify(law, []) is False
    for rec in LAWS.values():
        assert rec.verify(rec.random_law(rng), forged) is False


def test_pre_020_transcript_still_verifies():
    rng = random.Random(4)
    law = MOB.random_law(rng)
    x = MOB.initial_state(rng)
    readings = []
    for i in range(4):
        readings.append({"step": i, "value": x, "source": "self"})
        x = law.step(x)
    old = {  # exact 0.1.0 shape: no law_type
        "seed": 4,
        "law": {"a": law.a, "b": law.b, "c": law.c, "d": law.d},
        "readings": readings,
        "claimed_sector": law.sector(),
        "true_sector": law.sector(),
    }
    path = os.path.join(tempfile.mkdtemp(), "old.json")
    with open(path, "w") as f:
        json.dump(old, f)
    assert cli_main(["verify", path]) == 0


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
