"""semantic-model@0.2.0 — the meta-vocabulary a semantic model is written in.

A model authored in these kinds is the drawing the piece is proven against: the prover
(`model/prove`) proves predicates over it once, exhaustively, and the conformance natives
(`model/licensed`, `model/total`, `model/refines`) check every tape against it forever. This
package is neither of those things: it says what a model IS, and it carries the exprs a
model's author writes (guards, updates, licenses, invariants) without evaluating any of them.
Evaluation is the machinery's job; meaning travels first, pinned, so the machinery is built
against a digest rather than a file that can drift under it. Since 0.1.1 the four contracts
travel here too — as DATA (native solver descriptors and per-kind operations, the geometry
pattern), never as behavior: the implementations are host code, installed by importing
`epure.prove` and `epure.conformance`, and a native that disagrees with its descriptor's
contract is the bug. 0.2.0 restates the license contract: evidence may be named beyond the
claiming span's own window (`evidence(pattern, 'enclosing')`), because an instantaneous
act encloses nothing and was unlicensable by construction — the debt the 0.1.x license
KindDef carried as "richer window predicates arrive as natives", now due and paid.

Three rules, in the house style — each a structural claim a package cannot be published
without demonstrating and refuting:

- a model with no event-kinds cannot be refined by any tape, so nothing it proves ever binds
  to a running system;
- an event-kind with no license is testimony no evidence could ever convict — relocated
  guessing about meaning;
- an action no event-kind witnesses is a transition the prover would explore and no tape can
  ever exhibit — untestable fiction.

The third rule is why the `observation` kind exists. The natural shape would be an
`observed-as` link from action to event-kind, and it is deliberately not that: the rule
grammar reaches children (`nodes(kind, self)`) and never arbitrary links, so a link-based
requirement would be invisible to the one rule that exists to enforce it. The decision, and
the two shapes it rejected, are in this repo's ledger (`epure/tree.py`).
"""

from __future__ import annotations

from quern import KindDef, Node, OperationDef, Rule, SolverDef
from quern.library import CounterExample, Package

VOCABULARY = [
    KindDef(
        kind="model",
        description="The root of one semantic model: a small, finite mathematical object — "
        "state variables, actions with guards and updates, an alphabet of observable events, "
        "invariants. Its children are `state-var`s, `action`s, `event-kind`s and `invariant`s. "
        "A model is small ON PURPOSE: the tractability of every downstream check — exhaustive "
        "proof at design time, refinement/licensing/totality on every tape — is bought here, "
        "at authoring time, and nowhere else. A domain that resists a small finite model is "
        "not a limitation to hide; it is a modeling decision to journal.",
        operations={
            "prove": OperationDef(
                contract="model/prove",
                description="Exhaustive explicit-state check of every invariant over every "
                "reachable state — `solve('model/prove', self)` on the model node returns "
                "the count of refuted invariants. Bounded, never silently: exceeding the "
                "state cap is a refusal, not a partial pass.",
                params_doc={"cap": "optional bound on explored states (default 1e6)"}),
            "total": OperationDef(
                contract="model/total",
                description="No raw event escapes semantics: "
                "`solve('model/total', scenario, 'model')` on a scenario/session node whose "
                "`model` link names a node of this kind counts the raw boundary events no "
                "span encloses.",
                params_doc={"rel": "the link from the scenario to this model"}),
            "refines": OperationDef(
                contract="model/refines",
                description="The semantic trace is a behavior of the model: "
                "`solve('model/refines', scenario, 'model')` runs this model as an "
                "automaton over the scenario's top-level spans — args bound from span "
                "data, guards and domains respected, every invariant re-checked at every "
                "step — and counts divergences, naming the first divergent span.",
                params_doc={"rel": "the link from the scenario to this model"}),
        },
    ),
    KindDef(
        kind="state-var",
        description="One variable of the model's state; the node's id is the variable's name "
        "in every expr. Payload: `type` (\"bool\" | \"int\" | \"enum\"), `domain` (a value "
        "list for enum, {\"min\": n, \"max\": n} for int, absent for bool), `init` (the "
        "initial value, in the domain). FINITE DOMAINS ONLY in 0.1.0: "
        "only a finite model can be exhaustively proven by an explicit-state checker, so the "
        "bound on an int is not bookkeeping — it is the price of the proof. A quantity that "
        "cannot be finitely abstracted is a modeling decision to journal, not a wide domain "
        "to sneak in.",
    ),
    KindDef(
        kind="event-kind",
        description="One entry of the model's alphabet: a semantic act the instrumented "
        "system may claim, matching BY NAME the `sem` span names the code emits on its "
        "flight-recorder tapes (the node's id is the span name). Payload: `args` ({name: "
        "type}) — the data a claiming span carries. Must carry at least one `license` child: "
        "an event-kind is the unit of testimony, and testimony without an evidence "
        "requirement is not checkable, merely recorded.",
        operations={
            "licensed": OperationDef(
                contract="model/licensed",
                description="Testimony is justified by evidence: "
                "`solve('model/licensed', scenario, 'model')` on a scenario/session node "
                "holds every claiming span to this kind's licenses — each license expr "
                "evaluated with the declared args bound from the span's data, ctx('events') "
                "bound to its own raw window, and evidence(pattern, scope) reading named "
                "events from that window or, with scope 'enclosing', from its lineage — "
                "and counts the spans convicted. A span naming no event-kind of the model "
                "counts too: unknown testimony is unlicensed by definition.",
                params_doc={"rel": "the link from the scenario to the enclosing model"}),
        },
    ),
    KindDef(
        kind="license",
        description="The observation that justifies an emission of its parent event-kind: a "
        "predicate over raw boundary events. Payload: `expr` (rule grammar) and `note` "
        "(prose: what the evidence means). The expr's environment provides the event's args "
        "as variables and two evidence readers: `ctx('events')` — the claiming span's own "
        "raw window, in order — and `evidence(pattern, scope)` — the events whose name "
        "(fn / op / k) matches the fnmatch pattern, where scope 'own' (default) is that "
        "same window and 'enclosing' is the claim's lineage: its window plus every raw "
        "event a testimony ancestor directly encloses. The cut: a license may look beyond "
        "its own window ONLY by naming what it looks for — an instantaneous act's evidence "
        "usually lives one level up, in the act that produced it, but a bare count over an "
        "ancestor's window would be satisfied by any unrelated I/O, which is no license at "
        "all. Direction-blind: evidence anywhere in scope satisfies, before or after the "
        "claim. This package carries the expr and never evaluates it — evaluation is "
        "`model/licensed`'s contract. The move is the same one `ledger@`'s "
        "falsification.expr makes: prose that can already fire.",
    ),
    KindDef(
        kind="action",
        description="One transition of the model. Payload: `guard` (expr over state-vars and "
        "args — when the action is enabled), `updates` ([{\"var\": name, \"expr\": expr}] — "
        "the next state), `args` ({name: type}). Must carry at least one `observation` child "
        "naming the event-kind whose occurrence on a trace instantiates it: an action nobody "
        "can observe is a transition the prover explores and no tape can exhibit, and the "
        "rule below refuses it.",
    ),
    KindDef(
        kind="observation",
        description="The witness relation: this action, when it happens, is what its parent "
        "model's named event-kind testifies to. Payload: `event` — the event-kind's id, "
        "resolved within the enclosing model. An id and not a path, so a model subtree can "
        "move without breaking its own internal references; a dangling id is the conformance "
        "natives' catch (they have full traversal — the rule grammar counts presence, which "
        "is what it can see).",
    ),
    KindDef(
        kind="invariant",
        description="A predicate over state-vars that must hold in every reachable state of "
        "the model — proven exhaustively by `model/prove` at design time, and re-checked at "
        "every step of every refined trace at runtime, for free. Payload: `expr` (rule "
        "grammar over the state-vars as variables) and `note` (prose: what holding means, in "
        "the domain's own words). Safety only in 0.1.0: liveness and temporal claims have no "
        "vocabulary here yet, and that absence is carried as a debt in the authoring repo's "
        "ledger, not silently.",
    ),
]

RULES = [
    Rule(
        name="a-model-declares-its-alphabet",
        kind="model",
        description="A model with no observable vocabulary cannot be refined by any tape: "
        "nothing the prover establishes about it ever binds to a running system, so its "
        "proofs are true and useless. One event-kind is the least a model must offer the "
        "world to be checkable against it.",
        expr="len(nodes('event-kind', self)) >= 1",
    ),
    Rule(
        name="an-event-kind-carries-a-license",
        kind="event-kind",
        description="Unlicensed testimony is relocated guessing about meaning: a span the "
        "code may emit with nothing any tape could be asked to show beneath it. The license "
        "is what anchors the claim to evidence, and an event-kind that carries none has "
        "opted out of the only check that makes testimony worth recording.",
        expr="len(nodes('license', self)) >= 1",
    ),
    Rule(
        name="an-action-is-observable",
        kind="action",
        description="An action no event-kind witnesses is untestable fiction: the prover "
        "explores its transitions, no tape can ever exhibit one, and the gap between the two "
        "is exactly where a proven model quietly stops describing the system. Every action "
        "names the testimony that instantiates it, or it does not enter.",
        expr="len(nodes('observation', self)) >= 1",
    ),
]

# --- the turnstile: one neutral, invented domain that demonstrates everything --------------
#
# The classic coin-operated turnstile — locked until a coin, locked again after a push. Small,
# familiar, and it names no real consumer. The bounded coin/entry counters are not decoration:
# they make the safety property ("nobody passes more times than coins were accepted") a pure
# state predicate, and their bounds are the finiteness the state-var kind insists on.

EXAMPLES = [
    Node(
        id="turnstile", kind="model", name="A coin-operated turnstile",
        children=[
            Node(id="state", kind="state-var",
                 payload={"type": "enum", "domain": ["locked", "unlocked"],
                          "init": "locked"}),
            Node(id="coins", kind="state-var",
                 payload={"type": "int", "domain": {"min": 0, "max": 3}, "init": 0}),
            Node(id="entries", kind="state-var",
                 payload={"type": "int", "domain": {"min": 0, "max": 3}, "init": 0}),
            Node(id="coin", kind="event-kind",
                 payload={"args": {}},
                 children=[
                     Node(id="coin-license", kind="license",
                          payload={"expr": "len(evidence('acceptor.read')) >= 1",
                                   "note": "the claiming span encloses a raw exchange "
                                           "with the coin acceptor — named, so a span "
                                           "wrapping the wrong I/O is convicted, not "
                                           "counted"}),
                 ]),
            Node(id="push", kind="event-kind",
                 payload={"args": {}},
                 children=[
                     Node(id="push-license", kind="license",
                          payload={"expr": "len(evidence('sensor.read')) >= 1",
                                   "note": "the claiming span encloses a raw reading "
                                           "from the rotation sensor"}),
                 ]),
            Node(id="passage-counted", kind="event-kind",
                 payload={"args": {}},
                 children=[
                     Node(id="passage-counted-license", kind="license",
                          payload={"expr": "len(evidence('sensor.read', 'enclosing')) >= 1",
                                   "note": "the derived, instantaneous act: the tally "
                                           "increments because the rotation sensor read a "
                                           "passage, but the read happened in the act that "
                                           "detected it, one level up — a point encloses "
                                           "nothing, so its license names the evidence and "
                                           "looks along its lineage. Decomposition, not a "
                                           "transition: it nests under the push that "
                                           "counted it and no action witnesses it"}),
                 ]),
            Node(id="insert-coin", kind="action",
                 payload={"guard": "state == 'locked' and coins < 3",
                          "updates": [{"var": "state", "expr": "'unlocked'"},
                                      {"var": "coins", "expr": "coins + 1"}],
                          "args": {}},
                 children=[
                     Node(id="insert-coin-witness", kind="observation",
                          payload={"event": "coin"}),
                 ]),
            Node(id="push-through", kind="action",
                 payload={"guard": "state == 'unlocked'",
                          "updates": [{"var": "state", "expr": "'locked'"},
                                      {"var": "entries", "expr": "entries + 1"}],
                          "args": {}},
                 children=[
                     Node(id="push-through-witness", kind="observation",
                          payload={"event": "push"}),
                 ]),
            Node(id="no-free-entry", kind="invariant",
                 payload={"expr": "entries <= coins",
                          "note": "nobody passes through more times than coins were "
                                  "accepted — never unlocked without a prior coin, stated "
                                  "as a pure state predicate so an explicit-state walk can "
                                  "settle it"}),
        ],
    ),
]

COUNTER_EXAMPLES = [
    CounterExample(
        rule="a-model-declares-its-alphabet",
        because="a model with state and an invariant but no observable vocabulary — every "
                "proof over it is true and binds to nothing",
        node=Node(
            id="black-box", kind="model",
            name="A sealed counter nobody can observe",
            children=[
                Node(id="count", kind="state-var",
                     payload={"type": "int", "domain": {"min": 0, "max": 1}, "init": 0}),
                Node(id="bounded", kind="invariant",
                     payload={"expr": "count <= 1", "note": "provable, and unrefinable"}),
            ],
        ),
    ),
    CounterExample(
        rule="an-event-kind-carries-a-license",
        because="testimony with no evidence requirement — the code could claim it forever "
                "and no tape could ever convict the claim",
        node=Node(
            id="beep", kind="event-kind",
            name="An act any code may claim for free",
            payload={"args": {}},
        ),
    ),
    CounterExample(
        rule="an-action-is-observable",
        because="a transition the prover would explore and no tape can ever exhibit — "
                "untestable fiction with a guard on it",
        node=Node(
            id="silent-reset", kind="action",
            name="A reset no event witnesses",
            payload={"guard": "1 == 1",
                     "updates": [{"var": "count", "expr": "0"}],
                     "args": {}},
        ),
    ),
]


# The four contracts of the family, as data a tree pins: descriptors only (native=True, no
# blob) — the implementations are host code (`epure.prove`, `epure.conformance`), installed
# by importing the modules, exactly the geometry pattern. The descriptor is the stable
# surface; whatever honours it may serve it, and a native that disagrees is the bug.
SOLVERS = [
    SolverDef(
        name="model/prove", native=True,
        description="model |= invariants, established exhaustively over every reachable "
        "state of the (finite) model at `path`; returns the count of refuted invariants. "
        "Design-time, once; the artifact a green run emits grounds evidence."),
    SolverDef(
        name="model/licensed", native=True,
        description="(path, rel): count the spans under `path` whose claim the evidence "
        "their licenses name does not justify — own window by default, named evidence "
        "along the lineage via evidence(pattern, 'enclosing') — unknown kinds included."),
    SolverDef(
        name="model/total", native=True,
        description="(path, rel): count the raw boundary events under `path` enclosed by "
        "no span — behavior the linked model does not know exists."),
    SolverDef(
        name="model/refines", native=True,
        description="(path, rel): 0 iff the top-level span trace under `path` is a legal "
        "path of the linked model; on divergence, 1, naming the first illegal step."),
]


SEMANTIC_MODEL_PACKAGE = Package(
    name="semantic-model",
    version="0.2.0",
    description="The meta-vocabulary a semantic model is written in: state variables over "
                "finite domains, actions with guards and updates, an alphabet of observable "
                "events each anchored to evidence by a license, and invariants a checker can "
                "settle exhaustively. A model in these kinds is what the prover proves "
                "predicates over, once, and what the conformance checks confront every tape "
                "with, forever. The package carries exprs and evaluates nothing — meaning "
                "travels first, pinned, and the machinery is built against the digest. Its "
                "rules refuse the three ways a model quietly stops describing a system: no "
                "alphabet, unlicensed testimony, unobservable actions. 0.2.0 pays the "
                "license KindDef's standing debt: an instantaneous act encloses nothing, so "
                "under the own-window-only contract it was unlicensable by construction — "
                "now a license reaches beyond its own window by NAMING its evidence "
                "(evidence(pattern, 'enclosing')), and only so: a bare count over an "
                "ancestor's window would license anything, which is no license at all. The "
                "turnstile grows the derived act (passage-counted) that exercises this; "
                "kinds and rules are otherwise 0.1.1's.",
    publisher="poietic.studio",
    vocabulary=VOCABULARY,
    rules=RULES,
    solvers=SOLVERS,
    examples=EXAMPLES,
    counter_examples=COUNTER_EXAMPLES,
)
