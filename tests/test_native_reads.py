"""What each native says it reads, so a check can keep its answer while that is unchanged
(quern.cache): a native that says nothing is run on every check, and one that says too
little would keep a stale verdict."""

from pathlib import Path

from quern import Node, Quern, Rule, run_rules
from quern.cache import NativeCache
from quern.tree import NATIVE, NATIVE_READS

import epure.behavior  # noqa: F401  (each registers its natives)
import epure.bound
import epure.conformance  # noqa: F401
import epure.cost  # noqa: F401
import epure.holds
import epure.prove
import epure.reach  # noqa: F401
from epure.spec import _with_property


def test_every_native_says_what_it_reads():
    ours = sorted(n for n, fn in NATIVE.items() if str(getattr(fn, "__module__", "")).startswith("epure"))
    assert ours and [n for n in ours if n not in NATIVE_READS] == []


def test_a_sweep_reads_its_witnesses_and_what_they_import_and_the_declared_data(tmp_path: Path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "helper.py").write_text("def two():\n    return 2\n", encoding="utf-8")
    (tmp_path / "w.py").write_text("from pkg.helper import two\n\ndef f(x):\n    return two() * x\n",
                                   encoding="utf-8")
    prop = Node(id="p", kind="property", payload={"over": {"a": [1, 2]}, "calls": {"f": "w.py::f"},
                                                  "holds": "f(a) > 0"})
    model = Node(id="m", kind="model", payload={"code_root": str(tmp_path), "reads": ["data"]},
                 children=[prop])
    tree = Quern()
    tree.root.children = [model]
    read = {Path(p).resolve() for p in epure.holds.holds_reads(tree, "m")}
    assert {(tmp_path / "w.py").resolve(), (tmp_path / "pkg" / "helper.py").resolve(),
            (tmp_path / "pkg" / "__init__.py").resolve(), (tmp_path / "data").resolve()} <= read


def test_a_sweep_whose_model_declares_no_reads_cannot_say(tmp_path: Path):
    tree = Quern()
    tree.root.children = [_with_property("x + y <= 7")]
    assert epure.holds.holds_reads(tree, "turnstile") is None


def test_a_derivation_reads_every_file_its_bounds_name(tmp_path: Path):
    model = Node(id="m", kind="model", payload={"code_root": str(tmp_path)}, children=[
        Node(id="b", kind="bound", payload={"code": "app/a.py::f"}, children=[
            Node(id="c", kind="bound", payload={"code": "app/b.py::g"})])])
    tree = Quern()
    tree.root.children = [model]
    assert epure.bound.model_bound_reads(tree, "m") == sorted([tmp_path / "app" / "a.py",
                                                              tmp_path / "app" / "b.py"])


def test_the_mutants_run_again_only_when_the_drawing_moves(tmp_path: Path, monkeypatch):
    """bites kept its own answer in a file named by the drawing's digest; the check's cache
    keeps it now, keyed by the subtree the native read."""
    runs = []
    real = epure.prove.bites
    monkeypatch.setattr(epure.prove, "bites", lambda *a, **k: runs.append(1) or real(*a, **k))
    tree = Quern(rules=[Rule(name="bites", expr="solve('model/bites', 'turnstile') >= 0")])
    tree.root.children = [_with_property("x + y <= 7"), Node(id="elsewhere")]
    cache = NativeCache(tmp_path)
    run_rules(tree, cache=cache)
    tree.get("elsewhere").payload["n"] = 1
    run_rules(tree, cache=cache)
    assert len(runs) == 1
    tree.get("turnstile").children.append(Node(id="note", kind="note"))
    run_rules(tree, cache=cache)
    assert len(runs) == 2
