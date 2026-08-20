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
    """A span as the importer would carry it - with positions, since licenses may now say
    'before' and 'after': the span begins at 0, its own events follow it, its children
    come after them, and it ends past everything."""
    kids = list(children or [])
    return Node(id=id, kind=kind,
                payload={"data": {}, "outcome": "ok", "events": list(events),
                         "pos": list(range(1, len(events) + 1)), "at": 0,
                         "to": len(events) + 10 * (len(kids) + 1)},
                children=kids)


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


def _counted(read_first: bool) -> Node:
    """A push whose passage-counted point sits after (lawful) or before (not) the sensor read:
    the events are staged through the importer so the point has a position."""
    from .tape import _scenario

    point = {"k": "sem", "name": "passage-counted", "phase": "point", "sid": 2}
    events = [{"k": "sem", "name": "coin", "phase": "begin", "sid": 1}, FX_COIN,
              {"k": "sem", "name": "coin", "phase": "end", "sid": 1, "outcome": "ok"},
              {"k": "sem", "name": "push", "phase": "begin", "sid": 3},
              *([FX_PUSH, point] if read_first else [point, FX_PUSH]),
              {"k": "sem", "name": "push", "phase": "end", "sid": 3, "outcome": "ok"}]
    return Node(id="session", kind="session", links={"model": ["turnstile"]}, children=[
        _scenario({"seq": 1, "fn": "ride", "kwargs": {}, "events": events})])


COUNTED_AFTER_THE_READ = _counted(read_first=True)
COUNTED_BEFORE_THE_READ = _counted(read_first=False)


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
    d("licensed", judged(COUNTED_AFTER_THE_READ), ["session", "model"], expect=0,
      because="the passage is counted after the sensor read it: the point's license names "
              "the read along its lineage and says it came before — satisfied"),
    d("licensed", judged(COUNTED_BEFORE_THE_READ), ["session", "model"], expect=1,
      because="the same point placed before the sensor read: the evidence is there, in "
              "scope, and in the wrong direction — a count that preceded what it counted, "
              "which a direction-blind license could not tell from the lawful tape"),
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
# The conduct contracts (conduct@, natives in `epure.behavior`): what each behavior law
# answers, on the cloakroom — the published model that declares doors and projections. The
# recorded runs below are built THROUGH the importer (`epure.tape._scenario`) from literal
# call records, so the positions the checks reason about are the ones a real tape would
# carry, not ones a spec hand-typed to suit itself. Each family's refuting tape fails that
# family alone: the lawful tapes are green under every tape-level check, and every red tape
# differs from a lawful one by exactly the one thing its law forbids.
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


def _fx(fn: str, args: list | None = None, res: Any = None) -> dict[str, Any]:
    return {"k": "fx", "fn": fn, "args": list(args or []), "kwargs": {}, "res": res}


def _write(coat: str) -> dict[str, Any]:
    return _fx("hook.write", [{"coat": coat}])


def _read(res: Any) -> dict[str, Any]:
    return _fx("hook.read", [], res)


def _tag_write(color: str) -> dict[str, Any]:
    return _fx("tag.write", [{"color": color}])


def _tag_read(color: str | None) -> dict[str, Any]:
    return _fx("tag.read", [], {"color": color} if color else {})


def _shelf_write(level: str) -> dict[str, Any]:
    return _fx("shelf.write", [{"level": level}])


def _shelf_read(level: str | None) -> dict[str, Any]:
    return _fx("shelf.read", [], {"level": level} if level else {})


_REMOVE: dict[str, Any] = _fx("hook.delete", ["hook"])


def _rev_write(n: int) -> dict[str, Any]:
    return _fx("register.write", [{"rev": n}])


def _rev_read(n: int) -> dict[str, Any]:
    return _fx("register.read", [], {"rev": n})


def _act(name: str, data: dict, *events: dict, outcome: str = "ok") -> list[dict]:
    """One span with its enclosed raw events, as the tape would carry them."""
    return [_sem(name, "begin", 1, data), *events, _sem(name, "end", 1, outcome=outcome)]


def visit(*calls: list[dict]) -> Node:
    """A recorded visit to the cloakroom: each call a list of tape events, in order."""
    from .tape import _scenario

    return Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": i + 1, "fn": "cloakroom", "kwargs": {}, "events": events})
        for i, events in enumerate(calls)])


def world(coat: Any, tag: str | None, shelf: str | None, rev: int | None = None) -> list[dict]:
    """The reads that project the whole world: hook, tag, shelf — and the register's stamp
    when the tape is about it."""
    out = [_read({"coat": coat} if coat else None), _tag_read(tag), _shelf_read(shelf)]
    if rev is not None:
        out.append(_rev_read(rev))
    return out


RED = {"coat": "red"}
EMPTY = world(None, None, None)
DEPOSIT = _act("deposit", RED, _write("red"))
TAG_RED = _act("tagging", {"color": "red"}, _tag_write("red"))
TAG_BLUE = _act("tagging", {"color": "blue"}, _tag_write("blue"))
SHELVE_HIGH = _act("shelving", {"level": "high"}, _shelf_write("high"))
RECLAIM = _act("reclaim", {}, _REMOVE)

# --- one act, by presence (effect, faithful, frame, refusal) ------------------------------

SHOWN = visit([*DEPOSIT, _read({"coat": "red"})])
LOST = visit([*DEPOSIT, _read(None)])
NOOP = visit([*_act("deposit", RED), _read({"coat": "red"})])
UNREAD = visit([*DEPOSIT])
SWAPPED = visit([*_act("deposit", RED, _write("blue")), _read({"coat": "blue"})])
RECLAIMED = visit([*DEPOSIT, _read({"coat": "red"})], [*RECLAIM, _read(None)])
RESIDUE = visit([*DEPOSIT, _read({"coat": "red"})], [*RECLAIM, _read({"coat": "red"})])
OVERREACH = visit([*DEPOSIT, _read({"coat": "red"})],
                  [*_act("reclaim", {}, _REMOVE, _write("blue")), _read(None)])
HALF_DONE = visit([*_act("deposit", RED, _write("red"), outcome="error"), _read(None)])
REFUSED_CLEAN = visit([*_act("deposit", RED, outcome="error"), _read(None)])

# --- one act, by value (agrees) -----------------------------------------------------------
#
# Every one opens with the world read, so the abstraction function has a pre-world to apply
# the model's update to — Hughes's diagram needs both corners.

AGREES = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                *TAG_RED, *world("red", "red", None)])
WORLD_LOST = visit([*EMPTY, *DEPOSIT, *world(None, None, None)])
TAG_WRONG = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                   *TAG_RED, *world("red", "blue", None)])
BYSTANDER_MOVED = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                         *TAG_RED, *world("red", "red", None),
                         *SHELVE_HIGH, *world("red", "blue", "high")])
WORLD_UNOPENED = visit([*DEPOSIT, *world("red", None, None)])

# --- two stretches (twice, last-write, commute, undo, durable, same-story, constructible) ---

TAGGED_TWICE = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                      *TAG_RED, *world("red", "red", None),
                      *TAG_RED, *world("red", "red", None)])
TAGGED_TWICE_MOVED = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                            *TAG_RED, *world("red", "red", None),
                            *TAG_RED, *world("red", "blue", None)])
DEPOSITED_TWICE = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                         *DEPOSIT, *world("red", None, None)])

RETAGGED = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                  *TAG_RED, *world("red", "red", None),
                  *TAG_BLUE, *world("red", "blue", None)])
RETAGGED_FIRST_STUCK = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                              *TAG_RED, *world("red", "red", None),
                              *TAG_BLUE, *world("red", "red", None)])

_BOTH_WAYS_OPEN = [*EMPTY, *DEPOSIT, *world("red", None, None)]
COMMUTES = visit([*_BOTH_WAYS_OPEN,
                  *TAG_RED, *world("red", "red", None),
                  *SHELVE_HIGH, *world("red", "red", "high"),
                  *RECLAIM, *EMPTY, *DEPOSIT, *world("red", None, None),
                  *SHELVE_HIGH, *world("red", None, "high"),
                  *TAG_RED, *world("red", "red", "high")])
ORDER_MATTERED = visit([*_BOTH_WAYS_OPEN,
                        *TAG_RED, *world("red", "red", None),
                        *SHELVE_HIGH, *world("red", "red", "high"),
                        *RECLAIM, *EMPTY, *DEPOSIT, *world("red", None, None),
                        *SHELVE_HIGH, *world("red", None, "high"),
                        *TAG_RED, *world("red", "red", "low")])

UNDONE = visit([*EMPTY, *DEPOSIT, *world("red", None, None), *RECLAIM, *EMPTY])
UNDONE_WITH_RESIDUE = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                             *RECLAIM, *world(None, "red", None)])

LASTING = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                 *TAG_RED, *world("red", "red", None), *world("red", "red", None),
                 *world("red", "red", None)])
FADED = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
               *TAG_RED, *world("red", "red", None), *world("red", "red", None),
               *world("red", None, None)])

SAME_STORY_TOLD = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                         *RECLAIM, *EMPTY, *DEPOSIT, *world("red", None, None)])
DIFFERENT_STORY = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                         *RECLAIM, *EMPTY, *DEPOSIT, *world("red", "blue", None)])

UNREACHABLE = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                     *TAG_RED, *world(None, "red", None)])

# --- merges, validators, conditional writes ----------------------------------------------


def _import(tag: str, shelf: str) -> list[dict]:
    return _act("importing", {"other_tag": tag, "other_shelf": shelf}, _rev_write(9))


def _retag(color: str, expected: int, *events: dict, outcome: str = "ok") -> list[dict]:
    return _act("retagging", {"color": color, "expected": expected}, _rev_read(expected if outcome == "ok" else 1), *events,
                outcome=outcome)


# a tagged red coat on the floor absorbs a register saying (none, high): the tag stands, the
# shelf is taken from the other
MERGED = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                *TAG_RED, *world("red", "red", None),
                *_import("none", "high"), *world("red", "red", "high")])
MERGE_TOOK_THE_RIGHT = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                              *TAG_RED, *world("red", "red", None),
                              *_import("blue", "high"), *world("red", "blue", "high")])
SELF_MERGED = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                     *TAG_RED, *world("red", "red", None),
                     *_import("red", "floor"), *world("red", "red", None)])
# (b then c) from a, and (b ⊔ c) from a: b = (none, high), c = (blue, low), b ⊔ c = (blue, high)
ASSOCIATIVE = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                     *_import("none", "high"), *world("red", None, "high"),
                     *_import("blue", "low"), *world("red", "blue", "high"),
                     *RECLAIM, *EMPTY, *DEPOSIT, *world("red", None, None),
                     *_import("blue", "high"), *world("red", "blue", "high")])
NOT_ASSOCIATIVE = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                         *_import("none", "high"), *world("red", None, "high"),
                         *_import("blue", "low"), *world("red", "blue", "high"),
                         *RECLAIM, *EMPTY, *DEPOSIT, *world("red", None, None),
                         *_import("blue", "high"), *world("red", "blue", "low")])

STAMPED = visit([*world(None, None, None, 0),
                 *_act("deposit", RED, _write("red"), _rev_write(1)), *world("red", None, None, 1),
                 *_act("tagging", {"color": "red"}, _tag_write("red"), _rev_write(2)),
                 *world("red", "red", None, 2)])
UNSTAMPED = visit([*world(None, None, None, 0),
                   *_act("deposit", RED, _write("red"), _rev_write(1)), *world("red", None, None, 1),
                   *_act("tagging", {"color": "red"}, _tag_write("red")),
                   *world("red", "red", None, 1)])

CONDITIONAL_MATCH = visit([*world(None, None, None, 0),
                           *_act("deposit", RED, _write("red"), _rev_write(1)),
                           *world("red", None, None, 1),
                           *_retag("blue", 1, _tag_write("blue"), _rev_write(2)),
                           *world("red", "blue", None, 2)])
CONDITIONAL_REFUSED = visit([*world(None, None, None, 0),
                             *_act("deposit", RED, _write("red"), _rev_write(1)),
                             *world("red", None, None, 1),
                             *_retag("blue", 7, outcome="error"),
                             *world("red", None, None, 1)])
CONDITIONAL_IGNORED = visit([*world(None, None, None, 0),
                             *_act("deposit", RED, _write("red"), _rev_write(1)),
                             *world("red", None, None, 1),
                             *_retag("blue", 7, _tag_write("blue"), _rev_write(2)),
                             *world("red", "blue", None, 2)])
CONDITIONAL_STUCK = visit([*world(None, None, None, 0),
                           *_act("deposit", RED, _write("red"), _rev_write(1)),
                           *world("red", None, None, 1),
                           *_act("retagging", {"color": "blue", "expected": 1}, _rev_read(1),
                                 outcome="error"),
                           *world("red", None, None, 1)])


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
    c("effect", visited(NOOP), ["visit", "model"], expect=1,
      because="a deposit span with no hook.write under it: a verb with nothing beneath it. "
              "Licensing convicts it too; this convicts it as an effect that never "
              "materialized, which is a different sentence"),
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
      because="hook empty before; the deposit's own update says held 1, the tag's says "
              "red; the reads after project exactly that — Hoare's diagram commutes on a tape"),
    c("agrees", visited(WORLD_LOST), ["visit", "model"], expect=1,
      because="the hook reads empty after the deposit: the model says held = 1 and the "
              "world shows 0 — the effect law in its VALUE form, not a presence"),
    c("agrees", visited(TAG_WRONG), ["visit", "model"], expect=1,
      because="tagged red, the ticket reads blue: the update is the argument and the world "
              "disagrees — a wrong value, which no door could see"),
    c("agrees", visited(BYSTANDER_MOVED), ["visit", "model"], expect=1,
      because="shelving does not update the tag, and the tag moved from red to blue across "
              "it: the frame law in its VALUE form — «a value is the same if it wasn't "
              "changed», read back and compared"),
    c("agrees", visited(WORLD_UNOPENED), ["visit", "model"], expect=0,
      because="no read before the act: the pre-world is unknown, so nothing is computed "
              "and nothing is convicted — noted, never counted"),
    c("agrees", judged(LAWFUL), ["session", "model"], expect=0,
      because="the turnstile projects nothing: a model without projections has nothing "
              "to agree on, and says so in a note rather than passing in silence"),
]

TWICE = [
    c("twice", visited(TAGGED_TWICE), ["visit", "model"], expect=0,
      because="tagged red twice: the guard admits the repeat (the coat is still on the "
              "hook) and the world after twice is the world after once"),
    c("twice", visited(TAGGED_TWICE_MOVED), ["visit", "model"], expect=1,
      because="the same repeat, and the second time the ticket reads blue — twice was not "
              "once, RFC 9110's idempotence broken by a read that disagrees"),
    c("twice", visited(DEPOSITED_TWICE), ["visit", "model"], expect=0,
      because="deposited twice: the guard refuses a second coat on an occupied hook, so "
              "the repeat is a refusal and not this law's — the model says which acts are "
              "idempotent, and a guard that refuses its own post-state exits the family"),
]

LAST_WRITE = [
    c("last-write", visited(RETAGGED), ["visit", "model"], expect=0,
      because="tagged red then blue: the tag is an overwrite, and the world shows blue"),
    c("last-write", visited(RETAGGED_FIRST_STUCK), ["visit", "model"], expect=1,
      because="tagged red then blue and the ticket still reads red: the first write won. "
              "Hughes's InsertInsert on one key, refuted"),
    c("last-write", visited(TAGGED_TWICE), ["visit", "model"], expect=0,
      because="the same value twice is a last write that happens to equal the first; the "
              "law holds trivially and is judged, not skipped"),
]

COMMUTE = [
    c("commute", visited(COMMUTES), ["visit", "model"], expect=0,
      because="tag then shelve, and later — from the same world, after a reclaim and a "
              "fresh deposit — shelve then tag: both orders leave the coat red and high"),
    c("commute", visited(ORDER_MATTERED), ["visit", "model"], expect=1,
      because="the reverse order leaves the shelf low: two writes the model declares "
              "independent turned out to interfere — InsertInsertWeak, refuted"),
    c("commute", visited(AGREES), ["visit", "model"], expect=0,
      because="one order only, no reverse on the tape: unwitnessed, noted, never counted"),
]

UNDO = [
    c("undo", visited(UNDONE), ["visit", "model"], expect=0,
      because="deposit then reclaim: the world after the reclaim is the world before the "
              "deposit — no residue, no bystander taken"),
    c("undo", visited(UNDONE_WITH_RESIDUE), ["visit", "model"], expect=1,
      because="the hook is empty again but the ticket still reads red: the delete unmade "
              "the coat and left the tag — residue, Hughes's DeleteInsert on one key"),
    c("undo", visited(TAGGED_TWICE), ["visit", "model"], expect=0,
      because="no delete on the tape: nothing to undo, nothing judged"),
]

DURABLE = [
    c("durable", visited(LASTING), ["visit", "model"], expect=0,
      because="tagged red and read three times after: red every time, with nothing in "
              "between declaring it changed"),
    c("durable", visited(FADED), ["visit", "model"], expect=1,
      because="tagged red, read red, then read as nothing — the effect faded with no act "
              "declaring it changed: a write that did not survive its writer"),
    c("durable", visited(AGREES), ["visit", "model"], expect=0,
      because="one read after each act: shown once, never re-read — unwitnessed beyond "
              "the first read, noted"),
]

SAME_STORY = [
    c("same-story", visited(SAME_STORY_TOLD), ["visit", "model"], expect=0,
      because="the same deposit, twice, from the same empty world — after a reclaim in "
              "between — shows the same world after"),
    c("same-story", visited(DIFFERENT_STORY), ["visit", "model"], expect=1,
      because="the second deposit from the same empty world shows a blue tag the first "
              "did not: an undeclared input — something the model does not know decided it"),
    c("same-story", visited(TAGGED_TWICE), ["visit", "model"], expect=0,
      because="the two taggings start from different worlds (none, then red): not the same "
              "state, so not this law's comparison"),
]

CONSTRUCTIBLE = [
    c("constructible", visited(AGREES), ["visit", "model"], expect=0,
      because="every world read off the tape — empty, a red coat, a red coat tagged red "
              "— is a state the model reaches from init"),
    c("constructible", visited(UNREACHABLE), ["visit", "model"], expect=1,
      because="after the tagging the hook reads empty and the tag reads red: a world the "
              "model cannot reach — no tag without a coat — which Hughes's "
              "InsertComplete asks of every tree"),
    c("constructible", visited(UNREAD), ["visit", "model"], expect=0,
      because="no world read at all: nothing to place, nothing judged"),
]

MERGE = [
    c("merge", visited(MERGED), ["visit", "model"], expect=0,
      because="a red-tagged coat on the floor absorbs a register saying (no tag, high): the "
              "tag stands, the shelf is taken — left-biased, Hughes's union"),
    c("merge", visited(MERGE_TOOK_THE_RIGHT), ["visit", "model"], expect=1,
      because="the same absorb with the other register saying blue, and the tag reads blue "
              "after: the right won where the left was present — UnionPost's left bias, "
              "refuted"),
    c("merge", visited(SELF_MERGED), ["visit", "model"], expect=0,
      because="a register absorbs a copy of itself and nothing moves — UnionUnionIdem"),
    c("merge", visited(ASSOCIATIVE), ["visit", "model"], expect=0,
      because="(none, high) then (blue, low) from a red coat, and their merge (blue, high) "
              "from the same red coat, leave the same world — UnionUnionAssoc on a tape"),
    c("merge", visited(NOT_ASSOCIATIVE), ["visit", "model"], expect=2,
      because="the one-step merge leaves the shelf low where the two steps left it high: "
              "not associative — and, because every variable projects, that same read is "
              "also a left-bias failure of the one-step act. Two counts for one fact, stated; "
              "the associativity count earns its own place where a projection is missing"),
]

STAMPED_SPEC = [
    c("stamped", visited(STAMPED), ["visit", "model"], expect=0,
      because="the register's rev moved with the deposit and with the tag — a strong "
              "validator: it changes whenever the representation does"),
    c("stamped", visited(UNSTAMPED), ["visit", "model"], expect=1,
      because="the tag moved and the rev still reads 1: a change that did not move the "
              "stamp, which is the one thing a strong validator may not do"),
    c("stamped", visited(AGREES), ["visit", "model"], expect=0,
      because="the register is never read on this tape: the stamp is unwitnessed, noted, "
              "not counted"),
]

CONDITIONAL_SPEC = [
    c("conditional", visited(CONDITIONAL_MATCH), ["visit", "model"], expect=0,
      because="handed rev 1, the world at rev 1: the retag proceeds and the tag reads blue "
              "— If-Match, satisfied"),
    c("conditional", visited(CONDITIONAL_REFUSED), ["visit", "model"], expect=0,
      because="handed rev 7, the world at rev 1: the retag refuses and writes nothing — 412 "
              "Precondition Failed, honoured"),
    c("conditional", visited(CONDITIONAL_IGNORED), ["visit", "model"], expect=1,
      because="handed rev 7, the world at rev 1, and the retag wrote anyway: a precondition "
              "that did not hold and a write that happened — the lost update"),
    c("conditional", visited(CONDITIONAL_STUCK), ["visit", "model"], expect=1,
      because="handed the current rev and refused: a match that did not proceed"),
]

def cloakroom_that_traps() -> Node:
    """The reclaim's guard demands an UNTAGGED coat, and nothing ever untags: a coat once
    tagged can never leave — the trap."""
    model = cloakroom()
    reclaim = next(c for c in model.children if c.id == "reclaim-coat")
    reclaim.payload = {**reclaim.payload, "guard": "held == 1 and tag == 'none'"}
    return model


PROMISED = [
    Demonstration(contract="model/promised", nodes=[cloakroom()], args=["cloakroom"], expect=0,
                  because="from every state with a coat on the hook, a reclaim is possible: "
                          "the promise can be kept from everywhere it is made"),
    Demonstration(contract="model/promised", nodes=[cloakroom_that_traps()], args=["cloakroom"],
                  expect=1,
                  because="a reclaim that demands an untagged coat, when nothing untags: "
                          "the tagged coat is a state the promise is made in and no action "
                          "leaves — the trap, with the shortest path into it, which no "
                          "invariant could see"),
    Demonstration(contract="model/promised", nodes=[turnstile()], args=["turnstile"], expect=0,
                  because="a model making no promise breaks none"),
]

KEPT = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
              *TAG_RED, *world("red", "red", None),
              *RECLAIM, *EMPTY])
BROKEN = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                *TAG_RED, *world("red", "red", None),
                *SHELVE_HIGH, *world("red", "red", "high"),
                *TAG_BLUE, *world("red", "blue", "high")])
STILL_OPEN = visit([*EMPTY, *DEPOSIT, *world("red", None, None),
                    *TAG_RED, *world("red", "red", None)])

EVENTUALLY = [
    c("eventually", visited(KEPT), ["visit", "model"], expect=0,
      because="the coat checked in is reclaimed two acts later: the promise kept within "
              "its horizon"),
    c("eventually", visited(BROKEN), ["visit", "model"], expect=1,
      because="three acts after the deposit the coat is still on the hook — tagged, "
              "shelved, retagged, never reclaimed: the promise broken within its horizon, "
              "Lamport's liveness refuted on a recording because the horizon was stated"),
    c("eventually", visited(STILL_OPEN), ["visit", "model"], expect=0,
      because="one act after the deposit the tape ends: the promise is open, not broken — "
              "noted, never counted"),
]


def cloakroom_with_a_stray_writer() -> Node:
    """The recorder knows a write function no action admits."""
    model = cloakroom()
    boundary = next(c for c in model.children if c.kind == "boundary")
    boundary.payload = {"writes": [*boundary.payload["writes"], "ledger.append"]}
    return model


DOORS = [
    c("doors", [cloakroom()], ["cloakroom"], expect=0,
      because="every write function the cloakroom's recorder declares is a door of some "
              "action: the frame's empty boundary means the whole state"),
    c("doors", [cloakroom_with_a_stray_writer()], ["cloakroom"], expect=1,
      because="the recorder also records ledger.append and no action admits it: a write the "
              "frame could never see, named by the census before any tape takes that path"),
    c("doors", [turnstile()], ["turnstile"], expect=0,
      because="the turnstile declares no boundary: noted, the frame holds declared doors "
              "only — not a violation, not a whole-state claim either"),
]

CONDUCT_SPEC = {
    "conduct/eventually": EVENTUALLY,
    "conduct/doors": DOORS,
    "conduct/merge": MERGE,
    "conduct/stamped": STAMPED_SPEC,
    "conduct/conditional": CONDITIONAL_SPEC,
    "conduct/effect": EFFECT,
    "conduct/faithful": FAITHFUL,
    "conduct/frame": FRAME,
    "conduct/refusal": REFUSAL,
    "conduct/checkable": CHECKABLE,
    "conduct/agrees": AGREES_SPEC,
    "conduct/twice": TWICE,
    "conduct/last-write": LAST_WRITE,
    "conduct/commute": COMMUTE,
    "conduct/undo": UNDO,
    "conduct/durable": DURABLE,
    "conduct/same-story": SAME_STORY,
    "conduct/constructible": CONSTRUCTIBLE,
}
