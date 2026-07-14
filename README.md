# epure

**What does it mean, and will it always hold.**

An *épure* is the stonecutter's full-scale working drawing. The mason does not cut the block
and then wonder whether it fits: the geometry is settled on the drawing first, and the piece
is cut to it and checked against it. That is the whole idea, and the trade had it four
centuries before anyone wrote a model checker.

Here the drawing is a **semantic model** — a small, finite mathematical object: state
variables, actions with guards and updates, invariants. The piece is a running program that
**testifies**, on its own recording, which semantic acts it just performed. Verification then
splits into two obligations, and the point of the split is that they are not the same kind of
thing at all:

| | obligation | how it is discharged | when |
|---|---|---|---|
| 1 | **model ⊨ predicates** | proven, exhaustively, over every behavior the model admits | once, at design time |
| 2 | **code ⊑ model** | never provable — so checked mechanically, against evidence | on every execution |

The first is real proof, and it is cheap because the model is small. The second can never be
proved — the code talks to a database, a clock and a network — so it is *checked*, on every
tape, three ways:

- **refinement** — the semantic trace is a legal path of the model. If it is not, the tape
  names the first illegal step.
- **licensing** — each semantic claim is justified by the raw boundary events inside its span.
  Testimony, anchored to evidence: a program may not claim it charged a card unless the tape
  shows it calling the thing that charges cards.
- **totality** — no raw event escapes semantics. Behavior nobody modelled goes red rather than
  passing unnoticed, because unmodelled behavior is exactly where the bugs are.

What that buys is a decomposition. A predicate violation in the wild is impossible without a
refinement violation first, so a red result always answers *which of the two things is wrong*:
the model was wrong (fix it, re-prove it) or the code diverged from it (the tape names the
step). A failure that decomposes is a failure someone can act on.

**And the caveat, which is not buried:** proof relocates risk into specification. It does not
remove it. A system can perfectly refine a proven model that is *wrong about what its users
need*, and no amount of green here will notice. What proof cannot reach — comprehension,
confusion, tone, the real world — is not this substrate's job and never will be.

## The state of it

Early. Today this repo holds its own design ledger, its boundary declaration, and nothing
else; the substrate itself is being built in the open, in this order:

| | |
|---|---|
| `semantic-model@0.1.0` | the meta-vocabulary a model is written in: `model`, `state-var`, `event-kind`, `license`, `action`, `invariant` |
| tape importer | a semantic tape becomes a tree the rule language can ask questions of |
| conformance natives | `model/licensed`, `model/total`, `model/refines` — counts, `== 0` in an ordinary rule |
| `model/prove` | exhaustive explicit-state checking of finite models; proofs as artifacts |

```bash
uv run python -m epure.check     # this repo's own design ledger. Exit 1 while any rule is red.
uv run pytest                    # the tests
```

## Day one, both of them

Two practices are set up at inception here, not retrofitted once something hurts — retrofitting
is how a project ends up debugging by guesswork with no tape to replay and no record of why the
thing was built the way it was.

**The ledger** (`epure/tree.py`) is this repo's design record as *data*, pinning `ledger@0.1.0`
from the registry rather than re-authoring it. A decision that names no rejected alternative is
red. A belief carrying no observation that would kill it is red. `epure.check` exits 1 while
anything is red, and no red node can be discharged by editing the ledger — only by doing the
work it names. A README can state a caveat perfectly and go on being true while the thing it
warned about ships. **Prose does not fire.**

**The boundary** (`epure/boundary.py`) declares this repo's own nondeterminism, thin as it
currently is: publishing to a registry, reading packages back out of one, and reading tapes off
the disk. Every tape read goes through one function (`epure.tape.read_tape`) so that the
declaration is true by construction rather than by diligence. It is declared now, while it is
three lines, because a boundary retrofitted after the IO has spread is an archaeology exercise.

## What this depends on

`bom` (the substrate: meaning is data, rules are data, and a package must demonstrate itself
to be published) and `flight-recorder` (the tape, and its frozen shape). Both pinned by rev,
always — a repo whose whole subject is that meanings do not drift does not resolve its own
dependencies by range.

A plain `import epure` pulls in no domain: no vocabulary registered, no natives installed,
nothing read. The doors are the submodules, and each costs only what the caller asked for.
