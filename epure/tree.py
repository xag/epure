"""This repo's own design ledger — the decisions that founded it, as data a rule can go red on.

Not a changelog and not a README section: a README states a caveat and then cannot notice when
the caveat is violated. Here a decision that names no rejected alternative is red, and a belief
carrying no observation that would kill it is red, and `epure.check` exits 1 while either is —
so the record cannot quietly rot into decoration.

The vocabulary is `ledger@0.1.0`, pinned from the registry like anything else. It is not
re-authored here. Two projects already re-authored it before it was a package, which is the
whole argument for the registry channel: the third one pins.
"""

from __future__ import annotations

import os
from pathlib import Path

import bom.grounding  # noqa: F401 -- the grounding natives, for the ledger's own gate rules
from bom import Bom, Node
from bom.library import consume

_ROOT = Path(__file__).resolve().parents[1]


def build() -> Bom:
    lib, refs = consume(_ROOT, os.environ.get("BOM_REGISTRY", _ROOT.parent / "bom-registry"))
    bom = Bom(packages=[next(r for r in refs if r.name == "ledger")])
    bom = lib.effective(bom)
    bom.root.children = [_NAME, _TWO_OBLIGATIONS, _NATIVES_FIRST, _EXPLICIT_STATE_SUFFICES]
    return bom


# There is deliberately no `gate` node yet. A gate with no `admits` links is vacuously green,
# and a green gate is worth exactly what its links are worth — so planting one now would buy a
# reassuring line of output and nothing else. The first thing this repo will ask a gate to
# admit is a published claim (`semantic-model@0.1.0`, then a proof artifact), and the gate
# arrives with the thing it guards.


_NAME = Node(
    id="the-name-is-the-drawing",
    kind="decision",
    name="Call it epure: the drawing the piece is proven against before anything is cut",
    payload={
        "rationale":
            "An epure is the stonecutter's full-scale working drawing. The mason does not cut "
            "the stone and then ask whether it fits: the geometry is settled on the drawing, "
            "exhaustively, and the piece is then cut to it and checked against it. That is "
            "exactly the two obligations this substrate splits verification into, and the "
            "trade had a word for it four centuries before anyone wrote a model checker.",
        "note":
            "The estate's own adoption risk is a steep on-ramp of coined vocabulary, so this "
            "is a coinage that has to earn itself: the README explains the word once, in "
            "plain language, and the substrate is usable by someone who never reads the "
            "etymology. A name is allowed to be evocative. It is not allowed to be a "
            "prerequisite.",
    },
    children=[
        Node(id="alt-call-it-model", kind="alternative",
             name="Call it `model` — the plain word for the thing",
             payload={"why":
                      "Every stack in the world already has six `model`s (an ORM row, a "
                      "trained net, an MVC layer), and a package called `model` sitting in a "
                      "registry next to `semantic-model` is noise, not clarity. A name that "
                      "collides is worse than one that must be learned once."}),
        Node(id="alt-call-it-proof", kind="alternative",
             name="Call it `proof` — lead with the strongest claim",
             payload={"why":
                      "It claims the whole ground and delivers half of it. Proof is one of the "
                      "two obligations; the other is refinement, which is never proved and is "
                      "checked on every run precisely because it cannot be. A name that "
                      "promises more than the thing does is a name that will be quoted back "
                      "at us the first time a proven model turns out to be wrong about the "
                      "world -- which it will be, and which the substrate says out loud."}),
    ],
)


_TWO_OBLIGATIONS = Node(
    id="verification-splits-in-two",
    kind="decision",
    name="Two obligations of different character: prove model |= predicates, check code <= model",
    payload={
        "rationale":
            "A predicate over a small finite model can be settled once, exhaustively, over "
            "every behavior the model admits -- that is proof, and it costs a design-time "
            "run. Whether the *code* does what the model says can never be proved: the code "
            "talks to a database, a clock and a network. So the two are not two flavours of "
            "the same activity and must not share a mechanism. The first is discharged by a "
            "checker. The second is discharged on every execution, by confronting the "
            "semantic trace the code testified to with the model it claims to implement.",
        "consequence":
            "A predicate violation in the wild becomes impossible without a refinement "
            "violation first, so every failure decomposes mechanically: either the model was "
            "wrong (fix it, re-prove) or the code diverged from it (the tape names the first "
            "illegal step). That decomposition is the whole return on the split, and it is "
            "what makes a red result actionable instead of merely alarming.",
        "note":
            "Standing caveat, kept in view everywhere and not softened: proof relocates risk "
            "into specification; it does not remove it. A system can perfectly refine a "
            "proven model that is wrong about what its users need. Confronting the model with "
            "the world is a consumer's discipline and out of scope here -- this substrate "
            "guarantees only that whatever the model promises, the model keeps.",
    },
    children=[
        Node(id="alt-just-test-the-predicates", kind="alternative",
             name="One obligation: assert the predicates directly against running executions",
             payload={"why":
                      "This is what the estate does today, and it is the cost being removed. "
                      "An assertion over executions samples the behaviors that happened to "
                      "occur; it says nothing about the ones that did not. It is also the "
                      "expensive half: every scenario re-runs the real thing and an agent "
                      "reads the result. Sampling is what we already have too much of."}),
        Node(id="alt-verify-the-implementation", kind="alternative",
             name="Prove the code itself -- deductive verification of the real program",
             payload={"why":
                      "The honest maximal answer, and unreachable for an application whose "
                      "behavior is mostly the answers a datastore and a clock gave it. "
                      "Refinement against testimony is the tractable shape of the same "
                      "question: it does not prove the code, it makes the code's own claims "
                      "about itself mechanically refutable, on every run, against evidence."}),
    ],
)


_NATIVES_FIRST = Node(
    id="natives-first-wasm-later",
    kind="decision",
    name="The v0 checkers are natives, not wasm solver blobs",
    payload={
        "rationale":
            "A native is an optimisation of content, never a semantics of its own: the solver "
            "contract is the stable surface, and whatever honours the contract may serve it. "
            "So the choice of engine is reversible by construction, which is what makes "
            "taking the easy one now safe. The checkers must walk a model's closure and read "
            "a tape from the filesystem; the sandbox ABI cannot hold that today, and building "
            "for it first would buy portability nobody has asked for at the price of the "
            "thing actually being written.",
        "note":
            "Reversible, and the reversal is a fact about the contract, not a promise in a "
            "README: if a native ever disagrees with the contract it implements, the native "
            "is the bug.",
    },
    children=[
        Node(id="alt-wasm-blobs-now", kind="alternative",
             name="Ship the checkers as wasm blobs inside the package, from the start",
             payload={"why":
                      "The honest end state -- a package whose checks travel with its meaning "
                      "needs no installed Python at all -- and deferred, not rejected. Today "
                      "the checkers need filesystem reads and a graph walk over a package "
                      "closure, which the sandbox ABI does not offer. Revisit when it does."}),
        Node(id="alt-external-cli", kind="alternative",
             name="A separate command-line checker the rules shell out to",
             payload={"why":
                      "It puts the check outside the rule language, and a check outside the "
                      "rule language cannot be composed into a gate. The entire point is that "
                      "an unproven claim is refused by `ledger@`'s existing gate rule with no "
                      "new machinery -- which requires the check to be a `solve()` call like "
                      "any other."}),
    ],
)


_EXPLICIT_STATE_SUFFICES = Node(
    id="explicit-state-checking-suffices",
    kind="hypothesis",
    name="An explicit-state checker over finite models suffices for the first real domain's safety predicates",
    payload={
        "held_because":
            "The predicates a domain actually cares about tend to be safety properties over "
            "small, finite state -- nothing is ever double-counted, a turn cannot be done "
            "twice, the wall is never violated -- and those are decided by enumerating the "
            "reachable states of a model small enough to fit in memory. The bet is that the "
            "first real domain never reaches past that, and the bet is worth making because "
            "the alternative (a TLA+/Apalache backend behind the same contract) costs an "
            "order of magnitude more to build and would be built on guesses about which "
            "predicates matter.",
        "consequence_if_wrong":
            "Not a rewrite: `model/prove` is a solver contract, and a compile-to-TLA+ backend "
            "swaps in behind the same `solve()` call. The cost of being wrong is bounded by "
            "design, which is the only reason it is honest to hold the belief at all.",
    },
    children=[
        Node(
            id="a-predicate-needs-unbounded-state-or-liveness",
            kind="falsification",
            name="The first predicate that needs unbounded state or a liveness property",
            payload={
                "claim":
                    "One predicate the domain genuinely needs, which an explicit-state walk "
                    "over a finite model cannot decide -- an unbounded state variable, or a "
                    "liveness claim (`eventually`, `always eventually`) rather than a safety "
                    "claim -- kills this. Not 'is awkward to express': cannot decide.",
                "cadence": "on-authoring",
                "discharge_route":
                    "Compile to TLA+/Apalache behind the unchanged `model/prove` contract. "
                    "The hypothesis dying is a backend swap, and it is recorded here so that "
                    "when it dies nobody argues about whether it was ever believed.",
            },
        ),
    ],
)
