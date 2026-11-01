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

## The mirror layer: one state for any field

Any step that turns one thing into another and is sometimes wrong (reading
a page, summarising a chat, fitting a law, remembering) plugs in with three
functions. The core never looks inside it.

| method | does |
|---|---|
| `forward(x)` | the becoming: cause to effect |
| `mirror(y)` | the other side: effect back toward the cause |
| `compare(x, back)` | how far the round trip misses (0 = came back whole) |
| `view(x, y)` (optional) | how much an independent second view disagrees |

`Mirror(field)` runs the round trip, places the line between trusted and
review once from a few known-right examples (`calibrate`), and gives every
output one `State`, the event `z = t + i/t`:

| quantity | from t | reading |
|---|---|---|
| `z`, `z_mirror` | `t + i/t`, `t - i/t` | the event and its mirror view; `z² − z′² = 4i` always |
| `State.from_views(z, z′)` | `(z + z′)/2` | either view alone fits two causes; both fit one |
| `dt`, `dx` | `t + 1/t`, `t − 1/t` | `dt² − dx² = 4` always |
| `u`, `turn` | `ln|t|`, `arg t` | the clock: the moving part and the turning part |
| `observable()` | `|dx| < |dt|` | `|dt|² − |dx|² = 4 cos(2·turn)`, so the edge is the 45° line at every size |
| `sides()` | `t, −1/t, i/t, −it` | you, retro, twin, retro twin; speeds `v, −v, −1/v, 1/v` |
| `sector()` | multiplier `−1/t²` | of the rule `S → dx + 1/S` that rebuilds t from dx alone |

For an output, `|t| = line / residual` and `turn = 45° × view / view_line`.
It is **trusted** when `|t| > 1` and it is observable: a small miss puts it on
our side of the line, and a second view that disagrees past its own line
turns it over the edge.

The rebuilding rule is itself a law here: `State(t).law()` is
`Law(dx, 1, 1, 0)`, and for real t its Delta is exactly `dt²`. So the
sectors are the stages of the seed. Real t is **hyperbolic**, the rule
settles. `t = ±i` (where `dt = 0`) is **parabolic**, the seam. `|t| = 1`
otherwise is **elliptic**, the rule only turns.

```python
from reality_core import Mirror, CallableField, State

pair = Mirror(CallableField("ocr", forward=read, mirror=render, compare=image_distance))
pair.calibrate(anchors)              # [(image, right_text), ...], once
r = pair.route(image)                # r.y, r.residual, r.state, r.status
r.state.sides()["twin"]              # the same event seen from the unobservable side
```

### Fields that ship (zero dependencies)

| field | forward → mirror | what the tests show |
|---|---|---|
| `ExactField` | bytes → compressed → bytes | 200/200 come back whole |
| `MemoryField` | t → dx → rebuilt t | off `|t| = 1`: 150/150 trusted; on it: ≥145/150 sent to review |
| `LawField("mobius" / "linear")` | readings → fitted law → replayed readings | lawful runs miss < 10⁻⁶; a forged 6th reading is caught; with exactly 4 readings any transcript fits, so the 5th look is the mirror |
| `TextField(note_for)` | source → note → claims looked back up | a line-for-line port of the Memory Check tool: identical on its 96 test claims (and on 165 claims of formula-heavy text checked while building); changed numbers go to review |

Anything else, such as an OCR engine, a language model or a reading of a
person, plugs in through `CallableField`. On the OCR test from
`darmiyan-fs/protocol` (400 degraded lines, line set on 200, tested on 200):
the residual alone reviewed 26.5% and caught 86% of wrong reads. The full
state (residual as size, the two-view disagreement as turn) reviewed 34% and
caught 93%, with 97.0% of trusted outputs correct. At the same 34% review
budget the residual alone catches 91%. The difference, +1.7 points (95%
interval −5.5 to +9.8), is not significant, so the second view earns its
place as a shared way to describe outputs, not as extra accuracy.

### From the terminal

```bash
reality state 2               # z, dt, dx, the clock, the four sides, the rule's sector
reality state 0.6+0.8j
reality check source.md note.md   # every claim of the note looked back up; exit 1 if any need a person
```

## License

MIT — see [LICENSE](LICENSE).
