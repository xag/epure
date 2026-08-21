# epure

**What does it mean, and will it always hold.**

An *épure* is the stonecutter's full-scale working drawing. The mason does not cut the block and then wonder whether it fits: the geometry is settled on the drawing first, and the piece is cut to it and checked against it. That is the whole idea, and the trade had it four centuries before anyone wrote a model checker.

Here the drawing is a **semantic model** — a small, finite mathematical object: state variables, actions with guards and updates, invariants. The piece is a running program that **testifies**, on its own recording, which semantic acts it just performed — the recording being a [flight-recorder](https://github.com/xag/flight-recorder) *tape*: one file per request logging every database answer, HTTP response, clock read and random draw, with the app's named acts written in-stream above those raw events. Verification then splits into two obligations, and the point of the split is that they are not the same kind of thing at all:

| | obligation | how it is discharged | when |
|---|---|---|---|
| 1 | **model ⊨ predicates** | proven, exhaustively, over every behavior the model admits | once, at design time |
| 2 | **code ⊑ model** | never provable — so checked mechanically, against evidence | on every execution |

The first is real proof, and it is cheap because the model is small. The second can never be proved — the code talks to a database, a clock and a network — so it is *checked*, on every tape, four ways:

- **refinement** — the semantic trace is a legal path of the model. If it is not, the tape names the first illegal step.
- **licensing** — each semantic claim is justified by the raw boundary events inside its span. Testimony, anchored to evidence: a program may not claim it charged a card unless the tape shows it calling the thing that charges cards.
- **totality** — no raw event escapes semantics. Behavior nobody modelled goes red rather than passing unnoticed, because unmodelled behavior is exactly where the bugs are.
- **conduct** — the behavior laws of the cited sources (Hughes 2020, RFC 9110, Lamport), held by value: the store is read back, projected onto the model's variables, and compared with what the model's own updates compute after every act — so a tape judges the model as much as the model judges the tape. A state variable the app only recomputes (a view) projects from the point where the app states it.

What that buys is a decomposition. A predicate violation in the wild is impossible without a refinement violation first, so a red result always answers *which of the two things is wrong*: the model was wrong (fix it, re-prove it) or the code diverged from it (the tape names the step). A failure that decomposes is a failure someone can act on.

**And the caveat, which is not buried:** proof relocates risk into specification. It does not remove it. A system can perfectly refine a proven model that is *wrong about what its users need*, and no amount of green here will notice. What proof cannot reach — comprehension, confusion, tone, the real world — is not this substrate's job and never will be.

## The state of it

Today this repo holds its own design ledger, its boundary declaration, **`semantic-model@`** — the meta-vocabulary a model is written in (fifteen kinds: `model`, `state-var` with its projection or derived view, `event-kind`, `license`, `action`, `observation`, the effects `creates`/`mutates`/`deletes`/`merges`, `touches`, `validator`, `boundary`, `invariant`, `promise`) — and **`conduct@`**, the catalogue of behavior laws with its census of the sources, both published to the registry through the proof gate and pinned here by digest (`epure/package.py` and `epure/conduct.py` are the authored sources; the pin, not the file, is the meaning). The substrate, in the order it was built:

| | |
|---|---|
| tape importer | a semantic tape becomes a tree the rule language can ask questions of |
| conformance natives | `model/licensed`, `model/total`, `model/refines` — counts, `== 0` in an ordinary rule |
| `model/prove` | exhaustive explicit-state checking of finite models; proofs as artifacts |
| conduct natives | eighteen, in `epure.behavior` (and `model/promised` in `epure.reach`): by presence — `conduct/effect`, `faithful`, `frame`, `refusal` on a tape, `checkable` on a model; by value, over the projections a state-var declares — `agrees` (Hoare's diagram per act; each red names its culprit — model, app, harness, or unnamed — from four facts the native holds, and `python -m epure.attribution claims.jsonl` counts, from the diagnosis claims, the reds a session met against the reds the rule named right), the two-stretch laws `twice`, `last-write`, `commute`, `undo`, `durable`, `same-story`, `constructible`, and `merge`, `stamped`, `conditional`, `doors`, `eventually` over the `merges` effect, the `validator` kind, the `boundary` and the `promise` — the behavior laws of `conduct@` held against what the real system wrote and read back, through the doors (`via`, `shown_by`) an action declares; every family the census covers has a native, and the one item no native holds (weak fairness) is a named debt |
| `epure.testimony` | one table per app, beside its `span()` call sites, naming what each act does to the store; the model generates its effect nodes from it and the app's tests hold every emission literal to it — so the drawing and the code cannot say two things about one act |
| `epure.census` | every property the cited sources state (Hughes 2020, RFC 9110), each mapped to a law and given one status — covered, weakened, owed, aside — with the counts computed over the items; shipped as conduct@'s example, mounted in the ledger, and the number the brief shows |
| `epure.survey` | drafts, per tool, the doors its tapes show it writing — generalized patterns, split into the tool's own writes and its spans' — so declaring ninety tools is a reading job, and the frame law convicts the first tape that takes a path the draft never saw |
| coverage | the vocabulary side, per app, first line of every conformance report and in the receipt: state-vars projected, actions with effects and boundaries, validators, tools the model names over tools the app registers. The laws bind by kind and grow on their own; this is the side that grows by hand, and the number that bounds what any law can see |

```bash
uv run python -m epure.check     # this repo's own design ledger. Exit 1 while any rule is red.
uv run pytest                    # the tests
```

## Day one, both of them

Two practices are set up at inception here, not retrofitted once something hurts — retrofitting is how a project ends up debugging by guesswork with no tape to replay and no record of why the thing was built the way it was.

**The ledger** (`epure/tree.py`) is this repo's design record as *data*, pinning `ledger@0.1.0` from the registry rather than re-authoring it. A decision that names no rejected alternative is red. A belief carrying no observation that would kill it is red. `epure.check` exits 1 while anything is red, and no red node can be discharged by editing the ledger — only by doing the work it names. A README can state a caveat perfectly and go on being true while the thing it warned about ships. **Prose does not fire.**

**The boundary** (`epure/boundary.py`) declares this repo's own nondeterminism, thin as it currently is: publishing to a registry, reading packages back out of one, and reading tapes off the disk. Every tape read goes through one function (`epure.tape.read_tape`) so that the declaration is true by construction rather than by diligence. It is declared now, while it is three lines, because a boundary retrofitted after the IO has spread is an archaeology exercise.

## What this depends on

[`quern`](https://github.com/xag/quern) (rules and vocabulary kept as data, published as versioned packages that must demonstrate themselves) and [`flight-recorder`](https://github.com/xag/flight-recorder) (the tape, and its frozen shape). Both pinned by rev, always — a repo whose whole subject is that meanings do not drift does not resolve its own dependencies by range.

A plain `import epure` pulls in no domain: no vocabulary registered, no natives installed, nothing read. The doors are the submodules, and each costs only what the caller asked for.

And it knows nothing else. Not who uses it, not what they use it for — a substrate that names its consumers has inverted the dependency it depends on. `tools/open_ready.py` checks that on every commit, and it checks it with an allowlist, since a list of the projects we may not mention would be a list of our consumers sitting in our own source.

---

Apache-2.0. © 2026 Xavier Grehant.
