"""
reality — a terminal game and verifier built on reality_core.

    reality play [--seed N]       guess the law's sector in exactly 4 looks
    reality verify <transcript>   check a transcript against its claimed law
"""

import argparse
import json
import random
import sys

from . import Law, Reading, random_law, v_local, v_delta

SECTOR_HINT = {
    "hyperbolic": "settled — it closes, it has an arrow",
    "parabolic": "drifting — the seam, the borderline case",
    "elliptic": "unresolved — it cycles, or never repeats",
}


def cmd_play(args: argparse.Namespace) -> int:
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    rng = random.Random(seed)
    law = random_law(rng)
    x = rng.uniform(0.5, 3.0)

    print("=" * 64)
    print("REALITY — name the sector")
    print("=" * 64)
    print()
    print("A law is turning somewhere out of sight. You get exactly 4 looks")
    print("at it — not 3, not 5. A Mobius law has 3 degrees of freedom, so")
    print("below 4 observations, more than one sector is still consistent")
    print("with everything you've seen. That's not this game being stingy —")
    print("it's exact. (darmiyan-fs/instants.py, self-referential-seed)")
    print()
    print(f"seed: {seed}")
    print()

    readings = []
    for i in range(4):
        readings.append(Reading(step=i, value=x))
        print(f"  look {i + 1}/4:  x = {x:.6f}")
        x = law.step(x)
    print()

    print("Three possible sectors:")
    for s, hint in SECTOR_HINT.items():
        print(f"  {s:12s} {hint}")
    print()

    guess = input("Name the sector: ").strip().lower()
    truth = law.sector()
    correct = guess == truth

    print()
    print("-" * 64)
    print(f"  the law was:   a={law.a:.4f} b={law.b:.4f} c={law.c:.4f} d={law.d:.4f}")
    print(f"  Delta:         {law.delta:.6f}")
    print(f"  true sector:   {truth}  ({SECTOR_HINT[truth]})")
    print(f"  your guess:    {guess}  {'-> correct' if correct else '-> wrong'}")
    print("-" * 64)

    if args.save:
        transcript = {
            "seed": seed,
            "law": {"a": law.a, "b": law.b, "c": law.c, "d": law.d},
            "readings": [{"step": r.step, "value": r.value, "source": r.source} for r in readings],
            "claimed_sector": guess,
            "true_sector": truth,
        }
        with open(args.save, "w") as f:
            json.dump(transcript, f, indent=2)
        print(f"\n  transcript saved: {args.save}")
        print("  verify it yourself: reality verify " + args.save)

    return 0 if correct else 1


def cmd_verify(args: argparse.Namespace) -> int:
    with open(args.transcript) as f:
        data = json.load(f)

    law = Law(**data["law"])
    readings = [Reading(**r) for r in data["readings"]]

    local_ok = v_local(law, readings)
    true_sector = law.sector()
    claimed_sector = data.get("claimed_sector")

    print("=" * 64)
    print("REALITY — verify")
    print("=" * 64)
    print()
    print(f"  LOCAL check (do consecutive readings match the stated law?): "
          f"{'PASS' if local_ok else 'FAIL'}")
    print(f"  stated law's actual sector:   {true_sector}")
    if claimed_sector is not None:
        match = claimed_sector == true_sector
        print(f"  claimed sector in transcript: {claimed_sector}  "
              f"({'matches' if match else 'does NOT match'})")
    print()

    if not local_ok:
        print("  This transcript's own readings don't satisfy its own stated")
        print("  law. Either the law was misreported or a reading was forged.")
        return 1

    print("  Readings are internally consistent with the stated law.")
    print()
    print("  Caveat, straight from darmiyan-fs/chain/verify.py: this checks")
    print("  that the transition is LAWFUL. It cannot tell you this is the")
    print("  one true history — a valid run from a different seed in the")
    print("  same class passes identically. Verification here means")
    print("  'internally consistent,' not 'the only possible truth.'")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="reality", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_play = sub.add_parser("play", help="guess the law's sector in 4 looks")
    p_play.add_argument("--seed", type=int, default=None, help="reproducible/shareable puzzle")
    p_play.add_argument("--save", metavar="FILE", default=None,
                         help="save a transcript, verifiable with 'reality verify'")
    p_play.set_defaults(func=cmd_play)

    p_verify = sub.add_parser("verify", help="check a saved transcript")
    p_verify.add_argument("transcript", help="path to a transcript JSON file")
    p_verify.set_defaults(func=cmd_verify)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
