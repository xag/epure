"""model/escapes: liveness of return, on a house with a cellar.

Three rooms, and the stairs down have no stairs up: the classic trap `prove` cannot
see, because the cellar violates no invariant — it is merely a state you enter and
never leave. What is asserted exactly is asserted exactly on purpose, as in
test_prove: determinism is a contract.
"""

from __future__ import annotations

from quern import Node, Quern

from epure.reach import escapes


def _house(stairs_up: bool) -> Quern:
    children = [
        Node(id="room", kind="state-var",
             payload={"type": "enum", "domain": ["hall", "kitchen", "cellar"],
                      "init": "hall"}),
        Node(id="to-kitchen", kind="action",
             payload={"guard": "room == 'hall'",
                      "updates": [{"var": "room", "expr": "'kitchen'"}]}),
        Node(id="to-hall", kind="action",
             payload={"guard": "room == 'kitchen'",
                      "updates": [{"var": "room", "expr": "'hall'"}]}),
        Node(id="down", kind="action",
             payload={"guard": "room == 'kitchen'",
                      "updates": [{"var": "room", "expr": "'cellar'"}]}),
    ]
    if stairs_up:
        children.append(Node(id="up", kind="action",
                             payload={"guard": "room == 'cellar'",
                                      "updates": [{"var": "room",
                                                   "expr": "'kitchen'"}]}))
    tree = Quern()
    tree.root.children = [Node(id="house", kind="model", children=children)]
    return tree


def test_the_cellar_strands():
    escape = escapes(_house(stairs_up=False), "house", "room == 'hall'")
    assert escape.verdict == "refuted"
    assert escape.states_explored == 3
    assert escape.home_states == 1
    [s] = escape.stranded
    assert s.state == {"room": "cellar"}
    assert [step["action"] for step in s.path] == ["to-kitchen", "down"]
    assert s.exits == []
    assert "no way home after to-kitchen -> down" in s.replay()
    assert "no action is enabled at all" in s.replay()


def test_stairs_up_discharge_it():
    escape = escapes(_house(stairs_up=True), "house", "room == 'hall'")
    assert escape.verdict == "proved"
    assert escape.stranded == []
    assert escape.states_explored == 3


def test_a_home_nothing_satisfies_is_its_own_verdict():
    escape = escapes(_house(stairs_up=True), "house", "room == 'attic'")
    assert escape.verdict == "home-unreachable"
    assert escape.home_states == 0
    # NOT reported as 'everything is stranded': the claim was miswritten, and a pile
    # of identical violations would bury that fact.
    assert escape.stranded == []


def test_a_stranded_state_names_its_useless_doors():
    # A cellar with a light switch: an enabled action that leads nowhere home. The
    # report must say 'exits: ...' rather than 'no action enabled' — stuck with doors
    # is a different complaint than stuck without.
    tree = _house(stairs_up=False)
    model = tree.root.children[0]
    model.children.append(Node(id="light", kind="state-var",
                               payload={"type": "bool", "init": False}))
    model.children.append(Node(id="toggle-light", kind="action",
                               payload={"guard": "room == 'cellar'",
                                        "updates": [{"var": "light",
                                                     "expr": "not light"}]}))
    escape = escapes(tree, "house", "room == 'hall'")
    assert escape.verdict == "refuted"
    assert all(s.state["room"] == "cellar" for s in escape.stranded)
    assert all(s.exits == ["toggle-light"] for s in escape.stranded)
    assert "every one leads further from home" in escape.stranded[0].replay()
