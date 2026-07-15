"""semantic-model@0.1.0 — the meta-vocabulary a semantic model is written in.

A model authored in these kinds is the drawing the piece is proven against: the prover
(`model/prove`) proves predicates over it once, exhaustively, and the conformance natives
(`model/licensed`, `model/total`, `model/refines`) check every tape against it forever. This
package is neither of those things. It is pure vocabulary and rules — no solvers — exactly as
`ledger@0.1.0` is: it says what a model IS, and it carries the exprs a model's author writes
(guards, updates, licenses, invariants) without evaluating any of them. Evaluation is the
machinery's job; meaning travels first, pinned, so the machinery is built against a digest
rather than a file that can drift under it.

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

from quern import KindDef, Node, Rule
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
    ),
    KindDef(
        kind="license",
        description="The observation that justifies an emission of its parent event-kind: a "
        "predicate over the raw boundary events enclosed by the claiming span. Payload: "
        "`expr` (rule grammar; its environment provides ctx('events') — the enclosed raw "
        "events, in order — plus the event's args as variables) and `note` (prose: what the "
        "evidence means). This package carries the expr and never evaluates it — evaluation "
        "is `model/licensed`'s contract, and richer window predicates arrive as natives "
        "behind solve(). The move is the same one `ledger@`'s falsification.expr makes: "
        "prose that can already fire.",
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
                          payload={"expr": "len(ctx('events')) >= 1",
                                   "note": "the claiming span encloses at least one raw "
                                           "exchange with the coin acceptor; sharpened to "
                                           "name the acceptor's endpoint when the window "
                                           "predicates land as natives"}),
                 ]),
            Node(id="push", kind="event-kind",
                 payload={"args": {}},
                 children=[
                     Node(id="push-license", kind="license",
                          payload={"expr": "len(ctx('events')) >= 1",
                                   "note": "the claiming span encloses at least one raw "
                                           "reading from the rotation sensor"}),
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


SEMANTIC_MODEL_PACKAGE = Package(
    name="semantic-model",
    version="0.1.0",
    description="The meta-vocabulary a semantic model is written in: state variables over "
                "finite domains, actions with guards and updates, an alphabet of observable "
                "events each anchored to evidence by a license, and invariants a checker can "
                "settle exhaustively. A model in these kinds is what the prover proves "
                "predicates over, once, and what the conformance checks confront every tape "
                "with, forever. The package carries exprs and evaluates nothing — meaning "
                "travels first, pinned, and the machinery is built against the digest. Its "
                "rules refuse the three ways a model quietly stops describing a system: no "
                "alphabet, unlicensed testimony, unobservable actions.",
    publisher="poietic.studio",
    vocabulary=VOCABULARY,
    rules=RULES,
    examples=EXAMPLES,
    counter_examples=COUNTER_EXAMPLES,
)
