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

## License

MIT — see [LICENSE](LICENSE).
