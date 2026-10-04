"""model/holds: a property over every binding of its finite domains, through the real
functions, with a computed domain for the universal over an artifact."""

from pathlib import Path

from quern import Node, Quern

import epure.holds  # noqa: F401  (registers the native)
from epure.holds import hold
from epure.spec import _with_property


def _tree(model):
    t = Quern()
    t.root.children = [model]
    return t


def test_a_property_on_a_grid_holds_or_names_the_binding():
    out = hold(_tree(_with_property("x + y <= 7")), "turnstile")
    assert out.refuted == [] and out.bindings >= 12
    out = hold(_tree(_with_property("x + y <= 6")), "turnstile")
    assert [r.binding for r in out.refuted] == [{"x": 5, "y": 2}]


def test_a_witness_is_called_and_a_domain_may_come_from_one(tmp_path: Path):
    (tmp_path / "w.py").write_text(
        "def double(x):\n    return 2 * x\n\n"
        "def pages():\n    return ['/a', '/b', '/c']\n\n"
        "def status(p):\n    return 200 if p != '/c' else 404\n", encoding="utf-8")
    model = Node(id="m", kind="model", payload={"code_root": str(tmp_path)}, children=[
        Node(id="doubling-is-monotone", kind="property",
             payload={"over": {"a": [0, 1, 2, 3], "b": [0, 1, 2, 3]},
                      "calls": {"f": "w.py::double"},
                      "holds": "a > b or f(a) <= f(b)"}),
        Node(id="every-page-is-served", kind="property",
             payload={"over": {"p": {"from": "w.py::pages"}},
                      "calls": {"status": "w.py::status"},
                      "holds": "status(p) == 200"}),
    ])
    out = hold(_tree(model), "m")
    assert [r.property for r in out.refuted] == ["every-page-is-served"]
    assert out.refuted[0].binding == {"p": "/c"}
    assert out.refuted[0].calls == ["status('/c') = 404"]


def test_a_single_binding_is_noted_as_a_test_not_a_sweep():
    model = Node(id="m", kind="model", children=[
        Node(id="one-point", kind="property", payload={"over": {"x": [1]}, "holds": "x == 1"})])
    out = hold(_tree(model), "m")
    assert out.refuted == [] and any("one binding" in n for n in out.notes)
