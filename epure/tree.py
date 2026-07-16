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

import quern.grounding  # noqa: F401 -- the grounding natives, for the ledger's own gate rules
from quern import Quern, Node
from quern.library import consume
from quern.provenance import Quantity

_ROOT = Path(__file__).resolve().parents[1]


def build() -> Quern:
    lib, refs = consume(_ROOT, os.environ.get("QUERN_REGISTRY", _ROOT.parent / "quern-registry"))
    quern = Quern(packages=[next(r for r in refs if r.name == "ledger")])
    quern = lib.effective(quern)
    quern.root.children = [_NAME, _TWO_OBLIGATIONS, _NATIVES_FIRST, _OBSERVATION_CHILD,
                           _EXPLICIT_STATE_SUFFICES, _TEMPORAL_DEBT, _PUBLISH, _GATE,
                           _ONE_EVALUATOR, _PRE_STATE, _OUT_OF_DOMAIN, _FAIRNESS_DEBT,
                           _TOP_LEVEL_SPANS]
    return quern


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


_OBSERVATION_CHILD = Node(
    id="observability-is-a-child-node",
    kind="decision",
    name="An action's observability is an `observation` child node, referencing its "
         "event-kind by id",
    payload={
        "rationale":
            "The rule that needs it — an-action-is-observable — is written in the rule "
            "grammar, and the grammar reaches children (nodes(kind, self)) and never "
            "arbitrary links: the only link readers it has are the reserved structural "
            "verbs. A requirement the enforcing rule cannot see is decoration, so the "
            "witness relation is a child node the rule can count. The child references its "
            "event-kind by id, not by path: link targets are absolute tree paths, and a "
            "model subtree that moved would silently break its own internal references. An "
            "id resolves within the enclosing model wherever it is mounted.",
        "consequence":
            "Presence is the grammar's check; resolution is not. A dangling event id — an "
            "observation naming an event-kind the model does not declare — passes the "
            "package rule and is the conformance natives' catch, where full traversal "
            "exists. The split is deliberate: each layer refuses what it can actually see.",
    },
    children=[
        Node(id="alt-observed-as-link", kind="alternative",
             name="A domain link `observed-as` from the action to its event-kind",
             payload={"why":
                      "The natural shape, and unreachable: no rule builtin reads arbitrary "
                      "links, so the observability rule could not be written in the language "
                      "that must enforce it. Growing the grammar a links() reader to serve "
                      "one package inverts the doctrine that the grammar never grows toward "
                      "a domain — if a structural links reader ever earns its place, it will "
                      "be because several vocabularies needed it, and this decision is "
                      "superseded then, not bent now."}),
        Node(id="alt-reuse-verb", kind="alternative",
             name="Overload the reserved `uses` verb: action uses -> event-kind",
             payload={"why":
                      "Reachable today — uses() is in the grammar — and a misuse: `uses` "
                      "means resolves-through (params and kind read through the definition, "
                      "and explode() grafts the definition's children beneath the usage), so "
                      "every action would inherit its event-kind's licenses as phantom "
                      "children in every expansion. Reachability is not license to bend a "
                      "reserved verb's meaning."}),
    ],
)


_TEMPORAL_DEBT = Node(
    id="temporal-predicates-are-inexpressible",
    kind="debt",
    name="semantic-model@0.1.0 has one predicate kind — the state invariant; liveness and "
         "ordering claims have no vocabulary",
    params={
        # Ungrounded by construction: the number states what 0.1.0 can express, and nobody
        # competent has established that one kind is enough — the explicit-state hypothesis
        # below carries the falsification that would settle it.
        "predicate_kinds": Quantity(
            value=1, unit="kind", provenance="asserted", grounded=False,
            source="invariant is the only predicate kind in semantic-model@0.1.0; "
                   "eventually/until/leads-to cannot be written down"),
    },
    payload={
        "note":
            "Deliberate, not forgotten. The same trigger is recorded twice on purpose, in "
            "two substrates of record: the explicit-state hypothesis says the CHECKER "
            "suffices until a liveness predicate arrives, and this debt says the VOCABULARY "
            "cannot even carry one. The first liveness claim a domain genuinely needs kills "
            "the hypothesis and discharges this debt in the same act.",
    },
    children=[
        Node(id="a-temporal-kind-ships", kind="discharge",
             payload={
                 "condition":
                     "A later semantic-model version publishes a temporal predicate kind "
                     "behind the unchanged model/prove contract — authored when the first "
                     "domain predicate genuinely needs it, not before. Whoever does that "
                     "work grounds the param above with what the new version expresses.",
             }),
    ],
)


_PUBLISH = Node(
    id="publish-semantic-model-0-1-0",
    kind="decision",
    name="Publish semantic-model@0.1.0 before any machinery exists to evaluate it",
    payload={
        "rationale":
            "The vocabulary is the contract everything downstream is built against: the "
            "importer, the prover and the conformance natives should be written against a "
            "pinned digest, not a Python constant that can drift under them in the same "
            "repo. Publishing first costs one command and the proof gate; publishing after "
            "the machinery means the machinery was built against a moving target and nobody "
            "can say which meaning it was tested under.",
        "note":
            "The package carries exprs and evaluates nothing — no solvers travel in it. "
            "That is what makes publishing safe this early: there is no behavior to get "
            "wrong, only meaning, and meaning is exactly what the gate proves (every rule "
            "exercised by the turnstile example, every rule refuted by a counter-example "
            "staged alone).",
    },
    params={
        "rules": Quantity(
            value=3, unit="rule", provenance="verified", grounded=True,
            source="the registry publish gate: each rule exercised by the turnstile "
                   "example and refuted by its counter-example staged alone; the digest is "
                   "pinned in quern.lock and re-checked by tests/test_package.py"),
    },
    children=[
        Node(id="alt-author-in-repo-until-machinery", kind="alternative",
             name="Keep the vocabulary a Python constant here until the prover and "
                  "conformance natives exist, publish then",
             payload={"why":
                      "The machinery would be built against a file that drifts under it — "
                      "the exact pathology the registry channel dissolves. The channel's "
                      "argument was that the third consumer pins; here even the first "
                      "consumers, in this same repo, deserve a pinned meaning."}),
        Node(id="alt-fold-into-ledger-package", kind="alternative",
             name="Extend an existing package instead of rooting a new name",
             payload={"why":
                      "A semantic model is not a design ledger; cohabiting vocabularies "
                      "couple their release clocks, so refining one would wait on the "
                      "other. One package, one subject, its own version line."}),
    ],
)


_GATE = Node(
    id="publication",
    kind="gate",
    name="What leaves this repo as a pinned, citable claim",
    links={"admits": ["publish-semantic-model-0-1-0"]},
    payload={
        "note":
            "The gate this ledger deliberately did not plant while it had nothing to admit "
            "— a gate with no admits links is vacuously green, and green that guards "
            "nothing is decoration. It arrives with the first published claim, which is "
            "what it was waiting for: if an ungrounded param ever lands under an admitted "
            "node, nothing-unsound-passes-a-gate goes red and the check exits 1.",
    },
)


_ONE_EVALUATOR = Node(
    id="one-grammar-one-evaluator",
    kind="decision",
    name="model/prove evaluates guards, updates and invariants with quern's own evaluator, "
         "reached through its private surface at the pinned rev",
    payload={
        "rationale":
            "The exprs a model carries are declared to be in the quern rule grammar, and a "
            "grammar with two implementations is one text with two meanings — the checker's "
            "reading and the rule language's reading would drift, and a proof issued under "
            "the wrong reading is worse than no proof. quern exposes no public compile API, "
            "so the import is of `_tokenize`/`_parse_or` from the rev pyproject pins: a "
            "private surface, frozen by the pin, from a repo in the same estate.",
        "note":
            "If quern ever grows a public expr-compilation API, this import moves to it and "
            "the decision is superseded — the point is single evaluation semantics, not the "
            "underscore.",
    },
    children=[
        Node(id="alt-reimplement-the-grammar", kind="alternative",
             name="Re-implement the expr grammar inside epure",
             payload={"why":
                      "The drift machine itself: every future quern grammar fix would have "
                      "to be mirrored by hand, and the first missed mirror is a checker that "
                      "silently reads a guard differently than the rules that compose with "
                      "its verdicts."}),
        Node(id="alt-eval-via-run-rules", kind="alternative",
             name="Stage each expr as a throwaway rule and evaluate through run_rules",
             payload={"why":
                      "Public API, and wrong at both ends: a synthetic tree per state per "
                      "expr turns the walk's inner loop into tree construction, and the expr "
                      "environment (state variables, action args) would have to be smuggled "
                      "in as fake params — a contortion that obscures exactly the semantics "
                      "the checker exists to make plain."}),
    ],
)


_PRE_STATE = Node(
    id="updates-read-the-pre-state",
    kind="decision",
    name="An action's updates all read the pre-state and apply simultaneously",
    payload={
        "rationale":
            "Simultaneous assignment is the established semantics of every state-machine "
            "formalism a model here might one day compile to (TLA+'s primed variables, "
            "guarded commands), and it is the one an author can read off the page: each "
            "update expr means 'the next value, in terms of the state the action fired "
            "from', independent of the order the updates are written in.",
        "consequence":
            "A swap is two updates ({x: y, y: x}) with no temporary, and reordering a "
            "payload's update list can never change a model's meaning.",
    },
    children=[
        Node(id="alt-sequential-assignment", kind="alternative",
             name="Apply updates top to bottom, each seeing the previous one's writes",
             payload={"why":
                      "Makes the update list's ORDER load-bearing, invisibly: two models "
                      "differing only in payload ordering would have different behaviors, "
                      "and the difference survives every structural diff. Imperative "
                      "intuition bought at the price of the checker's whole claim to be "
                      "checking a mathematical object."}),
    ],
)


_OUT_OF_DOMAIN = Node(
    id="out-of-domain-is-a-refusal",
    kind="decision",
    name="An update that drives a variable outside its domain refuses the whole run — "
         "never an implicit guard, never a clamp",
    payload={
        "rationale":
            "A domain is the author's claim about what values a variable can hold, and a "
            "transition that breaks it means the model contradicts itself. Both silent "
            "readings are worse: an implicit guard quietly prunes exactly the behaviors the "
            "author most needs to know exist (the turnstile's 'coins < 3' guard is the "
            "author saying out loud what happens at the bound), and a clamp fabricates a "
            "state the updates never computed. The refusal names the action and binding, so "
            "the fix is one edit away.",
    },
    children=[
        Node(id="alt-implicit-guard", kind="alternative",
             name="Treat an out-of-domain successor as the action being disabled",
             payload={"why":
                      "TLA+'s own convention, and honest there because the type invariant "
                      "is stated and checked. Here it would make the domain bound a silent "
                      "extra conjunct of every guard — a proof could hold precisely because "
                      "the interesting transition was pruned, and nothing would say so."}),
        Node(id="alt-clamp", kind="alternative",
             name="Saturate at the domain edge",
             payload={"why":
                      "Fabricates a state no update computed and proves invariants over "
                      "the fabrication. A checker that invents states proves things about "
                      "its inventions."}),
    ],
)


_TOP_LEVEL_SPANS = Node(
    id="refinement-consumes-top-level-spans",
    kind="decision",
    name="model/refines consumes only a scenario's top-level spans; nested spans are the "
         "act's own decomposition, not further transitions",
    payload={
        "rationale":
            "A span tree is testimony at two granularities at once: the top level says WHAT "
            "semantic acts happened, the nesting says HOW each was carried out. The model's "
            "alphabet speaks at the first granularity — one action per act — so refinement "
            "reads exactly that level, and the decomposition stays what it is: evidence, "
            "held to its own licenses by model/licensed, span by span, at every depth.",
        "consequence":
            "An app may nest freely for auditability without every helper span needing an "
            "action of the model — instrumentation detail cannot force model growth. The "
            "cost: a genuine sub-transition mistakenly emitted as a nested span is invisible "
            "to refinement (its parent act testifies for both); it is still licensed, and "
            "totality still sees its raw events. Sessions refine as one continuous behavior "
            "— scenarios' top-level spans concatenated in tape order — because the calls of "
            "one recording ran against one accumulating state.",
    },
    children=[
        Node(id="alt-flatten-all-spans", kind="alternative",
             name="Refine over the flattening: every span at every depth is a transition",
             payload={"why":
                      "Forces the model to declare an action for every decomposition step "
                      "of every implementation — the model becomes a shadow of the code, "
                      "which is the exact inversion of the substrate's split: the code "
                      "refines the model, the model does not transcribe the code. And a "
                      "refactor that reshuffles helper spans would become a refinement "
                      "violation with no semantic change."}),
        Node(id="alt-explicit-depth-marker", kind="alternative",
             name="Let each span declare whether it is a transition or decomposition",
             payload={"why":
                      "A second channel for the instrumentation to lie through, and a "
                      "decision pushed to every call site forever. Structure already says "
                      "it: position IS the declaration."}),
    ],
)


_FAIRNESS_DEBT = Node(
    id="fairness-is-inexpressible",
    kind="debt",
    name="model/prove v0 has no fairness assumptions — and safety checking cannot miss them",
    params={
        # Ungrounded on purpose: nothing establishes that zero fairness vocabulary is
        # enough; the explicit-state hypothesis carries the falsification that would.
        "fairness_kinds": Quantity(
            value=0, unit="kind", provenance="asserted", grounded=False,
            source="no weak/strong fairness can be declared on an action; irrelevant to "
                   "safety verdicts, load-bearing the day a liveness predicate arrives"),
    },
    payload={
        "note":
            "Fairness only matters to liveness — an unfair path can postpone progress "
            "forever but cannot reach a state a fair one could not — so v0's safety-only "
            "verdicts are complete without it. Recorded now because the day the temporal "
            "backend lands, a liveness claim proven WITHOUT fairness assumptions is "
            "usually vacuously false, and whoever builds it must find this waiting.",
    },
    children=[
        Node(id="fairness-ships-with-the-temporal-backend", kind="discharge",
             payload={
                 "condition":
                     "The temporal backend (the discharge of "
                     "temporal-predicates-are-inexpressible) ships fairness annotations "
                     "with its first liveness predicate, and grounds the param above with "
                     "what can then be declared.",
             }),
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
