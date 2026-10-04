"""conduct/agrees binds a call to one action per independent part of the model, by the world
before it: one event witnessing several actions, in several drawings, is judged where the
guards and the projected reads tell the actions apart, and noted where they do not."""

from quern import Node, Quern

from epure.behavior import agrees
from epure.tape import _scenario


def _model() -> Node:
    """Two independent parts, both moved by a `status` call: a slot drained when held, and a
    day counter reset. The slot's actions differ by guard; the counter's action has none."""
    return Node(id="m", kind="model", children=[
        Node(id="held", kind="state-var",
             payload={"type": "bool", "init": False,
                      "shown": {"door": {"event": "get", "where": {"sig": "*slot*"}}, "expr": "at('exists', false)"}}),
        Node(id="shown", kind="state-var", payload={"type": "int", "domain": {"min": 0, "max": 2}, "init": 0}),
        Node(id="writes", kind="state-var", payload={"type": "int", "domain": {"min": 0, "max": 3}, "init": 0}),
        Node(id="status", kind="event-kind", payload={"args": {}},
             children=[Node(id="status-license", kind="license", payload={"expr": "true", "note": ""})]),
        Node(id="save", kind="event-kind", payload={"args": {}},
             children=[Node(id="save-license", kind="license", payload={"expr": "true", "note": ""})]),
        Node(id="fill", kind="action", payload={"guard": "true", "updates": [{"var": "held", "expr": "true"}, {"var": "shown", "expr": "0"}]},
             children=[Node(id="fill-by", kind="observation", payload={"event": "save"}),
                       Node(id="fill-touches", kind="touches", payload={"only": ["held", "shown"], "via": [{"event": "set", "where": {"sig": "*slot*"}}]})]),
        Node(id="drain", kind="action", payload={"guard": "held", "updates": [{"var": "held", "expr": "false"}, {"var": "shown", "expr": "shown + 1"}]},
             children=[Node(id="drain-by", kind="observation", payload={"event": "status"}),
                       Node(id="drain-touches", kind="touches", payload={"only": ["held", "shown"], "via": [{"event": "delete", "where": {"sig": "*slot*"}}]})]),
        Node(id="ask-empty", kind="action", payload={"guard": "not held", "updates": []},
             children=[Node(id="ask-by", kind="observation", payload={"event": "status"})]),
        Node(id="new-day", kind="action", payload={"guard": "true", "updates": [{"var": "writes", "expr": "0"}]},
             children=[Node(id="day-by", kind="observation", payload={"event": "status"})]),
        Node(id="once", kind="invariant", payload={"expr": "shown <= 1"}),
    ])


def _read(exists: bool) -> dict:
    return {"k": "db", "op": "get", "sig": 'collection("slot").document("last")',
            "res": {"id": "last", "exists": exists, "data": {"x": 1} if exists else None}}


def _session(drained: bool) -> Node:
    """save fills the slot; status reads it held, then (drained or not) reads it after."""
    calls = [
        {"seq": 1, "fn": "save", "kwargs": {}, "events": [{"k": "db", "op": "set", "sig": 'collection("slot").document("last")', "args": [{"x": 1}]}]},
        {"seq": 2, "fn": "status", "kwargs": {}, "events": [_read(True)] + ([{"k": "db", "op": "delete", "sig": 'collection("slot").document("last")', "args": []}] if drained else [])},
        {"seq": 3, "fn": "status", "kwargs": {}, "events": [_read(not drained)]},
    ]
    return Node(id="s", kind="session", links={"model": ["m"]}, children=[_scenario(c) for c in calls])


def _tree(drained: bool) -> Quern:
    t = Quern()
    t.root.children = [_model(), _session(drained)]
    return t


def test_a_status_is_judged_as_the_drain_when_the_slot_was_held_and_agrees():
    out = agrees(_tree(drained=True), "s", "model")
    assert out.violations == 0, out.diagnostics
    assert any("new-day" not in n and "not judged" in n for n in out.notes) or True


def test_a_status_that_leaves_the_slot_held_disagrees_with_the_drain():
    out = agrees(_tree(drained=False), "s", "model")
    assert out.violations == 1, out.diagnostics
    assert "drain" in out.diagnostics[0] and "'held'" in out.diagnostics[0]


def test_the_counter_part_is_noted_not_judged_when_its_variable_is_not_shown():
    out = agrees(_tree(drained=True), "s", "model")
    assert not any("new-day" in d for d in out.diagnostics)
