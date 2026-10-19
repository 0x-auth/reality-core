# reality-core

The Mobius-dynamics engine behind [the Reality game](https://reality-game.consciousness-portal.workers.dev/)
and [darmiyan-fs](https://github.com/0x-auth/darmiyan-fs) — zero dependencies,
usable as a library, a terminal game, or a verifier.

A "law" is a Mobius transformation `x -> (a*x + b) / (c*x + d)`, classified by
the scale-invariant discriminant `Delta = trace^2 - 4*det`:

| Delta | sector | fate |
|---|---|---|
| `> 0` | hyperbolic ("boost") | settled — closes, has an arrow |
| `= 0` | parabolic ("null") | drifting — the seam |
| `< 0` | elliptic ("rotation") | unresolved — cycles or never repeats |

A Mobius law has exactly **3 degrees of freedom**, so it takes exactly **4**
observed states to pin one down with certainty — not a game-design choice,
an exact result (`darmiyan-fs/instants.py`, `self-referential-seed`).

## Install

```bash
pip install reality-core
```

## Play

```bash
reality play                  # a fresh puzzle
reality play --seed 42        # reproducible — share the seed, share the puzzle
reality play --save run.json  # save a transcript
```

You get exactly 4 looks at a hidden law, then name its sector:
`hyperbolic`, `parabolic`, or `elliptic`.

### A second law: `--law linear`

```bash
reality play --law linear
```

Same game, different hidden process: a sequence `x[n+2] = p*x[n+1] + q*x[n]`.
Its sector comes from `Delta = p^2 + 4q` with the same sign rule, and it also
takes exactly 4 looks: 2 unknowns, one equation per look after the first two.
With 3 looks, laws from all three sectors still fit (readings `1, 1, 0` fit
`p=1, q=-1` elliptic, `p=4, q=-4` parabolic and `p=-4, q=4` hyperbolic).

It isn't unrelated to the Mobius law: the ratio `x[n+1]/x[n]` evolves by the
Mobius law `r -> (p*r + q)/r`, which is why Delta and the sectors line up.
Fibonacci (`p = q = 1`) has Delta = 5, the same as the golden-ratio map.

## Verify, trust-free

```bash
reality verify run.json
```

Re-derives the result from the raw readings — no server, no trust required,
just the same math run again. This is the honest version of "provably fair":
it tells you whether the transcript is internally consistent, not that it's
the one true history (a valid run from a different seed in the same
conjugacy class passes identically — see `darmiyan-fs/chain/verify.py` for
why that limit is real and exact, not a missing feature).

## As a library

```python
from reality_core import Law, random_law, v_local, v_delta

law = Law(1, 1, 1, 0)       # x -> 1 + 1/x, the golden-ratio map
law.sector()                 # 'hyperbolic'
law.step(1.0)                 # 2.0
```

### Plugging in a law

Every law implements one contract (`reality_core/interface.py`, signatures
only). A `Recognizer` can:

| method | does |
|---|---|
| `random_law(rng, sector=None)` | draw a hidden law, optionally from one sector |
| `initial_state(rng)` | draw a starting state |
| `fit(readings)` | recover the law from exactly `looks` readings |
| `verify(claimed_law, readings)` | re-derive every step from the raw readings |
| `from_dict(d)` | load a law from a transcript |

```python
from reality_core import LAWS

rec = LAWS["linear"]
law = rec.fit(readings)       # recognition: the law, from 4 readings alone
rec.verify(law, readings)     # True — and False for any forged or missing reading
```

`verify` rejects transcripts with gaps in the step numbers or fewer than
`looks` readings. (The pairwise `v_local` from 0.1.0 is still there, but it
skips gaps instead of rejecting them, so don't use it to check a transcript.)

A new law is a new module with a law class and a recognizer, plus one line in
`LAWS` — nothing else changes.

## License

MIT — see [LICENSE](LICENSE).
