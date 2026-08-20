"""The conduct natives: each family's refuter fails its own law alone, and doors cut by name
and by argument.

The demonstrations in `epure.spec` prove each native answers what its contract says; what
they do not state is the cross-product — that the tape built to refute the frame law is green
under effect, faithfulness and refusal. A refuter that trips two laws is two laws that cannot
be told apart, and the whole point of a census of families is that they can. The matrix is
the test.
"""

from __future__ import annotations

import epure.behavior  # noqa: F401 — registers the natives
import epure.conformance  # noqa: F401
import epure.prove  # noqa: F401
from quern import Node, Quern, Rule, run_rules

from epure import spec
from epure.behavior import agrees, checkable, door, effect, faithful, frame, refusal
from epure.tape import _scenario

CHECKS = {"effect": effect, "faithful": faithful, "frame": frame, "refusal": refusal}

# tape -> the one family it refutes (None: lawful under all four)
REFUTERS = {
    "SHOWN": None, "UNREAD": None, "RECLAIMED": None, "REFUSED_CLEAN": None,
    "LOST": "effect", "NOOP": "effect", "RESIDUE": "effect",
    "SWAPPED": "faithful",
    "OVERREACH": "frame",
    "HALF_DONE": "refusal",
}


def _judge(tape: Node) -> dict[str, int]:
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape.model_copy(deep=True)]
    return {name: fn(tree, "visit", "model").violations for name, fn in CHECKS.items()}


def test_every_refuter_fails_exactly_its_own_family():
    for name, family in REFUTERS.items():
        verdict = _judge(getattr(spec, name))
        red = {k for k, v in verdict.items() if v}
        assert red == ({family} if family else set()), f"{name}: {verdict}"


def test_silence_is_a_note_not_a_verdict():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.UNREAD.model_copy(deep=True)]
    got = effect(tree, "visit", "model")
    assert got.violations == 0
    assert len(got.notes) == 2 and all("unwitnessed" in n for n in got.notes)


def test_the_diagnostic_names_the_act_and_the_law():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.LOST.model_copy(deep=True)]
    (why,) = effect(tree, "visit", "model").diagnostics
    assert why.startswith("visit/call1/s0: 'deposit' (check-coat) declares creates 'held'")
    assert "none returns what the 1 write(s) carried" in why


def test_the_natives_answer_in_the_rule_language():
    tree = Quern(rules=[
        Rule(name="effects-show", kind="session",
             expr="solve('conduct/effect', self, 'model') == 0"),
        Rule(name="frame-holds", kind="session",
             expr="solve('conduct/frame', self, 'model') == 0"),
    ])
    tree.root.children = [spec.cloakroom(), spec.OVERREACH.model_copy(deep=True)]
    verdicts = {r.rule: r.ok for r in run_rules(tree)}
    assert verdicts == {"effects-show": True, "frame-holds": False}


# --- doors -----------------------------------------------------------------------------


PUT = {"k": "fx", "fn": "app.storage.put_field", "args": [],
       "kwargs": {"path": "h/1/board/log", "field": "done.c_1", "value": {"id": "c_1"}},
       "res": None}


def test_a_door_cuts_by_name():
    assert door("app.storage.put*")(PUT)
    assert not door("app.storage.get")(PUT)


def test_a_door_cuts_by_argument_when_told_to():
    assert door({"event": "app.storage.put_field", "where": {"field": "done.*"}})(PUT)
    assert not door({"event": "app.storage.put_field", "where": {"field": "chores.*"}})(PUT)
    assert not door({"event": "app.storage.put_field", "where": {"missing": "*"}})(PUT)


def test_a_door_reaches_positional_arguments_by_index():
    ev = {"k": "fx", "fn": "hook.delete", "args": ["hooks/7"], "kwargs": {}, "res": None}
    assert door({"event": "hook.delete", "where": {"0": "hooks/*"}})(ev)
    assert not door({"event": "hook.delete", "where": {"1": "*"}})(ev)


# --- the model-level check -------------------------------------------------------------


def test_checkable_names_what_no_tape_could_witness():
    tree = Quern()
    tree.root.children = [spec.turnstile()]
    got = checkable(tree, "turnstile")
    assert got.violations == 2
    assert all("no `via` door" in d and "no `shown_by` door" in d for d in got.diagnostics)


def test_checkable_refuses_an_entity_that_is_no_state_var():
    model = spec.cloakroom()
    action = next(c for c in model.children if c.id == "check-coat")
    creates = next(c for c in action.children if c.kind == "creates")
    creates.payload = {**creates.payload, "entity": "ticket"}
    tree = Quern()
    tree.root.children = [model]
    (why,) = checkable(tree, "cloakroom").diagnostics
    assert "entity 'ticket' is no state-var" in why


# --- after, across calls ---------------------------------------------------------------


def test_a_read_in_a_later_call_shows_an_effect_of_an_earlier_one():
    """One recording is one accumulating world: the hook is read back in the next call."""
    tape = Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": 1, "fn": "cloakroom", "kwargs": {},
                   "events": spec._act("deposit", spec.RED, spec._write("red"),
                                       spec._tick(1))}),
        _scenario({"seq": 2, "fn": "cloakroom", "kwargs": {},
                   "events": [spec._read({"coat": "red"}), spec._count(1)]}),
    ])
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape]
    got = effect(tree, "visit", "model")
    assert got.violations == 0 and not got.notes


def test_a_read_before_the_act_shows_nothing():
    """Positions, not mere presence: the same read placed BEFORE the deposit is no witness."""
    tape = Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": 1, "fn": "cloakroom", "kwargs": {},
                   "events": [spec._read({"coat": "red"}),
                              *spec._act("deposit", spec.RED, spec._write("red"),
                                         spec._tick(1))]}),
    ])
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape]
    got = effect(tree, "visit", "model")
    assert got.violations == 0 and len(got.notes) == 2


# --- the model-based native ------------------------------------------------------------


def test_agrees_names_the_variable_the_update_and_both_worlds():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.WORLD_MISCOUNTED.model_copy(deep=True)]
    (why,) = agrees(tree, "visit", "model").diagnostics
    assert "updates 'tickets' to 1 from the projected world {'held': 0, 'tickets': 0}" in why
    assert "the world shows 2 after" in why


def test_agrees_holds_the_frame_by_value():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.BYSTANDER_MOVED.model_copy(deep=True)]
    (why,) = agrees(tree, "visit", "model").diagnostics
    assert "does not update 'tickets'" in why and "moved from 1 to 2" in why


def test_agrees_refuses_a_projection_outside_the_domain():
    tape = Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": 1, "fn": "cloakroom", "kwargs": {},
                   "events": [*spec._OPEN,
                              *spec._act("deposit", spec.RED, spec._write("red"), spec._tick(1)),
                              spec._read({"coat": "red"}), spec._count(9)]}),
    ])
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape]
    got = agrees(tree, "visit", "model")
    assert got.violations == 1 and "outside its domain" in got.diagnostics[0]


def test_agrees_is_a_note_when_nothing_projects():
    tree = Quern()
    tree.root.children = [spec.turnstile(), spec.LAWFUL.model_copy(deep=True)]
    got = agrees(tree, "session", "model")
    assert got.violations == 0 and "projects no state-var" in got.notes[0]


# --- the call is an act ----------------------------------------------------------------


def _cloakroom_with_the_call_declared() -> Node:
    """The tool the tapes record is `cloakroom`; the model names it, binds it to a no-op
    action with an empty boundary: the call itself writes nothing outside its acts."""
    model = spec.cloakroom()
    model.children += [
        Node(id="cloakroom", kind="event-kind", payload={"args": {}},
             children=[Node(id="cloakroom-license", kind="license",
                            payload={"expr": "len(evidence('*')) >= 0",
                                     "note": "the call record is its own evidence"})]),
        Node(id="visit-cloakroom", kind="action", payload={"updates": [], "args": {}},
             children=[Node(id="visit-cloakroom-witness", kind="observation",
                            payload={"event": "cloakroom"}),
                       Node(id="visit-cloakroom-touches", kind="touches",
                            payload={"only": [], "via": []})]),
    ]
    return model


def test_a_write_outside_every_span_answers_to_the_call():
    """The tool's own write — the one totality used to be the only check to see."""
    stray = spec.visit([*spec._act("deposit", spec.RED, spec._write("red"), spec._tick(1)),
                        spec._read({"coat": "red"}), spec._write("blue")])
    tree = Quern()
    tree.root.children = [_cloakroom_with_the_call_declared(), stray]
    (why,) = frame(tree, "visit", "model").diagnostics
    assert why.startswith("visit/call1: 'cloakroom' (visit-cloakroom) writes through 'hook.write'")


def test_a_write_inside_a_declared_span_is_that_spans_not_the_calls():
    tree = Quern()
    tree.root.children = [_cloakroom_with_the_call_declared(), spec.SHOWN.model_copy(deep=True)]
    assert frame(tree, "visit", "model").violations == 0


def test_a_failed_call_that_wrote_is_a_refusal():
    tape = Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": 1, "fn": "cloakroom", "kwargs": {}, "error": "boom",
                   "events": [spec._write("red")]})])
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape]
    (why,) = refusal(tree, "visit", "model").diagnostics
    assert "the call 'cloakroom' failed and still wrote through ['hook.write']" in why
