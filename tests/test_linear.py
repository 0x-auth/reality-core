"""Plain-assertion tests, no pytest dependency. Run: python tests/test_linear.py"""

import builtins
import json
import os
import random
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reality_core import Law, LinearLaw, LinearRecognizer, Reading
from reality_core.cli import main as cli_main

REC = LinearRecognizer()
SECTORS = ("hyperbolic", "parabolic", "elliptic")


def run_readings(law, state, n):
    out = []
    for i in range(n):
        out.append(Reading(step=i, value=law.observe(state)))
        state = law.step(state)
    return out


def test_fibonacci_matches_golden_mobius():
    fib = LinearLaw(1, 1)
    assert fib.delta == 5 == Law(1, 1, 1, 0).delta
    assert fib.sector() == "hyperbolic"
    assert [r.value for r in run_readings(fib, (1, 1), 8)] == [1, 1, 2, 3, 5, 8, 13, 21]


def test_ratio_follows_mobius_law():
    rng = random.Random(3)
    for sector in SECTORS:
        law = REC.random_law(rng, sector)
        mob = Law(law.p, law.q, 1, 0)
        assert law.sector() == mob.sector() == sector
        xs = [r.value for r in run_readings(law, REC.initial_state(rng), 6)]
        for x0, x1, x2 in zip(xs, xs[1:], xs[2:]):
            assert abs(x2 / x1 - mob.step(x1 / x0)) < 1e-9


def test_sector_targeting():
    rng = random.Random(42)
    for _ in range(200):
        for sector in SECTORS:
            law = REC.random_law(rng, sector)
            assert law.sector() == sector, (sector, law)


def test_exact_fit_from_4_readings():
    rng = random.Random(7)
    for _ in range(200):
        for sector in SECTORS:
            law = REC.random_law(rng, sector)
            fitted = REC.fit(run_readings(law, REC.initial_state(rng), 4))
            assert abs(fitted.p - law.p) < 1e-9 * max(1, abs(law.p)), (law, fitted)
            assert abs(fitted.q - law.q) < 1e-9 * max(1, abs(law.q)), (law, fitted)
            assert fitted.sector() == sector


def test_three_readings_are_ambiguous():
    three = [1.0, 1.0, 0.0]
    candidates = [LinearLaw(1, -1), LinearLaw(4, -4), LinearLaw(-4, 4)]
    assert [c.sector() for c in candidates] == ["elliptic", "parabolic", "hyperbolic"]
    fourth = []
    for c in candidates:
        got = run_readings(c, (1.0, 1.0), 4)
        assert [r.value for r in got[:3]] == three
        fourth.append(got[3].value)
    assert len(set(fourth)) == 3  # the 4th look separates them
    try:
        REC.fit([Reading(i, v) for i, v in enumerate(three)])
        raise AssertionError("fit accepted only 3 readings")
    except ValueError:
        pass


def test_forgery_caught():
    rng = random.Random(11)
    law = REC.random_law(rng, "hyperbolic")
    readings = run_readings(law, REC.initial_state(rng), 6)
    assert REC.verify(law, readings) is True

    forged = list(readings)
    forged[3] = Reading(step=3, value=readings[3].value * 1.001)
    assert REC.verify(law, forged) is False

    gapped = [Reading(step=2 * r.step, value=r.value) for r in readings]
    assert REC.verify(law, gapped) is False
    assert REC.verify(law, readings[:3]) is False
    assert REC.verify(law, []) is False


def test_transcript_round_trip():
    path = os.path.join(tempfile.mkdtemp(), "run.json")
    real_input = builtins.input
    builtins.input = lambda prompt="": "elliptic"
    try:
        cli_main(["play", "--law", "linear", "--seed", "5", "--save", path])
    finally:
        builtins.input = real_input

    with open(path) as f:
        data = json.load(f)
    assert data["law_type"] == "linear" and set(data["law"]) == {"p", "q"}
    assert len(data["readings"]) == 4
    assert cli_main(["verify", path]) == 0

    data["readings"][2]["value"] += 0.5
    with open(path, "w") as f:
        json.dump(data, f)
    assert cli_main(["verify", path]) == 1


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
