"""Plain-assertion tests for the mirror layer, no pytest dependency.
Run: python tests/test_mirror.py"""

import cmath
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from reality_core import (LAWS, CallableField, ExactField, LawField, MemoryField, Mirror, Reading,
                          State, TextField, textcheck)

HERE = os.path.dirname(__file__)


def rand_t(rng):
    return cmath.rect(math.exp(rng.uniform(-2, 2)), rng.uniform(-math.pi, math.pi))


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol * max(1.0, abs(a), abs(b))


def test_state_identities():
    rng = random.Random(0)
    for _ in range(500):
        s = State(rand_t(rng))
        assert close(s.z ** 2 - s.z_mirror ** 2, 4j)
        assert close(State.from_views(s.z, s.z_mirror).t, s.t)
        assert close(s.dt ** 2 - s.dx ** 2, 4)
        sd = s.sides()
        assert close(sd["twin"].z, s.z) and close(sd["retro_twin"].z, sd["retro"].z)
        v = s.speed
        if s.dx != 0:
            assert close(sd["retro"].speed, -v) and close(sd["twin"].speed, -1 / v) and close(sd["retro_twin"].speed, 1 / v)
        assert s.observable() != sd["twin"].observable() or abs(abs(v) - 1) < 1e-9


def test_edge_is_45_degrees_at_every_size():
    for r in (0.2, 0.7, 1.0, 3.0, 40.0):
        for deg, want in ((30, True), (44, True), (46, False), (60, False), (134, False), (136, True)):
            assert State(cmath.rect(r, math.radians(deg))).observable() is want, (r, deg)


def test_clock_mirrors_are_reflections():
    rng = random.Random(1)
    wrap = lambda a: (a + math.pi) % (2 * math.pi) - math.pi
    for _ in range(200):
        s = State(rand_t(rng))
        u, th = s.u, s.turn
        for name, (u2, th2) in {"retro": (-u, math.pi - th), "twin": (-u, math.pi / 2 - th), "retro_twin": (u, th - math.pi / 2)}.items():
            o = s.side(name)
            assert close(o.u, u2) and abs(wrap(o.turn - th2)) < 1e-9, name


def test_sectors_and_the_rebuilding_law():
    rng = random.Random(2)
    for _ in range(200):
        t = rng.choice([1, -1]) * math.exp(rng.uniform(0.05, 2)) ** rng.choice([1, -1])
        s = State(t)
        law = s.law()
        assert close(law.delta, (s.dt ** 2).real) and law.sector() == "hyperbolic" == s.sector()
        outer = t if abs(t) > 1 else -1 / t
        assert close(s.rebuild(), outer, 1e-7)
    for t in (1j, -1j):
        assert State(t).sector() == "parabolic" and State(t).dt == 0
    for deg in (0, 20, 70, 110, 180):
        assert State(cmath.rect(1, math.radians(deg))).sector() == "elliptic"
    s = State(2.0)  # the error ratio of the rule is the multiplier
    b, x, errs = s.dx.real, 1.0, []
    for _ in range(12):
        x = b + 1 / x
        errs.append(x - 2.0)
    assert close(errs[-1] / errs[-2], s.multiplier.real, 1e-4)


def test_exact_field_comes_back_whole():
    rng = random.Random(3)
    m = Mirror(ExactField())
    data = [bytes(rng.randrange(256) for _ in range(rng.randrange(1, 300))) for _ in range(200)]
    assert max(m.check(d).residual for d in data) == 0.0
    m.calibrate([(d, ExactField().forward(d)) for d in data[:50]])
    assert all(m.route(d).status == "trusted" for d in data)


def test_memory_field_knows_where_it_cannot_decide():
    rng = random.Random(4)
    off = [cmath.rect(rng.uniform(1.05, 3), rng.uniform(-3.1, 3.1)) for _ in range(300)]
    on = [cmath.rect(1.0, rng.uniform(-3.1, 3.1)) for _ in range(300)]
    m = Mirror(MemoryField())
    m.calibrate([(t, t) for t in off[:150] + on[:150]], same=lambda b, t: abs(MemoryField().mirror(b) - t) < 1e-6)
    trusted = sum(m.route(t).status == "trusted" for t in off[150:])
    review = sum(m.route(t).status == "review" for t in on[150:])
    assert trusted == 150 and review >= 145, (trusted, review)


def test_law_field_needs_a_fifth_look():
    rng = random.Random(5)
    for law_type in ("mobius", "linear"):
        rec, f = LAWS[law_type], LawField(law_type)
        for _ in range(100):
            law, state = rec.random_law(rng), rec.initial_state(rng)
            xs = []
            for _ in range(6):
                xs.append(law.observe(state))
                state = law.step(state)
            if max(abs(x) for x in xs) > 1e6:
                continue
            rd = [Reading(i, x) for i, x in enumerate(xs)]
            assert f.compare(rd, f.mirror(f.forward(rd))) < 1e-6
            forged = [Reading(i, x * (1.3 if i == 5 else 1)) for i, x in enumerate(xs)]
            assert f.compare(forged, f.mirror(f.forward(forged))) > 1e-6
            four = forged[:4]  # exactly `looks` readings: any four fit some law
            try:
                assert f.compare(four, f.mirror(f.forward(four))) < 1e-6
            except ValueError:
                pass  # degenerate readings that fix no unique law


def test_textcheck_matches_the_browser_tool():
    with open(os.path.join(HERE, "textcheck_fixture.json")) as fh:
        docs = json.load(fh)
    n = 0
    for d in docs:
        got = textcheck.check(d["source"], d["note"])["claims"]
        assert len(got) == len(d["residual"]), d["name"]
        for c, r, nd, ms in zip(got, d["residual"], d["neg_diff"], d["missing"]):
            assert abs(c["residual"] - r) < 1e-12 and c["neg_diff"] == nd and c["missing"] == ms, c["text"]
            n += 1
    assert n == 96


def test_text_field_routes_a_changed_number():
    with open(os.path.join(HERE, "textcheck_fixture.json")) as fh:
        src = json.load(fh)[0]["source"]
    good = " ".join(textcheck.sentences(src)[:3])
    bad = good.replace("2", "7", 1) if "2" in good else good + " It costs 999."
    f = TextField(note_for=lambda s: s)
    m = Mirror(f, line=textcheck.LINE)
    f.note_for = lambda s: good
    assert m.route(src).status == "trusted"
    f.note_for = lambda s: bad
    assert m.route(src).status == "review"


def test_a_disagreeing_second_view_turns_it_over_the_edge():
    f = CallableField("toy", forward=lambda x: x["out"], mirror=lambda y: y, compare=lambda x, b: x["miss"], view=lambda x, y: x["view"])
    m = Mirror(f, line=0.5, view_line=0.2)
    assert m.route({"out": 1, "miss": 0.1, "view": 0.05}).status == "trusted"
    assert m.route({"out": 1, "miss": 0.1, "view": 0.25}).status == "review"   # turned past 45 degrees
    assert m.route({"out": 1, "miss": 0.9, "view": 0.0}).status == "review"    # the other side of the line
    s = m.route({"out": 1, "miss": 0.1, "view": 0.2}).state
    assert abs(math.degrees(s.turn) - 45) < 1e-9 and not s.observable()


def main():
    tests = [v for k, v in globals().items() if k.startswith("test_")]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} tests passed")


if __name__ == "__main__":
    main()
