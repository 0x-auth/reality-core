"""
reality — a terminal game and verifier built on reality_core.

    reality play [--law mobius|linear] [--seed N]   guess the law's sector in exactly 4 looks
    reality verify <transcript>                     check a transcript against its claimed law
"""

import argparse
import json
import random
import sys

from . import LAWS, Reading

SECTOR_HINT = {
    "hyperbolic": "settled — it closes, it has an arrow",
    "parabolic": "drifting — the seam, the borderline case",
    "elliptic": "unresolved — it cycles, or never repeats",
}

INTRO = {
    "mobius": [
        "A law is turning somewhere out of sight. You get exactly 4 looks",
        "at it — not 3, not 5. A Mobius law has 3 degrees of freedom, so",
        "below 4 observations, more than one sector is still consistent",
        "with everything you've seen. That's not this game being stingy —",
        "it's exact. (darmiyan-fs/instants.py, self-referential-seed)",
    ],
    "linear": [
        "A sequence is unfolding by a hidden rule x[n+2] = p*x[n+1] + q*x[n].",
        "You get exactly 4 looks. The rule has 2 unknowns and each look",
        "after the first two gives one equation, so with 3 looks a whole",
        "line of rules — spanning all three sectors — still fits. 4 is exact.",
    ],
}


def cmd_play(args: argparse.Namespace) -> int:
    rec = LAWS[args.law]
    seed = args.seed if args.seed is not None else random.randrange(1_000_000)
    rng = random.Random(seed)
    law = rec.random_law(rng)
    state = rec.initial_state(rng)

    print("=" * 64)
    print("REALITY — name the sector")
    print("=" * 64)
    print()
    for line in INTRO[rec.law_type]:
        print(line)
    print()
    print(f"seed: {seed}")
    print()

    readings = []
    for i in range(rec.looks):
        x = law.observe(state)
        readings.append(Reading(step=i, value=x))
        print(f"  look {i + 1}/{rec.looks}:  x = {x:.6f}")
        state = law.step(state)
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
    print("  the law was:   " + " ".join(f"{k}={v:.4f}" for k, v in law.to_dict().items()))
    print(f"  Delta:         {law.delta:.6f}")
    print(f"  true sector:   {truth}  ({SECTOR_HINT[truth]})")
    print(f"  your guess:    {guess}  {'-> correct' if correct else '-> wrong'}")
    print("-" * 64)

    if args.save:
        transcript = {
            "seed": seed,
            "law_type": rec.law_type,
            "law": law.to_dict(),
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

    law_type = data.get("law_type", "mobius")  # transcripts before 0.2.0 are all mobius
    rec = LAWS.get(law_type)
    if rec is None:
        print(f"unknown law_type: {law_type!r} (known: {', '.join(sorted(LAWS))})")
        return 2
    law = rec.from_dict(data["law"])
    readings = [Reading(**r) for r in data["readings"]]

    local_ok = rec.verify(law, readings)
    true_sector = law.sector()
    claimed_sector = data.get("claimed_sector")
    try:
        recognized = rec.fit(readings).sector()
    except ValueError:
        recognized = None

    print("=" * 64)
    print(f"REALITY — verify ({law_type})")
    print("=" * 64)
    print()
    print(f"  LOCAL check (do consecutive readings match the stated law?): "
          f"{'PASS' if local_ok else 'FAIL'}")
    print(f"  stated law's actual sector:   {true_sector}")
    print(f"  recognized from readings alone (stated law ignored): "
          f"{recognized or 'not determined'}")
    if claimed_sector is not None:
        match = claimed_sector == true_sector
        print(f"  claimed sector in transcript: {claimed_sector}  "
              f"({'matches' if match else 'does NOT match'})")
    print()

    if not local_ok:
        print("  This transcript's own readings don't satisfy its own stated law,")
        print(f"  or it lacks readings at steps 0..{rec.looks - 1}. Either the law was")
        print("  misreported or a reading was forged or dropped.")
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
    p_play.add_argument("--law", choices=sorted(LAWS), default="mobius",
                        help="which hidden process to play against (default: mobius)")
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
