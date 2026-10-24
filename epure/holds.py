"""model/holds — a property established over every binding of its finite domains.

The third way a drawing proves something, beside the states a model reaches (`model/prove`)
and the shape of a step's code (`model/bound`): the VALUES a function gives. A `property`
names finite domains for its arguments, the functions it may call, and an expression that
must hold; the checker evaluates the expression at every binding of the domains, through the
real functions, and counts the properties with a binding where it does not.

That is a proof by exhaustion over the domains the drawing declares, and it is honest about
exactly that: a formula over the reals is proven here on a grid, and the grid is written in
the drawing where a reader can refuse it as too coarse. What a test did at the three points
somebody typed, this does at every point of a stated domain, and the statement outlives the
points. A domain may also be computed - `{"from": "path.py::fn"}` - which makes the same
checker the universal over a committed artifact: every page the server lists is served,
every shot in the folder is credited. The function is the drawing's witness: it projects the
world (a page, a record, a learner's cell) onto the values the expression reads, and the
expression is where the claim lives.

What a property is not: a verdict on an input somebody chose. A property with a domain of
one point is a test moved into the ledger, and the checker says so in a note.

Importing this module registers the `model/holds` native and nothing else. The native
returns a COUNT of refuted properties, so the rule shape is `solve('model/holds', self) == 0`.
"""

from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from itertools import product
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from quern import Node, Quern, TreeStore, get_node, register_native
from quern.expr import compile_expr

from .prove import _LITERALS, _domain

DEFAULT_CAP = 1_000_000


class Refutation(BaseModel):
    property: str
    note: str = ""
    binding: dict[str, Any]
    calls: list[str] = Field(default_factory=list)   # the functions' values at that binding
    error: str = ""


class Holding(BaseModel):
    model: str
    properties: list[str]
    bindings: int
    refuted: list[Refutation]
    notes: list[str] = Field(default_factory=list)


def _callable(code: str, root: Path) -> Callable[..., Any]:
    """`path.py::name` or `path.py::Class.method`, imported live from `root`."""
    path, _, qual = str(code).partition("::")
    if not path.endswith(".py") or not qual:
        raise ValueError(f"'{code}': a witness is 'path.py::name'")
    module_name = path[:-3].replace("\\", "/").strip("/").replace("/", ".")
    root_str = str(root.resolve())
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        spec = importlib.util.spec_from_file_location(module_name, root / path)
        if spec is None or spec.loader is None:
            raise ValueError(f"'{code}': cannot import {path} under {root}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
    obj: Any = module
    for part in qual.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            raise ValueError(f"'{code}': no attribute '{part}' in {path}")
    if not callable(obj):
        raise ValueError(f"'{code}' is not callable")
    return obj


def _values(spec: Any, where: str, root: Path) -> list[Any]:
    """A domain: a literal one (as a state-var's), or one a witness yields."""
    if isinstance(spec, dict) and "from" in spec:
        values = list(_callable(spec["from"], root)())
        if not values:
            raise ValueError(f"{where}: the domain {spec['from']} yielded nothing - a "
                             "property over nothing holds of nothing")
        return values
    if isinstance(spec, list):
        return list(spec)
    return _domain(spec, where)


def hold(tree: Quern | TreeStore, path: str, cap: int = DEFAULT_CAP) -> Holding:
    """Every property under the model at `path`, evaluated at every binding of its domains."""
    model = get_node(tree, path)
    if model is None:
        raise ValueError(f"no node at '{path}'")
    if model.kind != "model":
        raise ValueError(f"'{path}' is a '{model.kind or '(bare)'}', not a model — "
                         "model/holds holds properties of models")
    root = Path(str(model.payload.get("code_root") or os.environ.get("EPURE_CODE_ROOT") or "."))
    refuted: list[Refutation] = []
    notes: list[str] = []
    names: list[str] = []
    bindings_total = 0
    for c in model.children:
        if c.kind != "property":
            continue
        names.append(c.id)
        where = f"property '{c.id}'"
        over = c.payload.get("over") or {}
        if not over:
            raise ValueError(f"{where}: names no domain - a property is over something")
        calls = {name: _callable(code, root) for name, code in (c.payload.get("calls") or {}).items()}
        expr = compile_expr(str(c.payload.get("holds") or ""))
        args = list(over)
        domains = [_values(over[a], f"{where} arg '{a}'", root) for a in args]
        total = 1
        for d in domains:
            total *= len(d)
        if total > cap:
            raise ValueError(f"{where}: {total} bindings exceed the cap of {cap}; refine the "
                             "domains or raise the cap - a partial sweep is not a proof")
        if total == 1:
            notes.append(f"{where}: one binding - a test moved into the ledger, not a sweep")
        env = {**_LITERALS, **calls}
        bindings_total += total
        for combo in product(*domains):
            binding = dict(zip(args, combo))
            try:
                ok = expr.evaluate(env, binding)
            except Exception as e:  # a witness that raises refutes: the property is not even evaluable there
                refuted.append(Refutation(property=c.id, note=c.payload.get("note", ""),
                                          binding=binding, error=f"{type(e).__name__}: {e}"))
                break
            if not ok:
                _, reads = expr.trace(env, binding)
                shown = [f"{r.call}({', '.join(repr(a) for a in r.args)}) = {r.value!r}"
                         for r in reads]
                refuted.append(Refutation(property=c.id, note=c.payload.get("note", ""),
                                          binding=binding, calls=shown))
                break
    return Holding(model=model.id, properties=names, bindings=bindings_total,
                   refuted=refuted, notes=notes)


def holds_count(tree: Quern | TreeStore, path: str, cap: int = DEFAULT_CAP) -> float:
    """The native: how many properties of the model at `path` have a binding that refutes
    them. A rule wants `== 0`: every property holds over its whole domain."""
    return float(len(hold(tree, path, cap=int(cap)).refuted))


def _import_closure(root: Path, path: str) -> set[Path]:
    """The project's own files a witness module runs: its file, and every module under
    `root` it imports, at any depth, read from the source."""
    import ast
    seen: set[Path] = set()
    todo = [(root / path).resolve()]
    while todo:
        f = todo.pop()
        if f in seen or not f.is_file():
            continue
        seen.add(f)
        try:
            tree = ast.parse(f.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, ValueError):
            continue
        package = f.parent
        for n in ast.walk(tree):
            names: list[str] = []
            base = root
            if isinstance(n, ast.Import):
                names = [a.name for a in n.names]
            elif isinstance(n, ast.ImportFrom):
                if n.level:
                    base = package
                    for _ in range(n.level - 1):
                        base = base.parent
                mod = n.module or ""
                names = [f"{mod}.{a.name}" if mod else a.name for a in n.names] + ([mod] if mod else [])
            for name in names:
                parts = name.split(".")
                for k in range(len(parts), 0, -1):
                    stem = base.joinpath(*parts[:k])
                    for cand in (stem.with_suffix(".py"), stem / "__init__.py"):
                        if cand.is_file():
                            todo.append(cand.resolve())
                            # ...and the packages it sits in, whose __init__ runs first
                            todo += [base.joinpath(*parts[:j], "__init__.py").resolve()
                                     for j in range(1, k)]
                            break
                    else:
                        continue
                    break
    return seen


def holds_reads(tree: Quern | TreeStore, path: str, cap: int = DEFAULT_CAP):
    """What a sweep reads that it may not open while it runs: the project's files every
    witness imports, and what the model declares in `reads` - the data its witnesses use,
    which an earlier call may have loaded already. A model that declares no `reads` cannot
    say, and its sweep is run every time."""
    model = get_node(tree, path)
    if model is None or model.kind != "model" or model.payload.get("reads") is None:
        return None
    root = Path(str(model.payload.get("code_root") or os.environ.get("EPURE_CODE_ROOT") or "."))
    out: set[Path] = {root / str(p) for p in model.payload.get("reads") or []}
    for c in model.children:
        if c.kind != "property":
            continue
        codes = list((c.payload.get("calls") or {}).values())
        codes += [v["from"] for v in (c.payload.get("over") or {}).values()
                  if isinstance(v, dict) and "from" in v]
        for code in codes:
            out |= _import_closure(root, str(code).partition("::")[0])
    return sorted(out)


from .spec import SEMANTIC_MODEL_SPEC  # noqa: E402

register_native("model/holds", holds_count, SEMANTIC_MODEL_SPEC["model/holds"],
                reads=holds_reads, env=("EPURE_CODE_ROOT",), spawns=True)
