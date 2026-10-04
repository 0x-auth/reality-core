"""Plain-assertion tests, no pytest dependency. Run: python tests/test_core.py"""

import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reality_core import Law, random_law, mirror_C, mirror_R, v_local, v_delta, Reading


def test_phi_law_is_hyperbolic():
    phi_law = Law(1, 1, 1, 0)
    assert phi_law.sector() == "hyperbolic"
    assert abs(phi_law.delta - 5) < 1e-9, phi_law.delta  # matches darmiyan-fs/chain/verify.py exactly


def test_mirrors_are_involutions_of_the_inverse():
    def finv(y):
        return 1 / (y - 1)

    law = Law(1, 1, 1, 0)
    x = 3.7
    for mirror in (mirror_C, mirror_R):
        lhs = mirror(law.step(mirror(x)))
        rhs = finv(x)
        assert abs(lhs - rhs) < 1e-9


def test_sector_targeting():
    rng = random.Random(42)
    for sector in ("hyperbolic", "parabolic", "elliptic"):
        law = random_law(rng, sector=sector)
        assert law.sector() == sector, (sector, law.sector(), law.delta)


def test_v_local_catches_forgery():
    rng = random.Random(42)
    law = random_law(rng, sector="hyperbolic")
    x = 1.3
    readings = []
    for i in range(5):
        readings.append(Reading(step=i, value=x))
        x = law.step(x)
    assert v_local(law, readings) is True

    forged = readings[:3] + [Reading(step=3, value=999.0), Reading(step=4, value=1000.0)]
    assert v_local(law, forged) is False


def test_v_delta_distinguishes_sectors():
    rng = random.Random(42)
    law = random_law(rng, sector="hyperbolic")
    other = random_law(rng, sector="elliptic")
    assert v_delta(law, law) is True
    assert v_delta(other, law) is False


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
