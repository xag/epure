"""The class, proven: the asymptotic algebra, the constructs a function has, and model/bound
over the cloakroom's glance and over a function on disk."""

from __future__ import annotations

import ast

import pytest

import epure.bound  # noqa: F401 — registers the native
from quern import Node, Quern, Rule, run_rules

from epure import spec
from epure.bound import constructs, model_bound, parse, show, under


def _b(src: str, *sizes: str):
    return parse(src, set(sizes), "test")


def test_the_algebra_orders_classes_as_complexity_does():
    n = {"n"}
    assert under(_b("n", *n), _b("n * n", *n))
    assert under(_b("n * log(n)", *n), _b("n ** 2", *n))
    assert not under(_b("n ** 2", *n), _b("n * log(n)", *n))
    assert not under(_b("n * log(n)", *n), _b("n", *n))
    assert under(_b("1", *n), _b("n", *n))
    assert under(_b("n + m", "n", "m"), _b("n * m + n + m", "n", "m"))
    assert not under(_b("n * m", "n", "m"), _b("n + m", "n", "m"))
    assert not under(_b("m", "n", "m"), _b("n", "n", "m")), "a size the claim does not name"
    assert show(_b("n * log(n) + 3", *n)) == "n * log(n)"
    with pytest.raises(ValueError):
        _b("k", *n)
    with pytest.raises(ValueError):
        _b("n / 2", *n)


def test_the_constructs_of_a_function_are_its_loops_folds_and_calls():
    fn = ast.parse(
        "def f(xs, ys, store):\n"
        "    out = [g(x) for x in xs if x]\n"
        "    for y in ys:\n"
        "        for z in y.parts:\n"
        "            out.append(len(z))\n"
        "    order = sorted(ys)\n"
        "    doc = store.get()\n"
        "    v = conf.get('k')\n"
        "    return out, order, doc, v\n").body[0]
    cs = constructs(fn)
    kinds = [(c.kind, c.key[:22], len(c.loops)) for c in cs]
    assert ("loop", "for x in xs", 0) in kinds
    assert ("call", "g(x)", 1) in kinds, "the call inside the comprehension is enclosed by it"
    assert ("loop", "for z in y.parts", 1) in kinds
    assert ("fold", "sorted(ys)", 0) in kinds
    assert ("call", "store.get()", 0) in kinds, "a store read: get with no arguments"
    assert not any(c.key.startswith("conf.get") for c in cs), "a lookup: get with arguments"
    assert not any(c.key.startswith("len(") or c.key.startswith("out.append") for c in cs)


def _tree(*nodes: Node) -> Quern:
    tree = Quern()
    tree.root.children = [n.model_copy(deep=True) for n in nodes]
    return tree


def test_the_glance_is_proven_and_its_sizes_vouched_for():
    out = model_bound(_tree(spec.cloakroom()), "cloakroom")
    assert out.violations == 0, out.diagnostics
    assert out.judged == 3 and not out.notes, out.notes


def test_a_claim_too_small_an_uncovered_fold_and_an_undeclared_size_are_red():
    small = model_bound(_tree(spec._glance_with(
        claims={"compute": "register_entries", "memory": "register_entries", "reads": "1"})),
        "cloakroom")
    assert small.violations == 1 and "derived register_entries * log(register_entries)" in small.diagnostics[0]
    missing = model_bound(_tree(spec._glance_with(derivation=[
        {"at": "for h in register", "size": "register_entries"},
        {"calls": "read", "bound": {"reads": "1"}}])), "cloakroom")
    assert missing.violations == 1 and "uncovered fold" in missing.diagnostics[0]
    unknown = model_bound(_tree(spec._glance_with(derivation=[
        {"at": "for h in register", "size": "coats"},
        {"at": "sorted(register.entries)", "size": "register_entries"},
        {"calls": "read", "bound": {"reads": "1"}}])), "cloakroom")
    assert unknown.violations == 1 and "'coats' is not a size-var" in unknown.diagnostics[0]


def test_a_stale_line_and_an_unstated_dimension_are_red():
    stale = model_bound(_tree(spec._glance_with(derivation=[
        {"at": "for h in register", "size": "register_entries"},
        {"at": "sorted(register.entries)", "size": "register_entries"},
        {"calls": "read", "bound": {"reads": "1"}},
        {"at": "for q in queue", "size": "register_entries"}])), "cloakroom")
    assert stale.violations == 1 and "matches no construct" in stale.diagnostics[0]
    unstated = model_bound(_tree(spec._glance_with(
        claims={"compute": "register_entries * log(register_entries)", "memory": "register_entries"})),
        "cloakroom")
    assert unstated.violations == 1 and "a dimension its claim does not state" in unstated.diagnostics[0]


def test_nesting_multiplies_and_of_spends_another_bounds_claim(tmp_path):
    (tmp_path / "steps.py").write_text(
        "def inner(rows):\n"
        "    return sorted(rows)\n"
        "\n"
        "def outer(decks, rows):\n"
        "    for d in decks:\n"
        "        inner(rows)\n"
        "    return 1\n", encoding="utf-8")
    model = Node(id="m", kind="model", payload={"code_root": str(tmp_path)}, children=[
        Node(id="decks", kind="size-var", payload={"holds": ["decks"]}),
        Node(id="rows", kind="size-var", payload={"holds": ["rows"]}),
        Node(id="inner", kind="bound", payload={
            "code": "steps.py::inner", "claims": {"compute": "rows * log(rows)", "memory": "rows"},
            "derivation": [{"at": "sorted(rows)", "size": "rows"}]}),
        Node(id="outer", kind="bound", payload={
            "code": "steps.py::outer", "claims": {"compute": "decks * rows * log(rows)",
                                                  "memory": "decks * rows"},
            "derivation": [{"at": "for d in decks", "size": "decks"},
                           {"calls": "inner", "of": "steps.py::inner"}]}),
    ])
    out = model_bound(_tree(model), "m")
    assert out.violations == 0, out.diagnostics
    model.children[-1].payload["claims"] = {"compute": "rows * log(rows)", "memory": "decks * rows"}
    out = model_bound(_tree(model), "m")
    assert out.violations == 1 and "derived decks * rows * log(rows)" in out.diagnostics[0]


def test_an_asserted_size_is_a_note_never_a_pass():
    model = spec._glance_with(derivation=[
        {"at": "for h in register", "size": "register_entries"},
        {"at": "sorted(register.entries)", "size": "register_entries"},
        {"calls": "read", "bound": {"reads": "1"}}])
    for c in model.children:
        if c.kind == "size-var":
            c.payload.pop("holds", None)
    out = model_bound(_tree(model), "cloakroom")
    assert out.violations == 0 and any("asserted" in n for n in out.notes), out.notes


def test_the_native_answers_in_the_rule_language():
    tree = _tree(spec.cloakroom())
    tree.rules = [Rule(name="bounded", kind="model", expr="solve('model/bound', self) == 0")]
    assert [r.ok for r in run_rules(tree) if r.rule == "bounded"] == [True]
