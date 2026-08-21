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
import epure.behavior  # noqa: F401 -- conduct@'s contracts need their natives in-process
import epure.conformance  # noqa: F401 -- consume() re-gates the synced closure, and
import epure.reach  # noqa: F401 -- model/promised, the liveness half
import epure.prove  # noqa: F401 -- semantic-model@'s contracts need their natives in-process
from quern import Quern, Node
from quern.library import consume
from quern.provenance import Quantity

_ROOT = Path(__file__).resolve().parents[1]


def build() -> Quern:
    from .census import census
    from .conduct import CONDUCT_LAWS

    lib, refs = consume(_ROOT, os.environ.get("QUERN_REGISTRY", _ROOT.parent / "quern-registry"))
    quern = Quern(packages=[r for r in refs if r.name in ("ledger", "conduct")])
    quern = lib.effective(quern)
    quern.root.children = [_NAME, _DIST_NAME, _TWO_OBLIGATIONS, _NATIVES_FIRST,
                           _OBSERVATION_CHILD, _EXPLICIT_STATE_SUFFICES,
                           _ATTRIBUTION_HYPOTHESIS, _DRAFT_HYPOTHESIS, _DRAFT_ROUTING, _REACHABLE_GRID,
                           _BETWEEN_LOOKS_ONE_WAY,
                           _TEMPORAL_DEBT,
                           _PUBLISH, _GATE, _ONE_EVALUATOR, _PRE_STATE, _OUT_OF_DOMAIN,
                           _FAIRNESS_DEBT, _TOP_LEVEL_SPANS, _WIDER_GAZE, _DIRECTION_DEBT,
                           _INHERITANCE, _CONDUCT_PUBLISH, _DOORS, _CONDUCT_NATIVES,
                           _TWO_STRETCHES_DEBT, _CENSUS_DECISION, _PROJECTION_DEBT,
                           _DERIVED_DECISION,
                           _MERGE_DEBT, _VALIDATOR_DEBT, _GENERATED_DEBT, _DOOR_CENSUS_DEBT,
                           census(),
                           *CONDUCT_LAWS]
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


_DIST_NAME = Node(
    id="the-dist-name-is-epure-py",
    kind="decision",
    name="The PyPI dist name is epure-py, settled before any adopter asks: "
         "`pip install epure-py`, `import epure`",
    payload={
        "rationale":
            "PyPI's `epure` has been another project's name for years (62 releases; a "
            "real package, not a squatter, so the name will not fall to a reclaim). "
            "Dist name and import name are independent, so the drawing keeps its word "
            "where it matters — in the code — and the dist takes the opencv-python "
            "convention: base name plus language marker, zero cleverness to defend. "
            "Settled now, ahead of any pull, because a name chosen under adopter "
            "pressure is chosen badly and a free name does not stay free (the estate "
            "ledger's names-reserve-ahead-of-pull records the same call for the whole "
            "fleet).",
        "consequence":
            "The name is reserved on PyPI the day a credential exists; no dist ships "
            "until someone asks for one — today's consumers pin the repo by rev and "
            "lose nothing. The decision is the artifact here, not a release.",
    },
    children=[
        Node(id="alt-pyepure", kind="alternative",
             name="pyepure — the py-prefix register (pytest, pydantic)",
             payload={"why":
                      "Reads as its own project rather than as the distribution of "
                      "this one; the suffix form says plainly 'epure, for Python'."}),
        Node(id="alt-wait-for-an-adopter", kind="alternative",
             name="Leave the dist name open until an adopter asks for pip install",
             payload={"why":
                      "The name is the one part of a dist that cannot be produced on "
                      "demand without risk: free names get taken, and deciding costs "
                      "nothing today. Only the release waits for pull."}),
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
    name="semantic-model@0.1.0 had one predicate kind — the state invariant; liveness and "
         "ordering claims had no vocabulary. Discharged 2026-08-21: `promise` (when, then, "
         "unless, within), model/promised and conduct/eventually",
    params={
        # Ungrounded by construction: the number states what 0.1.0 can express, and nobody
        # competent has established that one kind is enough — the explicit-state hypothesis
        # below carries the falsification that would settle it.
        # Grounded by the discharge (2026-08-21): `promise` joins `invariant` - when/then/
        # unless/within is eventually, leads-to and until in one kind, proved possible by
        # model/promised and held on tapes by conduct/eventually.
        "predicate_kinds": Quantity(
            value=2, unit="kind", provenance="verified", grounded=True,
            source="semantic-model@0.10.0+: invariant (safety) and promise (liveness: when -> "
                   "eventually then, unless released, within a horizon); the cloakroom "
                   "promises a checked coat is reclaimed and a reclaim that demands a tag is "
                   "refuted as a trap (epure.spec PROMISED)"),
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
    links={"admits": ["publish-semantic-model-0-1-0", "publish-the-conduct-seam",
                      "conduct-owns-its-natives", "the-census-is-read-from-the-sources"]},
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
        "the_day_has_come":
            "2026-08-22: it has arrived and the annotation did not ship with it. "
            "[[temporal-predicates-are-inexpressible]] discharged on 2026-08-21 - `promise`, "
            "model/promised and conduct/eventually - and the discharge condition below asked "
            "for fairness beside the first liveness predicate. A promise is now held in two "
            "places, and only the model half is a claim about the program: `eventually` binds "
            "whoever acts on the tape, which in the first consumer is a household, and a "
            "flight there has already been rewritten so a person would hoover and the check "
            "would stay green. That is the vacuity this debt predicted, arriving from the "
            "other side - not a liveness claim proved for nothing, but a liveness claim that "
            "binds the wrong party and is kept true by writing obedient tapes.",
    },
    children=[
        Node(id="fairness-ships-with-the-temporal-backend", kind="discharge",
             payload={
                 "condition":
                     "The temporal backend (the discharge of "
                     "temporal-predicates-are-inexpressible) ships fairness annotations "
                     "with its first liveness predicate, and grounds the param above with "
                     "what can then be declared. OVERDUE since 2026-08-21: the backend "
                     "shipped without it, and a promise able to say `under weak fairness` is "
                     "what lets a tape half bind the program and release the people.",
             }),
    ],
)


_WIDER_GAZE = Node(
    id="a-wider-gaze-names-its-evidence",
    kind="decision",
    name="A license reaches beyond the claiming span's own window only by naming what it "
         "looks for: evidence(pattern, scope), never a bare count over an ancestor's window",
    payload={
        "rationale":
            "An emission's evidence is very often not inside it. A derived, instantaneous "
            "act — 'the pick was shown', 'a day ticked over' — encloses nothing by "
            "construction, and the read that justifies it happened in the act that produced "
            "it, one level up. Under the v0 own-window-only contract the licensable set was "
            "'testimony that did its own I/O', when the promise is 'testimony anchored to "
            "evidence'; sibling acts derived from one read competed for the one innermost "
            "span that owned it, and the winner was decided by nesting order, not evidence. "
            "But the invariant that made v0 draw the cut tight still binds: silence is a "
            "lie, and a license that licenses anything is the `true` expr with extra steps. "
            "So the widening is asymmetric: `ctx('events')` stays exactly v0 (the own "
            "window, where a bare count is an honest 'I did I/O'), and the only way to look "
            "wider is `evidence(pattern, 'enclosing')` — a named pattern over the claim's "
            "lineage (its own window plus every raw event a testimony ancestor directly "
            "encloses). Naming is what keeps the check alive at width: unrelated ancestor "
            "I/O matches no pattern, and a claim with no matching evidence anywhere along "
            "its lineage is still convicted. Scopes are monotone (enclosing contains own), "
            "so widening a license can never convict a claim the narrow scope acquits; "
            "structural nodes contribute nothing to any lineage — a raw event parked on a "
            "scenario is a totality violation, and behavior the model does not know exists "
            "must never license a claim.",
        "consequence":
            "Points need no special casing: a point's own window is empty and its license "
            "names its evidence one level up — the delegation is written in the license, "
            "where a reader can refute it, not wired into the checker. Naming also "
            "sharpens own-window licenses for free: a span wrapping the WRONG I/O is now "
            "convicted where a bare count acquitted it.",
    },
    children=[
        Node(id="alt-blanket-enclosing-scope", kind="alternative",
             name="Give ctx a scope argument: ctx('events', 'enclosing') sees the "
                  "ancestors' windows",
             payload={"why":
                      "Symmetric and simple, and it dissolves the check it widens: the "
                      "idiomatic license is a count, and a count over an ancestor's window "
                      "is satisfied by ANY unrelated I/O above the claim — every "
                      "unfalsifiable claim in the estate quietly goes green. The refusal "
                      "is enforced, not advised: ctx with a scope argument raises, and the "
                      "message names the road that is open."}),
        Node(id="alt-point-delegates", kind="alternative",
             name="A point's evidence IS its enclosing span's window, by definition of "
                  "being a point",
             payload={"why":
                      "The narrow fix, and implicit: the author never says where the "
                      "evidence lives, so the delegation cannot be refuted by reading the "
                      "model. It fixes only points (sibling SPANS derived from one read "
                      "still compete for it), and at top level it delegates to structure, "
                      "whose parked events are totality violations licensing claims."}),
        Node(id="alt-explicit-licensor", kind="alternative",
             name="An act declares which other claim licenses it, and the link is checked",
             payload={"why":
                      "A second channel for the instrumentation to lie through — 'I am "
                      "licensed by that span over there' is itself unlicensed testimony — "
                      "and a placement decision pushed to every call site forever. The "
                      "license already knows what evidence justifies the kind; making each "
                      "emission repeat it invites the copies to disagree."}),
    ],
)


_DIRECTION_DEBT = Node(
    id="license-direction-is-blind",
    kind="debt",
    name="A license was satisfied by evidence anywhere in scope — before or after the "
         "claim; no direction could be expressed. Discharged 2026-08-20: positions travel "
         "and evidence() takes a direction",
    params={
        # Ungrounded on purpose: nothing establishes that zero directional vocabulary is
        # enough — the first license that genuinely needs before/after grounds it or
        # discharges the debt.
        # Grounded by the discharge: positions travel on the import (2026-08-20, the
        # conduct natives needed them) and evidence() took its third argument the same day.
        "directions_expressible": Quantity(
            value=2, unit="direction", provenance="verified", grounded=True,
            source="evidence(pattern, scope, 'before' | 'after'); the turnstile's "
                   "passage-counted license says the sensor read came before the count, "
                   "and model/licensed convicts the point placed before the read "
                   "(epure.spec LICENSED)"),
    },
    payload={
        "note":
            "Decided out loud, not overlooked: the tape defines enclosure by order, but "
            "the span tree separates a node's own events from its children, so a point's "
            "position among its parent's raw events does not survive import — a "
            "directional license would be judged against an order the judged object no "
            "longer carries. Blind is honest; pretending to direction against lost "
            "interleaving would convict and acquit by accident.",
    },
    children=[
        Node(id="direction-ships-with-interleaving", kind="discharge",
             payload={
                 "condition":
                     "The importer preserves the interleaving of a span's own events and "
                     "its children (a positional index on both), and evidence() grows a "
                     "direction — built when the first consumer's license genuinely needs "
                     "before/after, not before. Whoever builds it grounds the param above "
                     "with what can then be declared.",
             }),
    ],
)


_INHERITANCE = Node(
    id="behavior-laws-bind-by-inheritance",
    kind="decision",
    name="A behavior law is written once against a generic effect kind; an action inherits "
         "it by declaring the effect — never by stamping a formula per operation",
    payload={
        "rationale":
            "The founder's fork, asked out loud: formulas with holes, or type inheritance? "
            "The substrate already resolves it. Rules bind by KIND, so making the effect a "
            "kind (semantic-model@0.4.0's creates/mutates/deletes/touches, children of "
            "action) makes every law of the family arrive on every declaring action with "
            "no per-operation authoring at all — the same way ledger@'s gate rule binds "
            "every domain's gates. The declaration is one honest line about what the "
            "operation does; the laws are the catalogue's, written once, citable once, "
            "versioned once.",
        "consequence":
            "N operations x M families costs N declarations + M laws, not N x M stamped "
            "formulas that drift apart at the first rewording. And an operation that "
            "declares nothing inherits nothing — the catalogue is opt-in by construction, "
            "which is why semantic-model 0.4.0 ships no new mandatory rule.",
    },
    children=[
        Node(id="alt-templates", kind="alternative",
             name="Formulas with holes: instantiate each family per operation at "
                  "generation time",
             payload={"why":
                      "N x M generated artifacts whose wording can drift independently, "
                      "and the binding lives in the generator's output rather than in the "
                      "data — a stamped rule survives its own retirement when the "
                      "operation's declaration changes. Templates survive in one place "
                      "only: the refuting examples the conformance natives will demand, "
                      "where each instance must fail alone."}),
        Node(id="alt-mandatory-in-semantic-model", kind="alternative",
             name="Make effect declaration a rule of semantic-model itself",
             payload={"why":
                      "Every existing model in the estate goes red the day the package is "
                      "repinned — the first consumer's model first — for a demand it never opted into. "
                      "The demand belongs to the conduct catalogue, adopted deliberately, "
                      "exactly as craft@'s laws are adopted by the apps they judge."}),
    ],
)


_CONDUCT_PUBLISH = Node(
    id="publish-the-conduct-seam",
    kind="decision",
    name="Publish semantic-model@0.4.0 (the effect kinds) and conduct@0.1.0 (the nine "
         "families) as two packages, laws-as-content in this repo",
    payload={
        "rationale":
            "The vocabulary and the catalogue have different clocks: effect kinds change "
            "when the model language grows, laws change when a family is sourced or a "
            "sighting lands. Two packages keep the release lines independent, and the "
            "catalogue names the exact vocabulary version its triggers bind to "
            "(requires semantic-model@0.4.0). The nine laws themselves stay repo content "
            "here — craft-laws' own shape — because five are honestly uncited and red "
            "under a-law-cites-a-source, and the publish gate demands examples pass: "
            "laundering them through the gate would mean either faking citations or "
            "dropping the debt, and the ledger's treatment of a debt is to carry it "
            "visibly.",
        "note":
            "conduct@'s law shape mirrors craft@'s five kinds by name and structure, "
            "re-authored rather than consumed: craft's `law` KindDef defines itself as a "
            "claim about interface or copy, and stretching a published kind's stated "
            "meaning to a second domain is the drift the registry exists to refuse. The "
            "day a third law domain arrives, the shape earns extraction into a package "
            "both supersede onto.",
    },
    params={
        "families": Quantity(
            value=9, unit="law", provenance="verified", grounded=True,
            source="len(CONDUCT_LAWS), asserted equal in tests/test_conduct.py; census "
                   "folded from Hughes 2020's five approaches onto what a tape can "
                   "witness — cited on the four laws a source states, carried red on "
                   "the five no source has been found for"),
        "effect_kinds": Quantity(
            value=4, unit="kind", provenance="verified", grounded=True,
            source="creates, mutates, deletes, touches — instantiated by the package's "
                   "own examples at publish (11 kinds instantiated, gate output, "
                   "digest f2623b8f9010)"),
    },
    children=[
        Node(id="alt-laws-as-package-examples", kind="alternative",
             name="Ship the nine laws inside conduct@ as examples",
             payload={"why":
                      "The gate demands examples pass every rule, and five families are "
                      "honestly red under a-law-cites-a-source. Shipping only the cited "
                      "four would split the catalogue; faking the five would launder a "
                      "debt. Content stays where red can be carried and accounted."}),
        Node(id="alt-one-package", kind="alternative",
             name="Fold the effect kinds and the laws into one package",
             payload={"why":
                      "Couples the clocks: sourcing one uncited family would republish "
                      "the model vocabulary, and every consumer of the kinds would repin "
                      "for a change that touches no kind. One package, one subject — the "
                      "same call the ledger already records for semantic-model itself."}),
    ],
)


_DOORS = Node(
    id="an-effect-binds-to-the-tape-through-doors",
    kind="decision",
    name="An effect declaration binds its abstract entity to the tape through two DOORS — "
         "`via`, the write that materializes it, and `shown_by`, the read that shows it back "
         "— each a name pattern over raw events, optionally narrowed by an argument",
    payload={
        "rationale":
            "The laws speak in the model's words (an entity is a state-var) and the tape "
            "speaks in the app's (a path, a field, a document). Something has to say how one "
            "is the other, and the cheapest honest thing is the cut a license already makes: "
            "name the act. `via` names the write inside the act; `shown_by` names the read "
            "after it; `touches.via` names every write the act may make. What the write "
            "carried (its container arguments) must then appear, as a structural subset, in "
            "what the read returned — Hughes's postcondition read literally, with no "
            "app-specific navigation in the checker. The same door shape narrows by argument "
            "(`where`) where a name alone would admit too much, which is exactly the cut "
            "the first consumer's licenses asked for and could not get.",
        "consequence":
            "The natives are generic and the binding is per action, as declarations — "
            "templates stay out of the laws. A door is a claim the model makes about the "
            "app's I/O surface and it can be wrong the way a license can be wrong: a door "
            "naming an event the app never emits convicts every act that declares it, which "
            "is the failure mode that surfaces instead of hiding. And a model with no store "
            "(the turnstile) declares no doors and is counted by conduct/checkable as "
            "unwitnessable rather than silently passing.",
    },
    children=[
        Node(id="alt-abstraction-function", kind="alternative",
             name="Declare per state-var how its value is read off the store (a refinement "
                  "mapping), then compare abstract pre/post states against reads",
             payload={"why":
                      "The right thing in a textbook and the wrong first thing here: it "
                      "needs an expression language that reaches into event payloads, "
                      "which the rule grammar deliberately does not have, and it would make "
                      "every model author write a projection for every variable before any "
                      "law could fire. The door asks for one name per effect. The mapping "
                      "can arrive later, behind the same contracts, if a law needs a value "
                      "rather than a presence."}),
        Node(id="alt-match-the-entity-name", kind="alternative",
             name="Search raw events for the entity's name",
             payload={"why":
                      "The entity is `held` and the tape says `hook`; the entity is "
                      "`wash_pending` and the tape says `done.c_wfNc7Q`. Text matching "
                      "would bind by accident and miss by design."}),
        Node(id="alt-witness-expr", kind="alternative",
             name="A `shown` expr per effect, evaluated like a license",
             payload={"why":
                      "A license answers 'is there evidence'; the effect law asks 'does the "
                      "read agree with the write', which is a relation between two events, "
                      "and the grammar counts events, it does not compare their payloads. "
                      "The comparison lives in the native, once, and the declaration names "
                      "the two events it relates."}),
    ],
)


_CONDUCT_NATIVES = Node(
    id="conduct-owns-its-natives",
    kind="decision",
    name="The conduct contracts (conduct/effect, faithful, frame, refusal, checkable) are "
         "declared by conduct@0.2.0; the door vocabulary they read is semantic-model@0.5.0's",
    payload={
        "rationale":
            "A law family's check belongs to the catalogue that states the family: the "
            "native IS the law held against a tape, so adopting conduct@ is what makes the "
            "check a demand, and a model that declares effects without adopting the "
            "catalogue owes nothing — the opt-in the seam decision promised. semantic-model "
            "changes too, because the declaration has to say where on the tape to look, and "
            "that is vocabulary; but it gains no contract and no rule, and its 0.5.0 is a "
            "payload addition every existing model accepts unchanged.",
        "consequence":
            "Two publishes, two clocks, as the seam decision drew them: a sharper check "
            "republishes conduct; a richer door shape republishes semantic-model. The natives "
            "live in epure.behavior, imported explicitly — a third door beside epure.prove and "
            "epure.conformance — so a process that wants only the model checks pays nothing "
            "for the laws.",
    },
    params={
        "natives": Quantity(
            value=5, unit="contract", provenance="verified", grounded=True,
            source="conduct@0.2.0 SOLVERS; 19 demonstrations registered beside the "
                   "implementation hold at publish (digest b51ebee9ef51), each family's "
                   "refuting tape red under its own native and green under the other three "
                   "(tests/test_behavior.py)"),
        "families_owed": Quantity(
            value=4, unit="law", provenance="verified", grounded=True,
            source="the laws whose payload carries `owed` rather than `native`: "
                   "twice-is-once, undo-restores, same-state-same-story, "
                   "shown-once-shown-until-touched — asserted equal in tests/test_conduct.py"),
    },
    children=[
        Node(id="alt-natives-in-semantic-model", kind="alternative",
             name="Declare the conduct contracts in semantic-model@0.5.0 beside model/*",
             payload={"why":
                      "Makes the laws' checks look like the vocabulary's own demand, which "
                      "the seam decision refused: effects are opt-in, and a model author who "
                      "never adopted conduct@ would find five contracts pinned under their "
                      "model. And it couples the clocks the seam decision separated."}),
        Node(id="alt-one-native-per-law", kind="alternative",
             name="One contract per family, nine names, four of them raising 'not yet'",
             payload={"why":
                      "A contract that refuses every input is a descriptor with no "
                      "demonstration that can hold, and the publish gate is right to refuse "
                      "it. A family the tape cannot witness is a debt on the law node, "
                      "where it is red-able, not a stub in the solver table."}),
    ],
)


_TWO_STRETCHES_DEBT = Node(
    id="four-families-compare-two-stretches",
    kind="debt",
    name="twice-is-once, undo-restores, same-state-same-story, "
         "shown-once-shown-until-touched, independent-writes-commute, last-write-wins, "
         "equivalent-worlds-stay-equivalent and every-world-is-constructible compare two "
         "stretches of one tape; no native did. Discharged 2026-08-20: seven natives over "
         "the projected world around two acts",
    params={
        # Grounded by the discharge: conduct@0.5.0 declares seven stretch-comparing
        # contracts, each demonstrated on the cloakroom with a tape that refutes it and one
        # that holds, the cross-matrix of implications asserted in tests/test_behavior.py.
        "stretch_comparing_natives": Quantity(
            value=7, unit="contract", provenance="verified", grounded=True,
            source="conduct@0.5.0: conduct/twice, last-write, commute, undo, durable, "
                   "same-story, constructible; 21 demonstrations beside the implementation; "
                   "each lawful tape judged >= 1 pair (test_a_stretch_law_judges_something)"),
    },
    payload={
        "note":
            "Named rather than stretched: conduct/effect could have been widened to keep "
            "reading after the first agreeing read and call that durability, or to compare "
            "two consecutive same-kind acts and call that idempotence, and each widening "
            "would have convicted by accident the first time a tape did something the "
            "widening had not imagined. Positions now travel on the imported tape, so every "
            "one of the four is computable; what each still needs is a tape in the estate "
            "that stages its scenario, so the native is written against a real refuter and "
            "not a guessed one.",
    },
    children=[
        Node(id="durability-first", kind="discharge",
             payload={
                 "condition":
                     "A native per family, each arriving when a tape in the estate can "
                     "witness it — shown-once-shown-until-touched first, since every read "
                     "through the same door after the witnessing read is already on the first "
                     "consumer's flights. Whoever writes one grounds the param above with the count that "
                     "then holds.",
             }),
    ],
)


_DERIVED_DECISION = Node(
    id="a-view-projects-from-the-apps-statement",
    kind="decision",
    name="A state-var the app recomputes (a view: a rhythm's pending flag) projects from the "
         "testimony point where the app STATES the value, and names the stored variables it "
         "derives from so its writers are theirs - never from an expression that recomputes "
         "it out of several reads",
    payload={
        "rationale":
            "Hughes' caveat on the abstraction function: a projection that reimplements the "
            "operation tests nothing, because the model's arithmetic and the projection's "
            "are the same arithmetic written twice and agree by construction. The app "
            "already computes the view - the board is the rhythm's decision rendered - so "
            "the honest read is that decision as data at a point (`fr.note('board-shown', "
            "due=[...])`), and the law becomes: the model's arithmetic agrees with the "
            "app's. Staleness is the second half: a view changes without any write of its "
            "own, whenever a variable it depends on is written, so `derived_from` names "
            "those and the native takes their writers as the view's. The testimony node "
            "re-enters the stream at its own mark for the door to find it - the importer "
            "had lifted it into the tree and out of the raw window.",
        "consequence":
            "semantic-model@0.11.0: `shown.derived_from`, a door's `where` reaching the "
            "event's own fields (`name` of a point), a projection reading a point's data as "
            "`res`; the cloakroom's OCCUPIED sign as the example and three agrees "
            "demonstrations (stated, wrong, stale). conduct@0.9.0 reads it. The value laws "
            "and conduct/eventually now reach the views a rhythm derives; what the app must "
            "add is one note per surface where it states a view.",
    },
    params={
        "demonstrations": Quantity(value=3, unit="demonstration", provenance="verified",
                                   grounded=True,
                                   source="epure.spec AGREES_SPEC: SIGN_STATED 0, SIGN_WRONG "
                                          "1, SIGN_STALE 0 under conduct/agrees, "
                                          "semantic-model@0.11.0 digest cf6e19e8"),
    },
    children=[
        Node(id="alt-expr-over-several-reads", kind="alternative",
             name="A projection over several named reads, its expr recomputing the view "
                  "(`today - hoover_last >= 2`)",
             payload={"why":
                      "Exactly the reimplementation the paper warns against: the model's "
                      "guard and the projection's expr would be the same formula, and a "
                      "rhythm bug shared by both (the app's, the model's, the projection's "
                      "all written from the same reading) would be green three times."}),
        Node(id="alt-leave-views-unprojected", kind="alternative",
             name="Keep views unprojected and held by presence, as the census counts them",
             payload={"why":
                      "Then every promise over a pending flag judges 0/0 on every tape "
                      "(the first consumer measured it, 2026-08-21) and liveness stays a model-only "
                      "property; the vocabulary's asymptote is reached by adding the word, "
                      "not by declaring the gap permanent."}),
    ],
)


_CENSUS_DECISION = Node(
    id="the-census-is-read-from-the-sources",
    kind="decision",
    name="The catalogue's size is the census of its sources — every property Hughes 2020 "
         "and RFC 9110 state, each mapped to a law and given a status — never the count "
         "of laws it happened to build",
    links={"supersedes": ["publish-the-conduct-seam"]},
    payload={
        "rationale":
            "publish-the-conduct-seam stands on its two-package reasoning and falls on its "
            "count: `families: 9` was grounded on len(CONDUCT_LAWS), the catalogue measuring "
            "itself. Read in full, the paper states some fifty properties in six categories "
            "and ranks model-based ones — the abstraction function — first; 0.1.0 had "
            "folded that family into nothing and weakened every one it kept from a value "
            "comparison to a presence check. The census (epure.census, mounted below and "
            "shipped as conduct@0.3.0's example) lists every item, maps each to a law, and "
            "gives each exactly one status: covered, weakened, owed, aside. Its params are "
            "computed over the items. The numbers the brief shows are the sources'.",
        "consequence":
            "Eleven laws enter, each cited verbatim from a formula the paper or the RFC "
            "states; three laws carried uncited are cited the same way. What the five "
            "natives do not hold is now 46 owed and 9 weakened items pointing at four "
            "debts, each with a discharge — not a sentence.",
    },
    params={
        "laws_before": Quantity(value=9, unit="law", provenance="verified", grounded=True,
                                source="len(CONDUCT_LAWS) at conduct@0.2.1, digest cdcdd17b"),
    },
    children=[
        Node(id="alt-keep-the-nine", kind="alternative",
             name="Keep the nine families and add the missing ones as they become feasible",
             payload={"why":
                      "That is the filter restated as a plan. A family the source ranks "
                      "first had no red pointing at it anywhere; the next reader would have "
                      "trusted nine as the census because the brief said so."}),
        Node(id="alt-one-law-per-item", kind="alternative",
             name="One law per source property: seventy laws",
             payload={"why":
                      "A law is a form an act inherits by declaring an effect; an item is "
                      "that form instantiated on insert, delete, find or union. Seventy "
                      "laws would be the template-stamping the inheritance decision refused, "
                      "and the census already keeps every item on the record."}),
    ],
)


_PROJECTION_DEBT = Node(
    id="the-world-is-not-yet-projected",
    kind="debt",
    name="No state-var said how the world shows its value, so no native could compare the "
         "store to the model: the model-based family — Hughes's strongest — and the value "
         "forms of effect and frame were unheld. Discharged 2026-08-20: projections on "
         "state-var, conduct/agrees, and a real model projecting its stored variables",
    params={
        # Grounded by the discharge: semantic-model@0.6.0 carries the projection, conduct@0.4.0
        # the native, and chores-model@0.13.0 projects its five stored variables - held to 17
        # real tapes, 539 (act, variable) pairs judged, none disagreeing.
        "projected_state_vars": Quantity(
            value=5, unit="state-var", provenance="verified", grounded=True,
            source="chores-model@0.13.0 (digest 68ad0f00): today, hoover_last, bins_done, "
                   "hoover_assignee, bins_assignee carry `shown`; tools.conformance judged "
                   "539 pairs under conduct/agrees across 17 tapes, 0 disagreeing (2026-08-20). "
                   "The view variables (pending flags, wash_day, wash_by_hand) projected "
                   "nothing then; semantic-model@0.11.0's derived view (2026-08-21, "
                   "decision a-view-projects-from-the-apps-statement) is how they do"),
    },
    payload={
        "note":
            "toList in the paper: a function from the concrete store to the abstract state. "
            "Here the abstract side exists — the automaton's variables and updates — and "
            "the concrete side is on the tape as reads. What is missing is the arrow: per "
            "state-var, the read door and the expression that turns its result into the "
            "variable's value. With it, one native holds projected == computed after every "
            "act, and effect and frame become value laws for free. Variables that are views "
            "(a pending flag recomputed by a rhythm) were thought not to project cheaply - "
            "the paper's own caveat, that a projection reimplementing the operation tests "
            "nothing - until the derived view (2026-08-21, decision "
            "a-view-projects-from-the-apps-statement): a view projects from the point where "
            "the app states it, and reimplements nothing.",
    },
    children=[
        Node(id="projections-land-in-semantic-model", kind="discharge",
             payload={
                 "condition":
                     "semantic-model publishes a projection payload on state-var (door + "
                     "expr over the read's result), conduct publishes conduct/agrees holding "
                     "projected == computed after every act, and a real model projects at "
                     "least its stored variables with one real tape held to it. The param "
                     "above is then grounded with the count projected.",
             }),
    ],
)


_MERGE_DEBT = Node(
    id="no-kind-names-a-merge",
    kind="debt",
    name="semantic-model had no action over two worlds, so the fourteen union properties "
         "of the paper — a bulk import, a sync, a merge — bound to nothing. Discharged "
         "2026-08-20: the `merges` effect and conduct/merge",
    params={
        # Grounded by the discharge: the other world arrives as arguments, one per variable,
        # left-biased through `either`; conduct/merge holds left bias, self-merge and
        # associativity on the cloakroom's import, five demonstrations.
        "merge_kinds": Quantity(value=1, unit="kind", provenance="verified", grounded=True,
                                source="semantic-model@0.8.0 `merges`; conduct@0.6.0 "
                                       "conduct/merge. No app of the estate merges yet: judged "
                                       "0 on every real tape, which the report says"),
    },
    payload={
        "note":
            "Not a gap any app of the estate has hit yet — no app imports or syncs a second "
            "store — which is why it is a debt and not a law with a native. Listed at its "
            "size: thirteen of the paper's seventy items.",
    },
    children=[
        Node(id="a-merge-kind-arrives-with-its-first-app", kind="discharge",
             payload={"condition":
                      "The first app that merges two worlds (an import, a household sync, a "
                      "backup restore) declares it, semantic-model gains the kind, and the "
                      "left-biased/idempotent/associative laws get their native."}),
    ],
)


_VALIDATOR_DEBT = Node(
    id="no-kind-names-a-validator",
    kind="debt",
    name="No kind named an entity's version stamp or a precondition on it, so RFC 9110's "
         "validator and conditional-request properties bound to nothing — although the first "
         "consumer already stamped a `rev` on every change. Discharged 2026-08-20: the `validator` kind, "
         "`requires`, conduct/stamped and conduct/conditional",
    params={
        "validator_kinds": Quantity(value=1, unit="kind", provenance="verified",
                                    grounded=True,
                                    source="semantic-model@0.8.0 `validator` (+ `requires` on "
                                           "action); conduct@0.6.0 conduct/stamped and "
                                           "conduct/conditional, seven demonstrations"),
    },
    payload={
        "note":
            "Nine of the census's items. The strong-validator half is cheap once the stamp "
            "is a door: every act with an effect must also pass through the validator door. "
            "The conditional half needs an act to carry an expected version as an argument "
            "and refuse on mismatch — the first consumer had no such act then.",
    },
    children=[
        Node(id="the-stamp-becomes-a-door", kind="discharge",
             payload={"condition":
                      "semantic-model names a validator door on the model; conduct/stamped "
                      "holds every effect to moving it; a conditional act exists in some app "
                      "and conduct/conditional holds it to comparing first."}),
    ],
)


_GENERATED_DEBT = Node(
    id="no-generated-world-is-checked",
    kind="debt",
    name="A mutated tape was judged without first being held to the model, so a property "
         "checked on it could be checked on an invalid world. Discharged 2026-08-20: a probe "
         "tape is held to conduct/constructible before any other law is reported",
    params={
        "mutated_tapes_validated": Quantity(
            value=1, unit="rule", provenance="verified", grounded=True,
            source="epure.suite: a tape any of whose calls carries `probe: true` is red on "
                   "an unreachable world and its other laws are not reported "
                   "(tests/test_suite.py)"),
    },
    payload={
        "note":
            "Hughes: 'Invalid test data provokes false positives … This is why prop "
            "ArbitraryValid is so important.' Two of the census's items.",
    },
    children=[
        Node(id="probes-are-refined-before-they-are-judged", kind="discharge",
             payload={"condition":
                      "The suite refuses to report conduct verdicts on a probe tape whose "
                      "trace does not refine — refinement re-checks every invariant at "
                      "every step, which is ArbitraryValid for a recorded world."}),
    ],
)


_DOOR_CENSUS_DEBT = Node(
    id="no-door-census",
    kind="debt",
    name="A write through a door no declaration named, inside a read-act, passed every "
         "law: the frame saw declared doors and RFC 9110's `safe` says the WHOLE state. "
         "Discharged 2026-08-20: the `boundary` kind and conduct/doors",
    params={
        "write_functions_undeclared": Quantity(
            value=0, unit="function", provenance="verified", grounded=True,
            source="conduct/doors on the cloakroom (5 write functions, all admitted) and on "
                   "chores-model@0.16.0 (the recorder's 7 write functions held against the "
                   "doors) - ledger/conformance.json"),
    },
    payload={
        "note":
            "The survey (epure.survey) drafts doors from the tapes that exist; the boundary "
            "knows the functions that could write whether or not a tape took the path. The "
            "census that closes this compares the two lists and is red on a write function "
            "no door of any action names — which is what makes `touches.via: []` mean the "
            "whole state.",
    },
    children=[
        Node(id="every-write-function-is-some-doors", kind="discharge",
             payload={"condition":
                      "A native over (model, boundary declaration): every function the "
                      "boundary records as a write is matched by a door of some action. "
                      "Grounded with the count that then holds; the first consumer first, where "
                      "the boundary is one declared module."}),
    ],
)


_ATTRIBUTION_HYPOTHESIS = Node(
    id="a-red-is-attributed-by-a-rule-not-a-reader",
    kind="hypothesis",
    name="A red from the conduct natives can be attributed - model, code, or harness - by a "
         "rule over what the native already knows, without a reader opening the tape",
    payload={
        "held_because":
            "The program's direction is human -> AI -> code: the human states intent, the "
            "code renders the verdict. Today the verdict stops one step short. A native says "
            "WHICH act, WHICH variable, WHICH two worlds disagree; which of the three things "
            "is wrong - the drawing, the program, or the harness that recorded it - is still "
            "read off the tape by whoever is watching. Six reds were attributed this way on "
            "2026-08-21 and zero by the tooling. Yet the facts that decided them are facts "
            "the natives hold: whether the moved variable is a derived view; whether a clock "
            "read or a tick sits between the two worlds; whether the model declares the "
            "variable at all; whether the act's own writes went through any door of the "
            "variable; whether the same act on another tape was green. The bet is that a "
            "small rule over those facts names the culprit in most cases, and that the cases "
            "it cannot name are a short, growing list of new words - the asymptote again. "
            "The rule shipped 2026-08-21 (conduct@0.11.0): conduct/agrees names model, app, "
            "harness or unnamed on every red from the four facts, one row per profile, "
            "demonstrated on the cloakroom; `python -m epure.attribution claims.jsonl` "
            "counts, from the diagnosis claims' `red` records, the reds met against the "
            "reds the rule named right. The presence laws followed (conduct@0.12.0, "
            "2026-08-21 evening): conduct/effect from five facts of its own, conduct/frame "
            "from whether the stray write names what the act was given or every act of the "
            "action writes through it - the two cold reds of the day had been under these "
            "laws, where no rule spoke.",
        "consequence_if_wrong":
            "The reader stays in the loop for attribution, and the program's right edge is "
            "the verdict 'something is wrong here', which is still the larger half of the "
            "value. Nothing built on top depends on attribution being automatic; the cost of "
            "being wrong is the diagnosis minutes per red, counted below.",
    },
    params={
        # Computed per session from the claims and the receipts the natives write, never
        # typed: the numerator is the reds whose diagnosis a tool wrote, the denominator is
        # every red a session met. Ungrounded until the first tool-written diagnosis.
        "reds_attributed_by_a_tool": Quantity(
            value=32, unit="red", provenance="verified", grounded=True,
            source="2026-08-22, the third session, the first whose reds were all COLD - met by "
                   "the harness that reads the whole world after every act, none induced: 11 met, "
                   "4 named, 3 right (`epure.attribution` over both consumers' claims, "
                   "--session); the last two, on the flight the draft named, unnamed rightly. "
                   "The CALIBRATION the same day (chores' tools.induce, now a CI test with a "
                   "floor): 0.13.0 had read 73 met / 52 named / 40 right on the induced set while "
                   "fixing one cold red - the two-days clock fact left the machine-day fault "
                   "unnamed - and 0.14.1 reads 73 / 61 / 54 with the clock held against the "
                   "model's own clock variable and the act-between fact asked first. agrees 3/3/2: a tick carrying a missed turn forward was named "
                   "harness on 'a clock read between', a fact true of every board statement - "
                   "the fact is now whether the clock MOVED (0.13.0); two done-bins reds were "
                   "named model by 'read-clock between', an act with no door - right by accident, "
                   "and 0.13.1 counts an act between only with a door. frame 1/1/1. The other "
                   "five reds fell under laws with no rule: stamped (the validator's scope), "
                   "eventually (twice - the horizon counted reads; then a flight where nobody "
                   "hoovered), refinement (two guards the app never had), and a persona "
                   "falsifier (the-return, the missed pile on a return day). Ratio 3/9, the "
                   "first session under one half: one of the three the falsifier needs. Earlier, "
                   "2026-08-21, the first measurement: the first consumer re-induced the "
                   "four faults its first real run had met (one harness, three model) in "
                   "scratch, with the culprits known, and held the rule's word against them - "
                   "12 reds met, 12 named, 11 right, the tool's own tally. The miss named "
                   "harness where the drawing was wrong: a dropped update hid the act's doors "
                   "as writers and the red landed on the neighbour. That fact - an act "
                   "between the act and the read its world-after came from - is the fifth "
                   "fact (conduct@0.11.1); re-measured 12/12/12. Before the rule: six reds, "
                   "zero named by a tool. The first COLD reds, the same day, in the second "
                   "consumer's first slice: 2 met, 0 named - one under agrees errored in the "
                   "projection before the rule could speak (a fractional clock, parsed as a "
                   "date), one under effect, which has no rule. Both harness. The induced "
                   "number is the calibration; this is the measurement, and it is 0 of 2. "
                   "The evening of the same day, the presence rules (conduct@0.12.0) held "
                   "against known faults in both consumers, `epure.attribution` over each "
                   "repo's claims for the session: agrees 12/12/12 again; effect 15/15/15 "
                   "in the first consumer (a completion's via spelt as the chore door - "
                   "model) and 2/2/2 in the second (its cold red re-induced: the fractional "
                   "clock stringified by the store - harness, named by the type-forgetting "
                   "fact); frame 12 met / 6 named / 0 right - the 0.12.0 rule named app on "
                   "the six re-induced 2026-08-20 sightings (sent/*, index/metrics on "
                   "turn-done), all the drawing's; the write names nothing the act was given "
                   "and no tape fact separates an omitted conditional door from a stray "
                   "write, so 0.12.1 says unnamed there (the same six: 6 met, 0 named). "
                   "Total 41 met, 35 named, 29 right; excluding the superseded 0.12.0 frame "
                   "run, 35 met, 29 named, 29 right: every name the rules give is right, and "
                   "what they cannot name they decline. The second cold red of the morning "
                   "is not a red any more (weekday reads a numeric string), so it cannot be "
                   "re-measured"),
        "reds_met": Quantity(
            value=52, unit="red", provenance="verified", grounded=True,
            source="the same measurement: the denominator, counted by the same tally over "
                   "both consumers' claims files (41 through 2026-08-21, 11 cold on 2026-08-22)"),
    },
    children=[
        Node(
            id="the-reader-keeps-attributing",
            kind="falsification",
            name="Three consecutive sessions where the rule attributes fewer than half the "
                 "reds met, once the rule exists",
            payload={
                "claim":
                    "Once a diagnosis rule ships on the violation (conduct/agrees first: "
                    "derived-or-stored, clock-between, declared-or-not, written-through-a-"
                    "door-or-not), count per session the reds it named right against the "
                    "reds met. Three consecutive sessions under one half kills this: the "
                    "facts a native holds were not the facts that decide, and attribution "
                    "is a reading job. Not 'the rule was wrong once': the ratio, over time.",
                "cadence": "per-session, from the claims files",
                "discharge_route":
                    "The counter stays and becomes the honest number in every status: reds "
                    "met, reds the tool named. The program's right edge is then stated "
                    "where it is, not where it was hoped to be.",
            },
        ),
    ],
)


_BETWEEN_LOOKS_ONE_WAY = Node(
    id="the-act-between-is-only-looked-for-forwards",
    kind="debt",
    name="The culprit rule asks whether a door-bearing act lies between an act and the read "
         "its world-AFTER came from, and never the mirror question about the read its "
         "world-BEFORE came from - so a view's stale statement lands on the wrong culprit",
    payload={
        "what_it_costs":
            "A view is read rarely - a board statement, not every act - so one pair of "
            "statements is the window of every act in the span between them, and one act's "
            "undeclared update is a disagreement all of them carry. The forward fact "
            "(conduct@0.14.1) rescues the acts BEFORE the mover: their world-after was read "
            "past it. The acts AFTER it have the mirror problem - their world-before was read "
            "before it - and nothing asks, so they fall through to the harness fallback, "
            "'the statement came from something not on the tape'. On the calibration set "
            "that is the set-today fault's four rows of nine, named harness where model is "
            "known - four of the residual rows of "
            "[[a-red-is-attributed-by-a-rule-not-a-reader]]. Measured, not guessed: the fact "
            "was written (a `before` list beside "
            "`between`, guarded by `not clock` so a moved clock still wins as direct "
            "evidence of the harness) and the calibration read 73 met / 61 named / 58 right, "
            "up from 54, with no other row moved and 145 tests green. Then it was REVERTED, "
            "because it cannot pass the genericity gate yet.",
        "why_it_is_not_paid":
            "The gate wants the fact demonstrated on the cloakroom, and the cloakroom cannot "
            "witness it. The fallback the fact corrects is reached only by an act that writes "
            "NOTHING the model knows - a read-act - because any known write reaches `model` "
            "one branch earlier. Every cloakroom action writes a known door; the four chores "
            "rows are read_wake, clock-read, show_board and board-read. So the spec bed lacks "
            "the one shape that exhibits the bug, which is exactly why the bug went unseen. "
            "Paying it means giving the cloakroom a read-only action (`updates: []`, "
            "`touches.via: []`, as every real consumer has), which is semantic-model@0.15.0, "
            "a conduct republish and a walk of the pin chain - a piece of work with its own "
            "session, not a rider on another.",
    },
    params={
        "rows_misnamed": Quantity(
            value=4, unit="red", provenance="verified", grounded=True,
            source="python -m tools.induce in the first consumer, 2026-08-22: the set-today "
                   "fault reads model 5 / harness 4 of 9 - the five whose window holds the "
                   "mover, and the four that follow it. The nine are one disagreement "
                   "(wash_day -1 -> 1) seen from five successive acts and their calls, "
                   "between one statement and the next"),
        "calibration_if_paid": Quantity(
            value=58, unit="red", provenance="verified", grounded=True,
            source="73 met / 61 named / 58 right with the fact in place, against 73 / 61 / 54 "
                   "without - measured on the working copy before the revert, the four rows "
                   "moving harness -> model and nothing else moving"),
    },
    children=[
        Node(id="discharge-a-read-act-in-the-cloakroom", kind="discharge",
             name="Give the cloakroom a read-only action, demonstrate the mirror fact on it, "
                  "and ship the rule with the calibration floor raised to 58",
             payload={"route":
                      "semantic-model@0.15.0 grows the read-act; the mirror of "
                      "SHELVED_OFF_THE_HOOK is a view stated before an undeclared mover and "
                      "read again after a read-act that follows it; conduct republishes with "
                      "the row demonstrated; both consumers repin and the floor rises from 54 "
                      "to 58 in the commit that says why. Raising the floor without the "
                      "demonstration would be tuning the rule on its test set, which the "
                      "induced-faults decision already refuses by name."}),
    ],
)


_DRAFT_ROUTING = Node(
    id="a-draft-disagreement-is-adjudicated-before-it-reaches-a-person",
    kind="decision",
    name="The draft's remainder is triaged into three tracks - a missing flight, an "
         "adjudication recorded as an act, and the small rest where intent decides - and only "
         "the third reaches the person",
    payload={
        "rationale":
            "The model and the code do not come from one head, so their agreement is not "
            "self-congratulation: both are written to a person's prompt and both are "
            "corrected by an external signal - a gate going red sends an agent back to the "
            "code, a conviction sends the work to the person. Every red already has a track. "
            "The draft's remainder has none: it prints a line and waits to be noticed, which "
            "is why the same rows have survived four measurements. Routed the same way it "
            "splits three ways, and the sizes are very unequal. UNWITNESSED and 'positives "
            "only' are not disagreements at all - they are absent evidence, and `--propose` "
            "already names the flight, so the track is mechanical. DIFFERENT is a real "
            "contradiction with everything an adjudicator needs in hand: both expressions, "
            "the separating world, the tapes. Most resolve to a stale drawing or a wrong "
            "program, and the verdict is defensible against the evidence rather than "
            "asserted. Only what turns on INTENT is left - should a placed wash survive a "
            "calendar day - and no tape answers that, so no confidence about it should be "
            "manufactured.",
        "consequence":
            "Step 4's `confirmed` changes shape. It was drawn as a person accepting a drafted "
            "expression; it becomes an ADJUDICATION recorded as an act - the verdict, who or "
            "what made it, when, the drafted and hand expressions, and the tapes and acts it "
            "rested on - carrying whether it was settled against evidence or escalated "
            "because intent decides. The recording is the whole point: an adjudication with "
            "no record of what it rested on is a confident opinion that evaporates, which is "
            "the thing this repository exists to refuse. The rule already drawn for step 4 "
            "still holds and now bites harder: a confirmation goes red when the samples it "
            "rested on no longer exist on any tape.",
    },
    children=[
        Node(id="alt-every-disagreement-reaches-the-person", kind="alternative",
             name="Show the person every row the draft could not settle, as the step-4 "
                  "sketch had it",
             payload={"why":
                      "The largest class is absent evidence, which a person cannot supply by "
                      "reading - the flight can. Spending the one scarce reviewer on rows a "
                      "tool settles is how a review track dies: it fills with work that did "
                      "not need judgement until the judgement stops arriving."}),
        Node(id="alt-the-filter-decides-everything", kind="alternative",
             name="Let the adjudicator settle every row and escalate nothing",
             payload={"why":
                      "Intent has no witness on any tape. A firm answer where no evidence "
                      "exists is exactly the failure mode the whole programme is built "
                      "against - and it would be indistinguishable, in the record, from the "
                      "rows that were genuinely settled."}),
        Node(id="alt-leave-it-printed", kind="alternative",
             name="Leave the remainder as lines in --propose and let whoever reads them act",
             payload={"why":
                      "That is today, and today the rows persist by default rather than by "
                      "decision. A measurement whose remainder nothing routes is a "
                      "measurement nobody acts on."}),
    ],
)


_REACHABLE_GRID = Node(
    id="equivalence-is-judged-where-the-world-can-be",
    kind="decision",
    name="The draft's equivalence is decided over the model's reachable states, narrowed for "
         "an update to the states where its action is enabled - never the product of the "
         "declared domains",
    payload={
        "rationale":
            "The draft measures a drafted expression against a hand-written one by agreeing "
            "at every point of a grid. Which grid is the whole question. The product of the "
            "declared domains contains worlds the model can never be in: chores declares "
            "`wash_pending` and `wash_day` separately, and on the reachable set they are one "
            "fact - pending exactly when there is a day, 8 of the 16 combinations, the other "
            "8 unreachable. A disagreement at such a point charges the draft for a world "
            "that does not exist, and - worse - `--propose` then names it as the next flight "
            "to fly. It named exactly that: take tick at today=1, wash_day=0 - 1, "
            "wash_pending=true, a pending wash with no day, an errand nobody can run. So the "
            "grid is the reachable set, from `epure.prove`'s own BFS - the same walk the "
            "proof makes, so the draft and the proof mean one thing by 'a state'. Then the "
            "same argument once more, to the guard: an update only ever runs where the guard "
            "let the act through, so a world it refuses is no more a place to tell two "
            "updates apart than an unreachable one. Reachability alone left the tick's "
            "`wash_pending` different at today=6 - a Sunday tick, which `today < 6` refuses; "
            "both narrowings, and the row is equivalent. A guard is judged on the reachable "
            "set ONLY: narrowing its grid by itself would be circular.",
        "consequence":
            "Two equivalences now, counted apart and never merged: `domain`, agreeing "
            "everywhere, and `enabled`/`reachable`, agreeing everywhere the model can be. "
            "Both are honest; only the first is unconditional, and a row holding on the "
            "restricted grid alone says so. The restriction can hide exactly one thing, so "
            "that thing is counted out loud: a sampled pre-world the model cannot reach is "
            "the app in a state the model calls impossible - a finding, not a rounding - and "
            "`unreachable_pre` heads every run. It is 0 on both consumers. The price is the "
            "walk: 35280 states for chores, once per measurement, ~9s.",
    },
    params={
        "reachable_share": Quantity(
            value=6.8, unit="percent", provenance="verified", grounded=True,
            source="chores-model@0.24.0: 35280 states reachable of the 516096 in the product "
                   "of the declared domains (epure.prove.reachable_from_node, 2026-08-21). "
                   "The grid the draft used before was fourteen times too big, and the "
                   "surplus was not neutral - it is where --propose was sending people"),
        "rows_moved": Quantity(
            value=1, unit="update", provenance="verified", grounded=True,
            source="tick.wash_pending: different -> equivalent, and equivalent only where the "
                   "model reaches the act enabled. Measured as two changes with two numbers: "
                   "reachability alone moved 0 of the 5 different rows, and moved 1 of the 15 "
                   "named experiments onto a flyable world (today=6, wash_day=4, replacing "
                   "the unreachable wash_day=0 - 1); the enabled narrowing then closed the "
                   "row, today=6 being a Sunday tick that `today < 6` refuses. The hypothesis "
                   "the proposal carried - that reachability alone would move it - is "
                   "refuted, and the pair is what moved it"),
    },
    children=[
        Node(id="alt-keep-the-domain-grid", kind="alternative",
             name="Leave the grid as the product of the declared domains",
             payload={"why":
                      "It is the stricter equivalence and reads as the safer one, which is "
                      "how it survived four measurements. But strictness against worlds that "
                      "cannot occur is noise with a good reputation: it charged the draft for "
                      "a row it had right, and sent whoever read --propose to fly a world the "
                      "model forbids. A remainder nobody can work on measures nothing."}),
        Node(id="alt-reachable-only", kind="alternative",
             name="Restrict to the reachable set and stop there",
             payload={"why":
                      "Half the argument, and the half shows: the separating point for the "
                      "tick's wash_pending moved from an unreachable world to a reachable one "
                      "the tick's own guard refuses - flyable-looking and still unflyable. "
                      "The guard is part of where an update lives, and leaving it out keeps "
                      "the same class of unrunnable errand with better manners."}),
        Node(id="alt-restrict-the-samples-instead", kind="alternative",
             name="Judge equivalence on the sampled pre-worlds only",
             payload={"why":
                      "That is the fit the whole hypothesis exists to avoid. Equivalence on "
                      "the samples is what the draft ALREADY has by construction - every "
                      "candidate satisfies every sample - so the number would be 29 of 29 and "
                      "would mean nothing. The grid has to be wider than the tapes; the "
                      "question was only how much wider, and the answer is: as wide as the "
                      "model can actually be."}),
    ],
)


_DRAFT_HYPOTHESIS = Node(
    id="the-tapes-draft-the-arithmetic",
    kind="hypothesis",
    name="A model's updates and guards can be drafted from its tapes - the simplest expression "
         "of a small grammar every projected sample satisfies - and a person confirms intent "
         "rather than writing arithmetic",
    payload={
        "held_because":
            "The frame of a model is generated already: effects, doors and boundaries come "
            "off the tapes (epure.survey). What a person still writes is the arithmetic - "
            "what each action does to each variable, and when it may happen - and that is "
            "the part the tapes witness most directly: conduct/agrees already projects the "
            "world before and after every bound act to hold the hand-written update against "
            "it. The same samples, read the other way, propose the update: the frame, a "
            "constant, an argument, another variable, an increment, a saturating increment, "
            "simplest first (epure.draft, 2026-08-21). The bet is that most of a real model's "
            "updates are the simplest expression its tapes admit, and that the remainder - "
            "the human's share - is a short list of named kinds: a bound no run reached, a "
            "variable not projected around the act, a path no tape took. Guards are the "
            "other half of the bet and the weaker one by construction: a guard is what is "
            "REFUSED, and a tape with no refusal of an act holds no world where its guard was "
            "false, so positives alone draft at most the necessary booleans. The draft is "
            "measured, never installed: each proposal is held EQUIVALENT to the hand-written "
            "expression over every state the model can reach with the act enabled "
            "([[equivalence-is-judged-where-the-world-can-be]]), not on the samples that "
            "made it, so a constant that fits two "
            "samples of the same day is counted as different from the argument the person "
            "meant. Two consumers make the number a measurement and not a fit.",
        "the_loop_closed_once":
            "2026-08-22: `--propose` names, per unsettled row, the observation that separates "
            "draft from hand. Three were flown as named - the clock around the Monday acts, "
            "the quota's bound, the guards - and the number moved from 8 to 18 of 29 while the "
            "tapes corrected the hand four times. Hypothesis from the data, falsifier stated, "
            "the next experiment chosen by what discriminates; what remains for a person is "
            "five rows of 'different', each with its separating case printed beside it.",
        "consequence_if_wrong":
            "The person keeps writing the arithmetic, as today, and the draft is a checklist "
            "of what the tapes do and do not determine - still worth having, since every "
            "'unwitnessed' is a missing read around an act and every 'different' names the "
            "case the tapes never took. Nothing built on the model depends on how it was "
            "written; the proof and the natives judge the model that exists.",
    },
    params={
        # Computed by `python -m epure.draft` over each consumer's committed tapes and its
        # pinned model, never typed. Updates: the hand-written (action, variable) pairs;
        # equivalent: the draft agrees over the whole domain.
        "updates_by_hand": Quantity(
            value=29, unit="update", provenance="verified", grounded=True,
            source="2026-08-22: chores-model@0.22.0 over its 23 tapes declares 25 updates, "
                   "health-model@0.1.1 over its one flight declares 4 - the same counts as the "
                   "first measurement (2026-08-21, chores-model@0.20.0 over 20 tapes, "
                   "health-model@0.1.0), with different arithmetic behind five of them"),
        "updates_drafted_equivalent": Quantity(
            value=25, unit="update", provenance="verified", grounded=True,
            source="2026-08-22: 25 of 29 - chores 21 of 25, health 4 of 4 - after the GRID "
                   "was narrowed to where the world can be "
                   "([[equivalence-is-judged-where-the-world-can-be]]): the tick's "
                   "wash_pending, whose separating world was a pending wash with no day, is "
                   "equivalent everywhere the model reaches a tick enabled, and the "
                   "measurement says which - 1 of the 25 holds on the restricted grid only, "
                   "24 hold over the whole domain. Health unchanged at 4 of 4, 0 restricted. "
                   "Sampled pre-worlds the model cannot reach, both consumers: 0 - the tapes "
                   "stay inside the drawing, which is what makes the narrowing safe to make. "
                   "Four different remain: the tick's wash_by_hand and skip-wash's "
                   "(placed-wash paths no tape takes), skip-bins' two from one sample. "
                   "Earlier, 2026-08-22, late: 24 of 29 - chores 20 of 25, health 4 of 4 - "
                   "after the "
                   "RICHER GRAMMAR (a boolean as the simplest separating predicate, an int as a "
                   "conditional in the hand's own form: wash_day and done-bins' flag drafted "
                   "equivalent) and the FLIGHT IT NAMED (the-placed-turns, on the separating "
                   "worlds --propose printed one variable from a sampled one: two more tick "
                   "corrections, two acts witnessed; 0 partial, 0 unresolved, 0 unwitnessed). "
                   "Five different remained: the tick's wash_pending (the separating world was "
                   "one the model cannot reach - the generator did not know reachability, "
                   "which the reachable grid then fixed), two "
                   "placed-wash paths no tape takes, skip-bins' two from one sample. Earlier the "
                   "same day, the second measurement, three moves apart so each is its own "
                   "number. THE HARNESS: chores' flights read the clock and the board after "
                   "every act (the Monday tick off tape, since production's wake index is never "
                   "empty) - chores 5 -> 11 of 25, unwitnessed 12 -> 3, and four updates moved "
                   "from 'different' to 'unresolved' because the richer samples show variation "
                   "the grammar has no word for (the tick's views). THE TOOL: a row without a "
                   "before no longer thrown away (it witnesses a constant or an argument), a "
                   "candidate no row can judge skipped, `partial` naming the row and the "
                   "unread operand - health 3 -> 4 of 4 (pick_day := day had been witnessed "
                   "all along), chores' hoover_last := today named 'the store showed no today "
                   "before' the two Monday acts. THE FLIGHTS THE DRAFT NAMED: the bins bound "
                   "reached and held (the-bins-bound) - min(bins_settled + 1, 7) different -> "
                   "equivalent; the guards tried (the-guards-are-tried) - the app proceeded "
                   "on both, five guards left the drawing. Total 18 of 29: chores 14 of 25, "
                   "health 4 of 4. The remainder, named by `--propose`: 5 DIFFERENT (the "
                   "tick's wash_by_hand and skip-wash's, where the tapes say frame and no "
                   "placed wash ever met a calendar day or a skip; set-wash-today's wash_day, "
                   "set on a Tuesday only; skip-bins' two, one sample); 4 UNRESOLVED (the "
                   "tick's three view updates and done-bins' comparison - conditionals and "
                   "comparisons, the grammar's own remainder); 2 UNWITNESSED (set-hoover-today, "
                   "skip-hoover: no tape takes them). And what the tapes did to the HAND: four "
                   "corrections to chores-model (a missed turn carried forward, the quota's "
                   "flag a view of settled asks, five guards, a door) - the draft measured "
                   "against a drawing the tapes had first put right. Earlier, 2026-08-21, the "
                   "first measurement: 8 of 29 - chores 5 of 25 (wash_pending := false, wash_day := 0 - 1, "
                   "hoover_pending := false, hoover_assignee := member, bins_assignee := "
                   "member), health 3 of 4 (curated := true, curated := false, poll_day := "
                   "day). The remainder, named: 12 UNWITNESSED - no sample shows the variable "
                   "on both sides of the act (the completion acts never read the wake index, "
                   "so `today` is not in their world; the call-level actions declare nothing); "
                   "1 UNRESOLVED - done-hoover's hoover_last := today, the same missing read; "
                   "8 DIFFERENT - the tick's four view updates, where no tape moved the view "
                   "across a tick the way the arithmetic says (the draft says frame, or the "
                   "constant the samples show); done-bins' min(bins_done + 1, 7), where no "
                   "run reached the bound (the draft says bins_done + 1); done-wash's "
                   "wash_by_hand := false, where no placed wash was ever settled on a tape "
                   "(the draft says frame); health's pick_day := day, where the flight "
                   "publishes picks on one day only (the draft says the constant 1). Every "
                   "'different' is a case the tapes never took, and the draft says which"),
        "guards_by_hand": Quantity(
            value=16, unit="guard", provenance="verified", grounded=True,
            source="the same run: chores 13, health 3 - five of chores' now `true`, since the "
                   "tape refuted them"),
        "guards_drafted_equivalent": Quantity(
            value=1, unit="guard", provenance="verified", grounded=True,
            source="2026-08-22: still 1 - and the draft can now read refusals (the pre-worlds "
                   "of error-outcome acts, the simplest separating predicate of a small "
                   "grammar), so the number is no longer a limit of the tool. It is a fact "
                   "about the consumers: refused bound acts on 24 tapes, 0. The flight built "
                   "to refuse (the-guards-are-tried) found the app proceeding where the "
                   "drawing's guards said no, both times - the guards were the hand's, and "
                   "left; health's `day >= today` is a clock claim on a variable nothing "
                   "projects. A guard is drafted from refusals or not at all, and slice 1 of "
                   "either app refuses nothing by model state. Earlier, 2026-08-21: "
                   "health's show-home, whose hand guard is `true`. Refused "
                   "bound acts on all 21 tapes: 0 - no tape holds a world where any guard "
                   "was false, so the positive-only draft (the booleans that never varied) "
                   "overfits every real guard with the flags that happened to hold: "
                   "`wash_pending` is drafted as `wash_pending and not wash_by_hand and not "
                   "hoover_pending and bins_pending`. A guard is drafted from refusals or "
                   "not at all; this is the number that says so"),
    },
    children=[
        Node(
            id="the-tapes-underdetermine-the-arithmetic",
            kind="falsification",
            name="Once every act reads its world on both sides and the flights take the "
                 "bounding paths, fewer than half the updates draft equivalent",
            payload={
                "claim":
                    "The 'unwitnessed' and 'different' remainders each name a missing read "
                    "or a path no tape took. Close them - project the clock around the "
                    "completion acts, fly a week that reaches the quota's bound, settle a "
                    "placed wash, publish picks on two days - and re-run epure.draft. If the "
                    "equivalent share stays under one half of the updates a person wrote, "
                    "the tapes do not determine the arithmetic and the draft is a checklist, "
                    "not a generator. Guards are measured separately: with no refusal on any "
                    "tape they are not a test of this claim until a flight refuses something.",
                "cadence": "per consumer release, from `python -m epure.draft`",
                "discharge_route":
                    "The draft stays as the measurement of what the tapes determine, printed "
                    "in every status beside the attribution ratio; the person writes the "
                    "arithmetic and the natives hold it, as today.",
            },
        ),
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
