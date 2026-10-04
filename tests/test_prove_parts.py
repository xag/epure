"""A model that draws independent rules side by side is walked part by part: the states add
where a product would multiply, and an invariant is judged in the part that holds its variables."""

from quern import Node, Quern

from epure.prove import prove


def _model():
    return Node(id="two-rooms", kind="model", children=[
        Node(id="a", kind="state-var", payload={"type": "enum", "domain": [0, 1, 2], "init": 0}),
        Node(id="b", kind="state-var", payload={"type": "enum", "domain": [0, 1, 2, 3], "init": 0}),
        Node(id="step-a", kind="action", payload={"guard": "a < 2", "updates": [{"var": "a", "expr": "a + 1"}]}),
        Node(id="step-b", kind="action", payload={"guard": "b < 3", "updates": [{"var": "b", "expr": "b + 1"}]}),
        Node(id="a-stays-small", kind="invariant", payload={"expr": "a <= 2"}),
        Node(id="b-stays-small", kind="invariant", payload={"expr": "b <= 2"}),
    ])


def test_independent_parts_are_walked_apart_and_their_states_add():
    tree = Quern()
    tree.root.children = [_model()]
    proof = prove(tree, "two-rooms")
    assert proof.states_explored == 3 + 4, "three states of a, four of b: a sum, not 12"
    assert [v.invariant for v in proof.violations] == ["b-stays-small"]


def test_an_invariant_over_both_parts_joins_them():
    model = _model()
    model.children.append(Node(id="never-both-high", kind="invariant", payload={"expr": "a + b < 5"}))
    tree = Quern()
    tree.root.children = [model]
    proof = prove(tree, "two-rooms")
    assert proof.states_explored == 12, "the invariant couples a and b: the product is walked"
    assert {v.invariant for v in proof.violations} == {"b-stays-small", "never-both-high"}
