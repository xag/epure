"""What the four semantic-model contracts must answer, and for which scenarios.

`model/prove` establishes what the model promises; `model/licensed`, `model/total` and
`model/refines` establish that a recorded run is a behaviour of it. All four run outside
the sandbox, on the host's own clock, and a rule reaches them with
`solve('model/<check>', self, 'model')`. Prose said what they do; nothing said it twice
in a form that could disagree with the code. This is that second saying, and quern's
publish gate refuses `semantic-model` if any of it stops holding — here at publish, and
again on every consumer's machine at sync.

Written as SCENARIOS rather than coverage. The cases worth stating are the ones where a
wrong answer is still a plausible answer: a tape that is licensed but does not refine, a
span nested inside another (decomposition, not a second transition), a raw event that no
span encloses. Each says which case it is, so this is also the record of what was
anticipated — and the next reader can see what was not.

The model under test is the package's own published turnstile, not a fixture invented
here: the checker is demonstrated against the exact model every consumer reads first.
"""

from __future__ import annotations

from typing import Any

from quern.tree import Demonstration, Node

from .package import EXAMPLES


def turnstile() -> Node:
    return EXAMPLES[0].model_copy(deep=True)


def turnstile_with_false_invariant() -> Node:
    """The same model, its one invariant weakened until the machine refutes it: entries
    are unbounded by construction, so `entries <= 1` cannot survive the walk."""
    model = turnstile()
    for child in model.children:
        if child.id == "no-free-entry":
            child.payload = {**child.payload, "expr": "entries <= 1"}
    return model


# --- recorded runs, in the shape the tape importer produces ---------------------------
#
# Literal nodes rather than an imported tape: a demonstration stages data, and a spec that
# had to read a file to state its own case would be untestable anywhere the file is not.

FX_COIN: dict[str, Any] = {"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {},
                           "res": 1}
FX_PUSH: dict[str, Any] = {"k": "fx", "fn": "sensor.read", "args": [], "kwargs": {},
                           "res": 1}


def span(id: str, kind: str, events: list, children: list | None = None) -> Node:
    return Node(id=id, kind=kind,
                payload={"data": {}, "outcome": "ok", "events": list(events)},
                children=list(children or []))


def session(*spans: Node, raw: list | None = None) -> Node:
    """One recorded call, linked to the model it claims to be a behaviour of."""
    return Node(id="session", kind="session", links={"model": ["turnstile"]}, children=[
        Node(id="call1", kind="scenario", name="ride",
             payload={"seq": 1, "ts": "t", "ms": 1, "events": list(raw or [])},
             children=list(spans))])


LAWFUL = session(span("s0", "coin", [FX_COIN]), span("s1", "push", [FX_PUSH]))
BACKWARDS = session(span("s0", "push", [FX_PUSH]), span("s1", "coin", [FX_COIN]))
EMPTY_COIN = session(span("s0", "coin", []), span("s1", "push", [FX_PUSH]))
UNKNOWN = session(span("s0", "jump", []))
ORPHAN = session(span("s0", "coin", [FX_COIN]), span("s1", "push", [FX_PUSH]),
                 raw=[{"k": "now", "v": "t"}])
NESTED = session(
    span("s0", "coin", [FX_COIN], children=[span("s0", "coin", [FX_COIN])]),
    span("s1", "push", [FX_PUSH]))


def d(contract: str, nodes: list[Node], args: list, because: str, **expect):
    return Demonstration(contract=f"model/{contract}", nodes=nodes, args=args,
                         because=because, **expect)


def judged(nodes_session: Node) -> list[Node]:
    """A tape is judged against a model, so both have to be standing."""
    return [turnstile(), nodes_session]


# --- model/prove: what the model promises ----------------------------------------------

PROVE = [
    d("prove", [turnstile()], ["turnstile"], expect=0,
      because="the published turnstile proves: no reachable state admits a free entry"),
    d("prove", [turnstile_with_false_invariant()], ["turnstile"], expect=1,
      because="an invariant the machine refutes is counted, not raised — a rule wants "
              "`== 0` and a diagnostic wants to know how many"),
    d("prove", [LAWFUL], ["session"], expect_error="not a model",
      because="model/prove proves models: pointed at a recorded run it refuses, rather "
              "than answering 0 for a thing it never examined"),
    d("prove", [turnstile()], ["ghost"], expect_error="no node at",
      because="a model that is not there is refused, never answered 0"),
]


# --- model/licensed: testimony is justified by evidence ---------------------------------

LICENSED = [
    d("licensed", judged(LAWFUL), ["session", "model"], expect=0,
      because="every span's claim is convicted by a call beneath it that could have made "
              "it true"),
    d("licensed", judged(EMPTY_COIN), ["session", "model"], expect=1,
      because="a span claiming to have taken a coin with nothing under it that touches "
              "the acceptor — testimony with no evidence, which is the failure a tape "
              "full of green spans is least likely to show you"),
    d("licensed", judged(UNKNOWN), ["session", "model"], expect=1,
      because="a span the model has no license for at all is unlicensed by definition, "
              "not ignored"),
]


# --- model/total: no raw event escapes semantics ----------------------------------------

TOTAL = [
    d("total", judged(LAWFUL), ["session", "model"], expect=0,
      because="every boundary exchange in the run sits inside some span"),
    d("total", judged(ORPHAN), ["session", "model"], expect=1,
      because="a raw event no span encloses: the system did something its own testimony "
              "does not account for. Licensing and refinement both stay green here, so "
              "this is the only check that can see it"),
]


# --- model/refines: the recorded run is a behaviour of the model -------------------------

REFINES = [
    d("refines", judged(LAWFUL), ["session", "model"], expect=0,
      because="coin then push is a run the machine can make"),
    d("refines", judged(BACKWARDS), ["session", "model"], expect=1,
      because="a push against a locked turnstile: the guard is false in the state the "
              "run had actually reached"),
    d("refines", judged(UNKNOWN), ["session", "model"], expect=1,
      because="a span that is testimony to no action of the model is a divergence, not "
              "a span to skip over"),
    d("refines", judged(NESTED), ["session", "model"], expect=0,
      because="a coin span nested INSIDE another is decomposition, not a second "
              "transition. A checker that flattened the tree would read coin, coin and "
              "refuse the second against an already-unlocked turnstile — the subtlest "
              "wrong answer here, and the one that would look like a real defect"),
    d("refines", judged(EMPTY_COIN), ["session", "model"], expect=0,
      because="the unlicensed tape still refines: licensing asks whether testimony is "
              "justified, refinement asks whether the sequence is possible, and a run "
              "can fail one while passing the other"),
]


SEMANTIC_MODEL_SPEC = {
    "model/prove": PROVE,
    "model/licensed": LICENSED,
    "model/total": TOTAL,
    "model/refines": REFINES,
}


# =========================================================================================
# The conduct contracts (conduct@0.2.0, natives in `epure.behavior`): what each behavior
# law answers, on the cloakroom — the published model that declares doors. The recorded
# runs below are built THROUGH the importer (`epure.tape._scenario`) from literal call
# records, so the positions the checks reason about are the ones a real tape would carry,
# not ones a spec hand-typed to suit itself. Each family's refuting tape fails that family
# alone: the lawful tape is green under all four tape-level checks, and every red tape
# differs from it by exactly the one thing its law forbids.
# =========================================================================================


def cloakroom() -> Node:
    return EXAMPLES[1].model_copy(deep=True)


def _sem(name: str, phase: str, sid: int, data: dict | None = None,
         outcome: str | None = None) -> dict[str, Any]:
    ev: dict[str, Any] = {"k": "sem", "name": name, "phase": phase, "sid": sid}
    if data is not None:
        ev["data"] = data
    if outcome is not None:
        ev["outcome"] = outcome
    return ev


def _write(coat: str) -> dict[str, Any]:
    return {"k": "fx", "fn": "hook.write", "args": [{"coat": coat}], "kwargs": {},
            "res": None}


def _read(res: Any) -> dict[str, Any]:
    return {"k": "fx", "fn": "hook.read", "args": [], "kwargs": {}, "res": res}


_REMOVE: dict[str, Any] = {"k": "fx", "fn": "hook.delete", "args": ["hook"], "kwargs": {},
                           "res": None}


def _tick(n: int) -> dict[str, Any]:
    """The ticket counter moves: the deposit's second write."""
    return {"k": "fx", "fn": "counter.write", "args": [{"n": n}], "kwargs": {}, "res": None}


def _count(n: int) -> dict[str, Any]:
    return {"k": "fx", "fn": "counter.read", "args": [], "kwargs": {}, "res": {"n": n}}


def _act(name: str, data: dict, *events: dict, outcome: str = "ok") -> list[dict]:
    """One span with its enclosed raw events, as the tape would carry them."""
    return [_sem(name, "begin", 1, data), *events, _sem(name, "end", 1, outcome=outcome)]


def visit(*calls: list[dict]) -> Node:
    """A recorded visit to the cloakroom: each call a list of tape events, in order."""
    from .tape import _scenario

    return Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": i + 1, "fn": "cloakroom", "kwargs": {}, "events": events})
        for i, events in enumerate(calls)])


RED = {"coat": "red"}

SHOWN = visit([*_act("deposit", RED, _write("red"), _tick(1)), _read({"coat": "red"})])
LOST = visit([*_act("deposit", RED, _write("red"), _tick(1)), _read(None)])
NOOP = visit([*_act("deposit", RED), _read({"coat": "red"})])
UNREAD = visit([*_act("deposit", RED, _write("red"), _tick(1))])
SWAPPED = visit([*_act("deposit", RED, _write("blue"), _tick(1)), _read({"coat": "blue"})])
RECLAIMED = visit([*_act("deposit", RED, _write("red"), _tick(1)), _read({"coat": "red"})],
                  [*_act("reclaim", {}, _REMOVE), _read(None)])
RESIDUE = visit([*_act("deposit", RED, _write("red"), _tick(1)), _read({"coat": "red"})],
                [*_act("reclaim", {}, _REMOVE), _read({"coat": "red"})])
OVERREACH = visit([*_act("deposit", RED, _write("red"), _tick(1)), _read({"coat": "red"})],
                  [*_act("reclaim", {}, _REMOVE, _write("blue")), _read(None)])
HALF_DONE = visit([*_act("deposit", RED, _write("red"), _tick(1), outcome="error"),
                   _read(None)])
REFUSED_CLEAN = visit([*_act("deposit", RED, outcome="error"), _read(None)])

# --- the model-based tapes: the world read before and after, projected ------------------
#
# Every one opens with the world read (hook empty, counter at 0), so the abstraction function
# has a pre-world to apply the model's update to — Hughes's diagram needs both corners.

_OPEN = [_read(None), _count(0)]
AGREES = visit([*_OPEN, *_act("deposit", RED, _write("red"), _tick(1)),
                _read({"coat": "red"}), _count(1)])
WORLD_LOST = visit([*_OPEN, *_act("deposit", RED, _write("red"), _tick(1)),
                    _read(None), _count(1)])
WORLD_MISCOUNTED = visit([*_OPEN, *_act("deposit", RED, _write("red"), _tick(1)),
                          _read({"coat": "red"}), _count(2)])
BYSTANDER_MOVED = visit([*_OPEN, *_act("deposit", RED, _write("red"), _tick(1)),
                         _read({"coat": "red"}), _count(1)],
                        [*_act("reclaim", {}, _REMOVE), _read(None), _count(2)])
WORLD_UNOPENED = visit([*_act("deposit", RED, _write("red"), _tick(1)),
                        _read({"coat": "red"}), _count(1)])


def c(contract: str, nodes: list[Node], args: list, because: str, **expect):
    return Demonstration(contract=f"conduct/{contract}", nodes=nodes, args=args,
                         because=because, **expect)


def visited(tape: Node) -> list[Node]:
    return [cloakroom(), tape]


EFFECT = [
    c("effect", visited(SHOWN), ["visit", "model"], expect=0,
      because="the deposit wrote the coat and the hook reads it back afterwards — the "
              "postcondition's floor, held on the tape rather than in the automaton"),
    c("effect", visited(LOST), ["visit", "model"], expect=1,
      because="the deposit wrote and the read after it returns nothing: the act refined "
              "perfectly and the world lost the write — the failure no model check can see"),
    c("effect", visited(NOOP), ["visit", "model"], expect=2,
      because="a deposit span with no hook.write and no counter.write under it: two "
              "declared effects, neither materialized — verbs with nothing beneath them. "
              "Licensing convicts it too; this convicts it as effects that never happened, "
              "which is a different sentence"),
    c("effect", visited(UNREAD), ["visit", "model"], expect=0,
      because="written and never read back: not shown, and not convicted — a law is refuted "
              "by a read that disagrees, and silence is reported as a note, never as a pass "
              "dressed up or a violation invented"),
    c("effect", visited(RECLAIMED), ["visit", "model"], expect=0,
      because="deposit, read, reclaim, read nothing: the delete's inverted check holds"),
    c("effect", visited(RESIDUE), ["visit", "model"], expect=1,
      because="after the reclaim the hook still reads the red coat the deposit wrote — the "
              "removal did not remove, the inverted postcondition's one failure"),
    c("effect", [cloakroom(), Node(id="visit", kind="session")], ["visit", "model"],
      expect_error="links 'model' to 0",
      because="a tape naming no model is unjudged, never green"),
]

FAITHFUL = [
    c("faithful", visited(SHOWN), ["visit", "model"], expect=0,
      because="the span testifies coat=red and the write carried red"),
    c("faithful", visited(SWAPPED), ["visit", "model"], expect=1,
      because="the span testifies coat=red and the write carried blue: made from one value, "
              "written as another — the read after it shows blue, so conduct/effect stays "
              "green and only this law sees it"),
    c("faithful", visited(LOST), ["visit", "model"], expect=0,
      because="faithfulness is about the write and its inputs; that the world later lost "
              "it is conduct/effect's finding, not this one's"),
]

FRAME = [
    c("frame", visited(RECLAIMED), ["visit", "model"], expect=0,
      because="each act passes only through the doors it declared"),
    c("frame", visited(OVERREACH), ["visit", "model"], expect=1,
      because="the reclaim also wrote the hook: a door the model knows, outside the act's "
              "declared boundary — something moved that the act never claimed to touch"),
    c("frame", visited(NOOP), ["visit", "model"], expect=0,
      because="an act that wrote nothing at all moved nothing outside its frame, whatever "
              "else is wrong with it"),
]

REFUSAL = [
    c("refusal", visited(REFUSED_CLEAN), ["visit", "model"], expect=0,
      because="a deposit that failed and wrote nothing: the refusal changed nothing"),
    c("refusal", visited(HALF_DONE), ["visit", "model"], expect=1,
      because="a deposit that failed AFTER writing the hook: the error path half-did the "
              "thing, which is the least-tested path and the most likely to"),
    c("refusal", visited(SHOWN), ["visit", "model"], expect=0,
      because="an act that succeeded is not a refusal; its writes are the effect law's"),
]

CHECKABLE = [
    c("checkable", [cloakroom()], ["cloakroom"], expect=0,
      because="every effect of the cloakroom names a state-var and both doors"),
    c("checkable", [turnstile()], ["turnstile"], expect=2,
      because="the turnstile's two mutates name no doors: a hardware model with no store "
              "to read back from, and the other laws silently skip exactly what this one "
              "counts"),
    c("checkable", visited(SHOWN), ["visit"], expect_error="not a model",
      because="pointed at a tape it refuses: declarations live on the model"),
]

AGREES_SPEC = [
    c("agrees", visited(AGREES), ["visit", "model"], expect=0,
      because="hook empty and counter 0 before; the deposit's own updates say held 1, "
              "tickets 1; the reads after project exactly that — Hoare's diagram commutes "
              "on a tape"),
    c("agrees", visited(WORLD_LOST), ["visit", "model"], expect=1,
      because="the hook reads empty after the deposit: the model says held = 1 and the "
              "world shows 0 — the effect law in its VALUE form, not a presence"),
    c("agrees", visited(WORLD_MISCOUNTED), ["visit", "model"], expect=1,
      because="the counter reads 2 after one deposit from 0: the model's update is "
              "tickets + 1 and the world disagrees — a wrong value, which no door could see"),
    c("agrees", visited(BYSTANDER_MOVED), ["visit", "model"], expect=1,
      because="the reclaim does not update tickets, and the counter moved from 1 to 2 "
              "across it: the frame law in its VALUE form — «a value is the same if it "
              "wasn't changed», read back and compared"),
    c("agrees", visited(WORLD_UNOPENED), ["visit", "model"], expect=0,
      because="no read before the act: the pre-world is unknown, so nothing is computed "
              "and nothing is convicted — noted, never counted"),
    c("agrees", judged(LAWFUL), ["session", "model"], expect=0,
      because="the turnstile projects nothing: a model without projections has nothing "
              "to agree on, and says so in a note rather than passing in silence"),
]

CONDUCT_SPEC = {
    "conduct/effect": EFFECT,
    "conduct/faithful": FAITHFUL,
    "conduct/frame": FRAME,
    "conduct/refusal": REFUSAL,
    "conduct/checkable": CHECKABLE,
    "conduct/agrees": AGREES_SPEC,
}
