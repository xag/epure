"""The conduct natives: each family's refuter fails its own law, and doors cut by name and by
argument.

The demonstrations in `epure.spec` prove each native answers what its contract says; what
they do not state is the cross-product — which OTHER laws a refuting tape trips. For the
presence laws the answer is none: a tape built to refute the frame is green under effect,
faithfulness and refusal, and that is what keeps four families four. For the value laws the
cross-product has implications that are true, not leaks — a repeat whose second read is wrong
is also a value disagreement — and the matrix states them exactly, so a new overlap is a diff
somebody reads.
"""

from __future__ import annotations

import epure.behavior  # noqa: F401 — registers the natives
import epure.conformance  # noqa: F401
import epure.prove  # noqa: F401
from quern import Node, Quern, Rule, run_rules

from epure import spec
from epure.behavior import (agrees, checkable, commute, constructible, door, durable, effect,
                            faithful, frame, last_write, refusal, same_story, twice, undo)
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
    assert len(got.notes) == 1 and "unwitnessed" in got.notes[0]


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
        Rule(name="twice-is-once", kind="session",
             expr="solve('conduct/twice', self, 'model') == 0"),
    ])
    tree.root.children = [spec.cloakroom(), spec.OVERREACH.model_copy(deep=True)]
    verdicts = {r.rule: r.ok for r in run_rules(tree)}
    assert verdicts == {"effects-show": True, "frame-holds": False, "twice-is-once": True}


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
        _scenario({"seq": 1, "fn": "cloakroom", "kwargs": {}, "events": list(spec.DEPOSIT)}),
        _scenario({"seq": 2, "fn": "cloakroom", "kwargs": {},
                   "events": [spec._read({"coat": "red"})]}),
    ])
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape]
    got = effect(tree, "visit", "model")
    assert got.violations == 0 and not got.notes


def test_a_read_before_the_act_shows_nothing():
    """Positions, not mere presence: the same read placed BEFORE the deposit is no witness."""
    tape = Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": 1, "fn": "cloakroom", "kwargs": {},
                   "events": [spec._read({"coat": "red"}), *spec.DEPOSIT]}),
    ])
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape]
    got = effect(tree, "visit", "model")
    assert got.violations == 0 and len(got.notes) == 1


# --- the model-based native ------------------------------------------------------------


def test_agrees_names_the_variable_the_update_and_both_worlds():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.TAG_WRONG.model_copy(deep=True)]
    (why,) = agrees(tree, "visit", "model").diagnostics
    assert "updates 'tag' to 'red' from the projected world" in why
    assert "the world shows 'blue' after" in why


def test_agrees_holds_the_frame_by_value():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.BYSTANDER_MOVED.model_copy(deep=True)]
    (why,) = agrees(tree, "visit", "model").diagnostics
    assert "does not update 'tag'" in why and "moved from 'red' to 'blue'" in why


def test_agrees_refuses_a_projection_outside_the_domain():
    tape = Node(id="visit", kind="session", links={"model": ["cloakroom"]}, children=[
        _scenario({"seq": 1, "fn": "cloakroom", "kwargs": {},
                   "events": [*spec.EMPTY, *spec.DEPOSIT, *spec.world("red", None, None),
                              *spec.TAG_RED, *spec.world("red", "green", None)]}),
    ])
    tree = Quern()
    tree.root.children = [spec.cloakroom(), tape]
    got = agrees(tree, "visit", "model")
    assert got.violations == 1 and "outside its domain" in got.diagnostics[0]


# the culprit rule: one row per (derived, declared, wrote, clock) profile the cloakroom can
# witness, and the facts printed beside the name so a wrong attribution can be argued with
CULPRITS = {
    "TAG_UNWRITTEN": "app",
    "DEPOSIT_TAGGED_TOO": "model",
    "SIGN_UNDER_THE_CLOCK": "harness",
    "SIGN_DARK_AT_CLOSING": "model",
    "SHELVED_OFF_THE_HOOK": "model",
    "BYSTANDER_MOVED": "harness",
    "TAG_WRONG": "unnamed",
    "SIGN_WRONG": "unnamed",
    "WORLD_LOST": "unnamed",
}


def test_every_red_under_agrees_names_its_culprit():
    for name, who in CULPRITS.items():
        tree = Quern()
        tree.root.children = [spec.cloakroom(), getattr(spec, name).model_copy(deep=True)]
        got = agrees(tree, "visit", "model")
        assert got.violations == 1, (name, got.diagnostics)
        assert got.culprits == [who], (name, got.culprits, got.diagnostics)
        assert f"culprit: {who} [" in got.diagnostics[0], got.diagnostics[0]


def test_culprits_walk_in_step_with_diagnostics():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.AGREES.model_copy(deep=True)]
    got = agrees(tree, "visit", "model")
    assert got.violations == 0 and got.culprits == []


def test_agrees_is_a_note_when_nothing_projects():
    tree = Quern()
    tree.root.children = [spec.turnstile(), spec.LAWFUL.model_copy(deep=True)]
    got = agrees(tree, "session", "model")
    assert got.violations == 0 and any("projects no state-var" in n for n in got.notes)


# --- the two-stretch natives: each refuter red under its own law, and the implications ---

STRETCH = {"agrees": agrees, "twice": twice, "last-write": last_write, "commute": commute,
           "undo": undo, "durable": durable, "same-story": same_story,
           "constructible": constructible, "effect": effect}

# tape -> the laws red on it. The first named is the law the tape was built to refute; the
# rest are IMPLICATIONS, stated rather than hidden: a repeat whose second read is wrong is
# also a value disagreement and an effect not shown; residue after an undo is also a world
# the model cannot reach; a value that faded is also a bystander that moved.
RED_UNDER = {
    "TAGGED_TWICE": set(),
    "TAGGED_TWICE_MOVED": {"twice", "last-write", "agrees", "effect"},
    "DEPOSITED_TWICE": set(),
    "RETAGGED": set(),
    "RETAGGED_FIRST_STUCK": {"last-write", "agrees", "effect"},
    "COMMUTES": set(),
    "ORDER_MATTERED": {"commute", "agrees", "durable"},
    "UNDONE": set(),
    "UNDONE_WITH_RESIDUE": {"undo", "agrees", "constructible"},
    "LASTING": set(),
    "FADED": {"durable"},
    "SAME_STORY_TOLD": set(),
    "DIFFERENT_STORY": {"same-story", "agrees", "durable"},
    "UNREACHABLE": {"constructible", "agrees", "durable"},
}


def test_every_stretch_refuter_is_red_under_its_own_law_and_exactly_the_implied_ones():
    for name, expected in RED_UNDER.items():
        tree = Quern()
        tree.root.children = [spec.cloakroom(), getattr(spec, name).model_copy(deep=True)]
        red = {law for law, fn in STRETCH.items() if fn(tree, "visit", "model").violations}
        assert red == expected, f"{name}: red under {sorted(red)}, expected {sorted(expected)}"


def test_a_stretch_law_judges_something_on_its_lawful_tape():
    """A zero that judged nothing is silence; each lawful tape must be a verdict."""
    for name, fn in (("TAGGED_TWICE", twice), ("RETAGGED", last_write), ("COMMUTES", commute),
                     ("UNDONE", undo), ("LASTING", durable), ("SAME_STORY_TOLD", same_story),
                     ("AGREES", constructible)):
        tree = Quern()
        tree.root.children = [spec.cloakroom(), getattr(spec, name).model_copy(deep=True)]
        got = fn(tree, "visit", "model")
        assert got.violations == 0 and got.judged >= 1, (name, got)


def test_the_stretch_diagnostics_name_both_stretches():
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.ORDER_MATTERED.model_copy(deep=True)]
    (why,) = commute(tree, "visit", "model").diagnostics
    assert "'tagging' then 'shelving' leaves" in why and "in the other order leave" in why
    tree.root.children = [spec.cloakroom(), spec.DIFFERENT_STORY.model_copy(deep=True)]
    (why,) = same_story(tree, "visit", "model").diagnostics
    assert "the same act from the same world at visit/call1/s0" in why


def test_projection_helpers_read_a_log():
    from epure.behavior import _count, _latest, _weekday
    log = {"a": {"chore_id": "bins", "kind": "done", "day": "2026-08-04"},
           "b": {"chore_id": "bins", "kind": "skipped", "day": "2026-08-05"},
           "c": {"chore_id": "hoover", "kind": "done", "day": "2026-08-06"}}
    assert _count(log, "chore_id", "bins") == 2
    assert _count(log, "chore_id", "bins", "kind", "done") == 1
    assert _latest(log, "day", "kind", "done") == "2026-08-06"
    assert _latest(log, "day", "chore_id", "wash") is None
    assert _weekday("2026-08-04") == 1.0 and _weekday(None, -1) == -1 and _weekday(None) is None
    # an epoch in milliseconds, as a number or as the string a store hands back: 2026-08-04
    # 08:00 UTC is a Tuesday, and 23:30 UTC the same day still is - the day is read in UTC
    assert _weekday(1785830400000) == 1.0 and _weekday("1785830400000") == 1.0
    assert _weekday(1785830400000 + 15.5 * 3600 * 1000) == 1.0
    assert _weekday("", -1) == -1
    assert _weekday("1785830400062.6995") == 1.0   # a clock that answers fractions, stored as text


def test_a_read_shows_the_json_text_a_write_carried_once_the_store_parsed_it():
    from epure.behavior import _subsumes
    assert _subsumes({"id": "p1", "rows": [{"id": "a"}]}, {"id": "p1", "rows": '[{"id": "a"}]'})
    assert not _subsumes({"id": "p1", "rows": [{"id": "b"}]}, {"id": "p1", "rows": '[{"id": "a"}]'})
    assert not _subsumes({"rows": [1]}, {"rows": "not json"})


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
    stray = spec.visit([*spec.DEPOSIT, spec._read({"coat": "red"}), spec._write("blue")])
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


# the presence laws' culprit rules (conduct@0.12.0): one row per profile of the facts the
# effect and frame natives hold, each a cloakroom tape built for that row
EFFECT_CULPRITS = {
    "WRONG_DOOR": "model",
    "NOOP": "harness",
    "NEVER_DEPOSITED": "app",
    "RETYPED": "harness",
    "OVERWRITTEN_BY_THE_SHELVING": "model",
    "SHOWN_OTHERWISE": "app",
    "LOST": "unnamed",
    "RESTORED_BEHIND_THE_RECLAIM": "model",
    "RESIDUE": "app",
}
FRAME_CULPRITS = {
    "TAGGED_THE_HOOK": "model",
    "TAGGED_ANOTHER_HOOK": "app",
    "OVERREACH": "unnamed",
}


def _one_red(native, name):
    tree = Quern()
    tree.root.children = [spec.cloakroom(), getattr(spec, name).model_copy(deep=True)]
    got = native(tree, "visit", "model")
    assert got.violations == 1, (name, got.diagnostics)
    return got


def test_every_red_under_effect_names_its_culprit():
    from epure.behavior import effect
    for name, who in EFFECT_CULPRITS.items():
        got = _one_red(effect, name)
        assert got.culprits == [who], (name, got.culprits, got.diagnostics)
        assert f"culprit: {who} [" in got.diagnostics[0], got.diagnostics[0]


def test_every_red_under_frame_names_its_culprit():
    from epure.behavior import frame
    for name, who in FRAME_CULPRITS.items():
        got = _one_red(frame, name)
        assert got.culprits == [who], (name, got.culprits, got.diagnostics)
        assert f"culprit: {who} [" in got.diagnostics[0], got.diagnostics[0]


def test_presence_culprits_walk_in_step_with_diagnostics():
    from epure.behavior import effect, frame
    tree = Quern()
    tree.root.children = [spec.cloakroom(), spec.RECLAIMED.model_copy(deep=True)]
    assert effect(tree, "visit", "model").culprits == []
    assert frame(tree, "visit", "model").culprits == []


def test_coerced_forgets_scalar_types_and_nothing_else():
    from epure.behavior import _coerced
    assert _coerced({"a": "5", "b": '["x"]'}, {"a": 5, "b": ["x"]})
    assert _coerced({"a": 5.0}, {"a": "5"})
    assert not _coerced({"a": "6"}, {"a": 5})
    assert not _coerced({"a": "red"}, {"a": "blue"})
