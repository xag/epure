"""model/bites: every law of a drawing is refuted by some mutant of its actions, or it is
named vacuous. The demonstration a proof keeps beside it, generated from the drawing."""

from quern import Node, Quern

from epure.prove import bites
from epure.spec import turnstile, turnstile_with_a_vacuous_invariant


def _tree(model):
    t = Quern()
    t.root.children = [model]
    return t


def test_the_turnstiles_law_bites_and_the_mutant_is_named():
    out = bites(_tree(turnstile()), "turnstile")
    assert out.vacuous == []
    assert "push-through without its guard" in out.refuted_by["no-free-entry"]
    assert out.mutants >= 1   # and no more than it took: a part stops once every law has a witness


def test_a_law_true_by_the_domains_is_vacuous():
    out = bites(_tree(turnstile_with_a_vacuous_invariant()), "turnstile")
    assert out.vacuous == ["coins-are-counted"]
    assert "no-free-entry" in out.refuted_by


def test_a_value_swap_is_among_the_mutants():
    """A law that only a wrong value breaks - not a dropped guard or update - still bites."""
    from quern import Node
    model = Node(id="m", kind="model", children=[
        Node(id="x", kind="state-var", payload={"type": "enum", "domain": ["a", "b"], "init": "a"}),
        Node(id="keep", kind="action", payload={"guard": "true", "updates": [{"var": "x", "expr": "'a'"}]}),
        Node(id="never-b", kind="invariant", payload={"expr": "x != 'b'"}),
    ])
    out = bites(_tree(model), "m")
    assert out.vacuous == []
    assert out.refuted_by["never-b"] == ["keep with 'x' set to 'b'"]


def test_a_law_naming_no_variable_is_refused_not_called_vacuous():
    import pytest
    model = turnstile()
    model.children.append(Node(id="about-nothing", kind="invariant", payload={"expr": "plan == 'free' or coins >= 0"}))
    with pytest.raises(Exception):
        bites(_tree(model), "turnstile")


def test_a_name_inside_a_string_literal_couples_nothing():
    from epure.prove import _names_in
    assert _names_in("plan == 'premium' and premium", {"plan", "premium"}) == {"plan", "premium"}
    assert _names_in("plan == 'premium'", {"plan", "premium"}) == {"plan"}
