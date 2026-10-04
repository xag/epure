"""Bound: the computational complexity of a step along every dimension, derived over its
code and held to its claim, on the drawing, in an instant.

A `cost` states what one call may spend at the tape's sizes; a tape witnesses it at the
sizes recorded and no other. A `bound` claims the class: the step's cost is O(f) in the
size-vars, per dimension - compute, documents read, documents written, bytes across the
store, memory held, and whatever else the drawing names - and carries the derivation that
makes the claim a proof rather than a measurement:

- the step's code (`code`: `path.py::function`, or `source`: the text itself);
- one derivation line per construct that costs: every loop and comprehension (`size`: how
  many iterations, as an expr in the size-vars), every fold - sorted, sum, list, set, dict,
  join over an iterable - (`size` likewise), and every call that is not in the free table
  (`bound`: what one call spends per dimension, or `of`: another bound's claim).

`model/bound` reads the code's syntax tree, finds every such construct, refuses one no line
covers and a line no construct has, composes the lines - nesting multiplies by the loop's
size, sequence adds - and holds the total to the claim per dimension by asymptotic
domination (n log n is under n^2, n^2 is not under n log n, a size the claim does not name
is not under anything). A loop costs its size in compute on its own; a list, set or dict
built over a size holds that size in memory; a sort costs size log size. Everything the
free table names - length, a dictionary lookup, an append, a string method - is constant.

What is NOT derived is red, with the construct named: a call nobody bounded, a loop nobody
sized. That red is the statement that the step's complexity is unproven, which is the
honest thing a drawing can say until someone derives it. The free table and the per-call
bounds are the trusted base, the way axioms are, and they are data on the drawing where a
reader can refuse them.

Sizes are checked where they can be: a loop's iterable whose text a size-var `holds` names
is a size the drawing vouches for; one it does not is asserted by the line, counted in the
notes, so a model whose derivations rest on assertions says so.
"""

from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Any

from quern import Node, Quern, TreeStore, register_native

from epure.conformance import Conformance, get_node

# --- the asymptotic algebra ------------------------------------------------------------------
#
# A bound is a sum of monomials; a monomial maps each size to (degree, log-degree). n log n is
# {n: (1, 1)}, n^2 is {n: (2, 0)}, n * m is {n: (1, 0), m: (1, 0)}, a constant is {}.

Monomial = dict[str, tuple[int, int]]
Bound = list[Monomial]

ONE: Bound = [{}]
ZERO: Bound = []


def _mul_m(a: Monomial, b: Monomial) -> Monomial:
    out = dict(a)
    for v, (d, l) in b.items():
        d0, l0 = out.get(v, (0, 0))
        out[v] = (d0 + d, l0 + l)
    return out


def _under_m(a: Monomial, b: Monomial) -> bool:
    """a is O(b): in every size, a's degree is lower, or equal with no more logs."""
    for v, (d, l) in a.items():
        d2, l2 = b.get(v, (0, 0))
        if (d, l) > (d2, l2):
            return False
    return True


def add(a: Bound, b: Bound) -> Bound:
    return normal(list(a) + list(b))


def mul(a: Bound, b: Bound) -> Bound:
    return normal([_mul_m(x, y) for x in a for y in b])


def normal(b: Bound) -> Bound:
    """Drop the monomials another already dominates; keep one of equals."""
    out: Bound = []
    for m in b:
        if any(_under_m(m, o) for o in out):
            continue
        out = [o for o in out if not _under_m(o, m)] + [m]
    return out


def under(a: Bound, b: Bound) -> bool:
    """a is O(b): every monomial of a is under some monomial of b."""
    if not a:
        return True
    return all(any(_under_m(m, o) for o in b) for m in a)


def parse(src: str, sizes: set[str], where: str) -> Bound:
    """A class expression - sizes, numbers, +, *, ** with an integer, log(x) - as a bound.
    Any name that is not a size-var is refused: a class is stated in the drawing's sizes."""
    try:
        tree = ast.parse(str(src), mode="eval")
    except SyntaxError as e:
        raise ValueError(f"{where}: {src!r} is not a class expression ({e.msg})") from e

    def go(n: ast.AST) -> Bound:
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return ZERO if n.value == 0 else ONE
        if isinstance(n, ast.Name):
            if n.id not in sizes:
                raise ValueError(f"{where}: {n.id!r} is not a size-var of the model")
            return [{n.id: (1, 0)}]
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            return add(go(n.left), go(n.right))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult):
            return mul(go(n.left), go(n.right))
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Pow) \
                and isinstance(n.right, ast.Constant) and isinstance(n.right.value, int):
            out: Bound = ONE
            for _ in range(n.right.value):
                out = mul(out, go(n.left))
            return out
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "log" \
                and len(n.args) == 1:
            inner = go(n.args[0])
            return normal([{v: (0, 1)} for m in inner for v in m] or ONE)
        raise ValueError(f"{where}: {ast.unparse(n)!r} is not a class expression "
                         "(sizes, numbers, +, *, ** n, log(x))")
    return go(tree.body)


def show(b: Bound) -> str:
    if not b:
        return "0"
    parts = []
    for m in b:
        if not m:
            parts.append("1")
            continue
        fs = []
        for v, (d, l) in sorted(m.items()):
            fs += [v] * d if d <= 1 else [f"{v}^{d}"]
            fs += [f"log({v})"] * l
        parts.append(" * ".join(fs))
    return " + ".join(parts)


# --- the constructs of a function -----------------------------------------------------------

FOLDS = {"sorted": True, "sum": False, "any": False, "all": False, "min": False, "max": False,
         "list": False, "set": False, "dict": False, "tuple": False, "frozenset": False,
         "join": False, "enumerate": False, "zip": False, "map": False, "filter": False}
ALLOCATING = {"sorted", "list", "set", "dict", "tuple", "frozenset", "join"}
LOGGED = {"sorted"}
# Calls that cost a constant along every dimension: the trusted base. A callee name here
# (the function's name, or the method's) needs no derivation line.
FREE = {
    "len", "isinstance", "issubclass", "int", "float", "str", "bool", "round", "abs",
    "repr", "hash", "id", "type", "getattr", "hasattr", "setattr", "callable", "iter",
    "next", "divmod", "ord", "chr", "print", "range",
    "append", "add", "pop", "popleft", "setdefault", "items", "keys", "values",
    "startswith", "endswith", "strip", "lstrip", "rstrip", "lower", "upper", "casefold",
    "split", "rsplit", "replace", "format", "isdigit", "isalpha", "encode", "decode",
    "partition", "count", "find", "index", "insert", "remove", "discard", "clear",
    "isoformat", "timestamp", "now", "utcnow", "time", "perf_counter", "monotonic",
    "debug", "info", "warning", "error", "exception", "_log", "sqrt", "floor", "ceil",
    "exp", "log2", "log10", "pow", "match", "search", "fullmatch", "sub", "compile",
    "get_event_loop", "Lock", "RLock",
}
# `.get` is a dictionary lookup with arguments and a store read without: the arity decides.
FREE_WITH_ARGS = {"get", "update", "copy"}


def _callee(call: ast.Call) -> str:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


class Construct:
    def __init__(self, kind: str, key: str, node: ast.AST, loops: list[str]):
        self.kind = kind      # loop | fold | call
        self.key = key
        self.node = node
        self.line = getattr(node, "lineno", 0)
        self.loops = list(loops)   # the keys of the enclosing loops, outermost first
        self.callee = _callee(node) if isinstance(node, ast.Call) else ""
        self.args = len(node.args) + len(node.keywords) if isinstance(node, ast.Call) else 0


def _loop_key(target: ast.AST, iter_: ast.AST) -> str:
    return f"for {ast.unparse(target)} in {ast.unparse(iter_)}"


def constructs(fn: ast.AST) -> list[Construct]:
    """Every loop, comprehension generator, fold and non-free call in `fn`'s body, each with
    the loops that enclose it. Nested functions and lambdas are read where they stand."""
    out: list[Construct] = []

    def walk(node: ast.AST, loops: list[str]) -> None:
        for child in ast.iter_child_nodes(node):
            visit(child, loops)

    def visit(node: ast.AST, loops: list[str]) -> None:
        if isinstance(node, (ast.For, ast.AsyncFor)):
            key = _loop_key(node.target, node.iter)
            out.append(Construct("loop", key, node, loops))
            visit(node.iter, loops)
            for s in node.body + node.orelse:
                visit(s, loops + [key])
            return
        if isinstance(node, ast.While):
            key = f"while {ast.unparse(node.test)}"
            out.append(Construct("loop", key, node, loops))
            visit(node.test, loops)
            for s in node.body + node.orelse:
                visit(s, loops + [key])
            return
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            inner = list(loops)
            for g in node.generators:
                key = _loop_key(g.target, g.iter)
                out.append(Construct("loop", key, g, inner))
                visit(g.iter, inner)
                inner = inner + [key]
                for cond in g.ifs:
                    visit(cond, inner)
            if isinstance(node, ast.DictComp):
                visit(node.key, inner)
                visit(node.value, inner)
            else:
                visit(node.elt, inner)
            return
        if isinstance(node, ast.Call):
            name = _callee(node)
            if name in FOLDS:
                over = node.args[0] if node.args else None
                # a fold over a comprehension is the comprehension's own loops
                if over is not None and not isinstance(
                        over, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                    out.append(Construct("fold", ast.unparse(node), node, loops))
            elif not (name in FREE or (name in FREE_WITH_ARGS and (node.args or node.keywords))):
                out.append(Construct("call", ast.unparse(node), node, loops))
            visit(node.func, loops)
            for a in node.args:
                visit(a, loops)
            for k in node.keywords:
                visit(k.value, loops)
            return
        walk(node, loops)

    for s in getattr(fn, "body", []):
        visit(s, [])
    return out


def resolve(code: str, root: Path) -> ast.AST:
    """`path.py::name` or `path.py::Class.method`, parsed from `root`."""
    path, _, qual = str(code).partition("::")
    try:
        tree = ast.parse((root / path).read_text(encoding="utf-8"))
    except OSError as e:
        raise ValueError(f"{code}: cannot read {path} under {root} ({e})") from e
    scope: Any = tree
    for part in qual.split("."):
        found = next((n for n in getattr(scope, "body", [])
                      if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                      and n.name == part), None)
        if found is None:
            raise ValueError(f"{code}: no definition named {part!r} in {path}")
        scope = found
    return scope


# --- the derivation ------------------------------------------------------------------------


def _matches(line: dict, c: Construct) -> bool:
    at = line.get("at")
    if at is not None:
        at = str(at)
        if not (c.key == at or c.key.startswith(at) or (c.kind == "call" and c.callee == at)):
            return False
    calls = line.get("calls")
    if calls is not None and c.callee != str(calls):
        return False
    args = line.get("args")
    if args is not None and c.args != int(args):
        return False
    kind = line.get("kind")
    if kind is not None and c.kind != str(kind):
        return False
    return at is not None or calls is not None


class _Derivation:
    def __init__(self, model: Node, root: Path):
        self.model = model
        self.root = root
        self.sizes = {c.id: c for c in model.children if c.kind == "size-var"}
        self.bounds: dict[str, Node] = {}
        for c in model.children:
            if c.kind == "bound":
                self.bounds[str(c.payload.get("code") or c.id)] = c
            if c.kind == "action":
                for b in c.children:
                    if b.kind == "bound":
                        self.bounds[str(b.payload.get("code") or b.id)] = b
        self.claims: dict[str, dict[str, Bound]] = {}
        self.stack: list[str] = []
        self.diagnostics: list[str] = []
        self.notes: list[str] = []
        self.judged = 0
        self.asserted = 0
        self.vouched = 0

    def claim_of(self, node: Node) -> dict[str, Bound]:
        key = str(node.payload.get("code") or node.id)
        if key in self.claims:
            return self.claims[key]
        out = {}
        for dim, src in (node.payload.get("claims") or {}).items():
            out[dim] = parse(src, set(self.sizes), f"bound '{node.id}' {dim}")
        self.claims[key] = out
        return out

    def _fn(self, node: Node) -> ast.AST:
        src = node.payload.get("source")
        if src is not None:
            tree = ast.parse(str(src))
            fns = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            if not fns:
                raise ValueError(f"bound '{node.id}': its source defines no function")
            return fns[0]
        return resolve(str(node.payload.get("code") or ""), self.root)

    def _size(self, src: Any, where: str) -> Bound:
        return parse(str(src), set(self.sizes), where)

    def _line_bound(self, line: dict, where: str) -> dict[str, Bound]:
        if "of" in line:
            target = self.bounds.get(str(line["of"]))
            if target is None:
                raise ValueError(f"{where}: `of` names {line['of']!r}, which no bound derives")
            if str(line["of"]) in self.stack:
                raise ValueError(f"{where}: `of` {line['of']!r} is circular")
            return self.claim_of(target)
        b = line.get("bound")
        if b is None:
            return {}
        if isinstance(b, str):
            return {"compute": self._size(b, where)}
        return {dim: self._size(src, f"{where} {dim}") for dim, src in b.items()}

    def check(self, node: Node) -> None:
        name = str(node.payload.get("code") or node.id)
        where = f"bound '{node.id}'"
        self.stack.append(name)
        try:
            claims = self.claim_of(node)
            fn = self._fn(node)
            cs = constructs(fn)
            lines = list(node.payload.get("derivation") or [])
            loop_size: dict[str, Bound] = {}
            total: dict[str, Bound] = {}
            matched = [False] * len(lines)

            def spend(dim: str, b: Bound, loops: list[str]) -> None:
                for k in loops:
                    b = mul(b, loop_size.get(k, ONE))
                total[dim] = add(total.get(dim, ZERO), b)

            # loops first: their sizes scale what they enclose
            for c in cs:
                if c.kind != "loop":
                    continue
                hits = [i for i, ln in enumerate(lines) if _matches(ln, c)]
                if not hits:
                    self.diagnostics.append(
                        f"{where}: uncovered loop at line {c.line}: `{c.key}` - give it a size")
                    loop_size[c.key] = ONE
                    continue
                ln = lines[hits[0]]
                for i in hits:
                    matched[i] = True
                if "size" not in ln:
                    self.diagnostics.append(f"{where}: the line for `{c.key}` states no size")
                    loop_size[c.key] = ONE
                    continue
                size = self._size(ln["size"], f"{where} `{c.key}`")
                loop_size[c.key] = size
                self._vouch(ln, c, size)
            for c in cs:
                if c.kind == "loop":
                    spend("compute", loop_size[c.key], c.loops)
                    if isinstance(c.node, ast.comprehension):
                        pass   # the allocation is the enclosing comprehension's; the elt pays
                    continue
                hits = [i for i, ln in enumerate(lines) if _matches(ln, c)]
                if not hits:
                    self.diagnostics.append(
                        f"{where}: uncovered {c.kind} at line {c.line}: `{c.key[:90]}` - "
                        f"{'give it a size' if c.kind == 'fold' else 'bound it, or name it free'}")
                    continue
                ln = lines[hits[0]]
                for i in hits:
                    matched[i] = True
                if c.kind == "fold":
                    if "size" not in ln:
                        self.diagnostics.append(f"{where}: the line for `{c.key[:60]}` states no size")
                        continue
                    size = self._size(ln["size"], f"{where} `{c.key[:60]}`")
                    work = mul(size, [{v: (0, 1)} for m in size for v in m] or ONE) \
                        if c.callee in LOGGED else size
                    spend("compute", work, c.loops)
                    if c.callee in ALLOCATING:
                        spend("memory", size, c.loops)
                    self._vouch(ln, c, size)
                else:
                    for dim, b in self._line_bound(ln, f"{where} `{c.key[:60]}`").items():
                        spend(dim, b, c.loops)
            # comprehensions allocate what they build
            for c in cs:
                if c.kind == "loop" and isinstance(c.node, ast.comprehension):
                    pass
            for i, ln in enumerate(lines):
                if not matched[i]:
                    self.diagnostics.append(
                        f"{where}: the line {ln.get('at') or ln.get('calls')!r} matches no "
                        "construct of the code - stale, or misspelt")
            for dim, b in total.items():
                self.judged += 1
                if dim not in claims:
                    if b != ZERO:
                        self.diagnostics.append(
                            f"{where}: spends {show(b)} in {dim}, a dimension its claim does "
                            "not state")
                    continue
                if not under(b, claims[dim]):
                    self.diagnostics.append(
                        f"{where} {dim}: derived {show(b)}, claimed {show(claims[dim])}")
            for dim in claims:
                if dim not in total:
                    self.judged += 1
        except ValueError as e:
            self.diagnostics.append(str(e))
        finally:
            self.stack.pop()

    def _vouch(self, ln: dict, c: Construct, size: Bound) -> None:
        """A loop's size the drawing vouches for: its iterable is one a size-var `holds`."""
        iter_text = c.key.partition(" in ")[2] if c.kind == "loop" else ""
        if c.kind == "fold" and isinstance(c.node, ast.Call) and c.node.args:
            iter_text = ast.unparse(c.node.args[0])
        names = {v for m in size for v in m}
        held = any(iter_text and iter_text in (self.sizes[v].payload.get("holds") or [])
                   for v in names)
        if held or not names:
            self.vouched += 1
        else:
            self.asserted += 1
            if not ln.get("because"):
                self.notes.append(f"bound: `{c.key[:60]}` sized {show(size)} by assertion, "
                                  "with no `because` and no size-var holding its iterable")


def model_bound(tree: Quern | TreeStore, path: str) -> Conformance:
    """How many bounds under the model at `path` are not proven: a construct no line
    covers, a line no construct has, a size or class in a name no size-var declares, a
    circular `of`, or a derived total past the claim in any dimension."""
    model = get_node(tree, path)
    if model is None or model.kind != "model":
        raise ValueError(f"no model at '{path}'")
    root = Path(str(model.payload.get("code_root") or os.environ.get("EPURE_CODE_ROOT") or "."))
    d = _Derivation(model, root)
    if not d.bounds:
        return Conformance(check="model/bound", violations=0,
                           notes=[f"model '{model.id}': no bound to derive"])
    for b in d.bounds.values():
        d.check(b)
    notes = list(d.notes)
    if d.asserted:
        notes.append(f"model '{model.id}': {d.asserted} size(s) asserted by a line, "
                     f"{d.vouched} vouched for by a size-var's `holds`")
    return Conformance(check="model/bound", violations=len(d.diagnostics),
                       diagnostics=d.diagnostics, notes=notes, judged=d.judged)


def model_bound_count(tree, path) -> float:
    return float(model_bound(tree, path).violations)


from .spec import SEMANTIC_MODEL_SPEC  # noqa: E402

register_native("model/bound", model_bound_count, SEMANTIC_MODEL_SPEC["model/bound"])
