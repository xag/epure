"""Cost on the drawing and on the tape: growth read symbolically, model/cost over the
cloakroom, conduct/cost over recorded visits, and the rule that refuses a costless action."""

from __future__ import annotations

import pytest

import epure.cost  # noqa: F401 — registers the natives
from quern import Node, Quern, Rule, run_rules, validate_package

from epure import spec
from epure.cost import conduct_cost, growth, model_cost
from epure.package import SEMANTIC_MODEL_PACKAGE


def test_growth_reads_the_degree_of_each_size():
    assert growth("3") == {}
    assert growth("1 + n") == {"n": 1}
    assert growth("n * n") == {"n": 2}
    assert growth("n * m + 2") == {"n": 1, "m": 1}
    assert growth("max(n, 3 * m)") == {"n": 1, "m": 1}
    assert growth("n * n / n") == {"n": 1}
    assert growth("true") == {}
    with pytest.raises(ValueError):
        growth("n ** 2")
    with pytest.raises(ValueError):
        growth("'red'")


def _tree(*nodes: Node) -> Quern:
    tree = Quern()
    tree.root.children = [n.model_copy(deep=True) for n in nodes]
    return tree


def test_the_cloakroom_states_every_cost_within_its_growth():
    out = model_cost(_tree(spec.cloakroom()), "cloakroom")
    assert out.violations == 0 and out.judged == 7 * 3, out.diagnostics


def test_a_drawing_with_no_doors_holds_and_says_no_tape_could_count_it():
    out = model_cost(_tree(spec.turnstile()), "turnstile")
    assert out.violations == 0 and out.notes and "no boundary" in out.notes[0]


def test_model_cost_names_the_action_the_dimension_and_the_size():
    out = model_cost(_tree(spec.cloakroom_overgrown()), "cloakroom")
    assert out.violations == 1
    assert "import-register" in out.diagnostics[0] and "degree 2" in out.diagnostics[0]
    out = model_cost(_tree(spec.cloakroom_unstated()), "cloakroom")
    assert out.violations == 1 and "glance" in out.diagnostics[0] and "bytes" in out.diagnostics[0]
    out = model_cost(_tree(spec.cloakroom_unsized()), "cloakroom")
    assert out.violations == 1 and "'coats'" in out.diagnostics[0]


def test_conduct_cost_counts_what_the_act_spent_at_the_tapes_sizes():
    within = conduct_cost(_tree(spec.cloakroom(), spec.WITHIN_COST), "visit", "model")
    assert within.violations == 0 and within.judged == 3, within
    over = conduct_cost(_tree(spec.cloakroom(), spec.OVERSPENT), "visit", "model")
    assert over.violations == 1
    assert "spent 3 reads" in over.diagnostics[0] and "allows 0" in over.diagnostics[0]
    assert "register_entries=0" in over.diagnostics[0]
    at_size = conduct_cost(_tree(spec.cloakroom(), spec.IMPORT_OVER), "visit", "model")
    assert at_size.violations == 1 and "allows 3 at register_entries=2" in at_size.diagnostics[0]


def test_an_unwitnessed_size_is_a_note_never_a_pass():
    out = conduct_cost(_tree(spec.cloakroom(), spec.IMPORT_UNWITNESSED), "visit", "model")
    assert out.violations == 0
    assert out.judged == 1, "writes, a constant, is judged; reads and bytes are not"
    assert len(out.notes) == 2 and all("unwitnessed" in n for n in out.notes)


def test_a_model_with_no_read_doors_counts_nothing_and_says_so():
    out = conduct_cost(_tree(spec.turnstile(), spec.COUNTED_AFTER_THE_READ), "session", "model")
    assert out.violations == 0 and out.judged == 0 and out.notes


def test_the_natives_answer_in_the_rule_language():
    tree = _tree(spec.cloakroom(), spec.OVERSPENT)
    tree.rules = [Rule(name="costed", kind="model", expr="solve('model/cost', self) == 0"),
                  Rule(name="within-cost", kind="session",
                       expr="solve('conduct/cost', self, 'model') == 0")]
    verdicts = {(r.rule, r.ok) for r in run_rules(tree)}
    assert ("costed", True) in verdicts and ("within-cost", False) in verdicts


def test_an_action_with_no_cost_is_refused_by_the_rule(tmp_path):
    rules = {ce.rule for ce in SEMANTIC_MODEL_PACKAGE.counter_examples}
    assert "an-action-states-its-cost" in rules
    model = spec.cloakroom()
    for a in model.children:
        if a.id == "glance":
            a.children = [c for c in a.children if c.kind != "cost"]
    tree = _tree(model)
    tree.rules = [r for r in SEMANTIC_MODEL_PACKAGE.rules if r.name == "an-action-states-its-cost"]
    red = [r for r in run_rules(tree) if not r.ok]
    assert [r.node for r in red] == ["cloakroom/glance"]


def test_compute_is_held_through_the_boundarys_compute_door():
    within = conduct_cost(_tree(spec.cloakroom(), spec.GLANCE_COUNTED), "visit", "model")
    assert within.violations == 0 and within.judged == 4, within
    over = conduct_cost(_tree(spec.cloakroom(), spec.GLANCE_OVERWORKED), "visit", "model")
    assert over.violations == 1 and "spent 9000 compute" in over.diagnostics[0]


def test_a_stated_compute_with_no_compute_door_is_noted_unheld():
    model = spec.cloakroom()
    for c in model.children:
        if c.kind == "boundary":
            del c.payload["compute"]
    out = conduct_cost(_tree(model, spec.GLANCE_OVERWORKED), "visit", "model")
    assert out.violations == 0 and any("unheld" in n for n in out.notes), out
