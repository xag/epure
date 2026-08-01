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
