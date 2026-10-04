"""Cost: what one occurrence of an action may spend, stated on the drawing in terms of the
data's size, proven over the model, and held on every tape.

Time is a symptom; complexity is what a drawing can hold. Reads, writes and payload bytes are
exact properties of (code, recorded world): a replay asks the same questions in the same order,
so they are deterministic where a call's milliseconds are not. semantic-model@0.18.0 gives them
a vocabulary — `size-var` on the model (a dimension the data grows along, projected from the
store like a state-var and never enumerated by the prover) and `cost` on the action (exprs over
the size-vars for `reads`, `writes`, `bytes`, optionally `compute`) — and this module holds
them two ways, the same split as everything else here:

- `model/cost` — PROVEN over the model, symbolically: each cost expr is read as a polynomial
  in the size-vars, and its degree in each is held to the growth that size-var allows
  (`growth`: constant, linear, any). An expr naming a variable no size-var declares, a cost
  stating no reads, writes or bytes, and a model with costs but no boundary that says which
  doors read — all red on the drawing, before any tape.
- `conduct/cost` — CHECKED on every tape: inside each act the raw events through the
  boundary's read doors are counted as documents (a batched read counts the items it
  returned, at least one), through its write doors as writes, and the bytes of what crossed
  (a read's result, a write's arguments, as JSON) as bytes; the size-vars are projected from
  the latest read that shows each, at or before the act; the action's exprs are evaluated at
  those sizes, and an act that spent more than its cost allows is named with the act, the
  dimension, the count and the sizes. A size no read witnessed is a note — unwitnessed, never
  a pass — which is what the witness-coverage debt in the ledger is about.

`compute` is held the same way when the boundary names `compute` doors (0.19.0): the events
through them carry an instruction count as `ops` - a recorder's, written at record or replay
time, never in production - and the act's sum is held to the `compute` expr. A model with no
compute door leaves a stated compute unheld, and the check says so once. Whose instructions a
count is (which code, which interpreter) is the recorder's to say; a replay-time counter per
span and per code object is still a named debt (epure/tree.py).
"""

from __future__ import annotations

import ast
import json
from typing import Any

from quern import Node, Quern, TreeStore, register_native

from epure.behavior import _Act, _Model, _Projection, _acts_and_stream, _through, doors
from epure.conformance import Conformance, _confront, get_node
from epure.prove import _ENV, _LITERALS, _compile

DIMENSIONS = ("reads", "writes", "bytes")
OPTIONAL = ("compute",)
GROWTHS = {"constant": 0, "linear": 1, "any": 10 ** 6}

# --- the drawing: a cost expr as a polynomial in the size-vars -------------------------------


def growth(expr: str) -> dict[str, int]:
    """The degree of `expr` in each variable it names: {} for a constant, {"n": 1} for one
    linear in n, {"n": 2} for n * n. Sums take the greater degree, products add, a division
    by a variable subtracts (never below zero), min/max/abs take the greater of their
    arguments. Comparisons and booleans are constants. Raises ValueError on anything the
    rule grammar would not evaluate."""
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"cost expr {expr!r}: {e.msg}") from e
    return _degree(tree.body, expr)


def _merge(a: dict[str, int], b: dict[str, int], how) -> dict[str, int]:
    return {k: how(a.get(k, 0), b.get(k, 0)) for k in set(a) | set(b)}


def _degree(node: ast.AST, expr: str) -> dict[str, int]:
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float, bool)):
            return {}
        raise ValueError(f"cost expr {expr!r}: a cost is a number, not {node.value!r}")
    if isinstance(node, ast.Name):
        if node.id in _LITERALS:
            return {}
        return {node.id: 1}
    if isinstance(node, ast.UnaryOp):
        return _degree(node.operand, expr)
    if isinstance(node, ast.BinOp):
        left, right = _degree(node.left, expr), _degree(node.right, expr)
        if isinstance(node.op, (ast.Add, ast.Sub)):
            return _merge(left, right, max)
        if isinstance(node.op, ast.Mult):
            return _merge(left, right, lambda x, y: x + y)
        if isinstance(node.op, ast.Div):
            return {k: v for k, v in _merge(left, right, lambda x, y: x - y).items() if v > 0}
        raise ValueError(f"cost expr {expr!r}: operator not in the rule grammar")
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
            and node.func.id in ("min", "max", "abs"):
        out: dict[str, int] = {}
        for a in node.args:
            out = _merge(out, _degree(a, expr), max)
        return out
    if isinstance(node, (ast.Compare, ast.BoolOp)):
        return {}
    raise ValueError(f"cost expr {expr!r}: {type(node).__name__} is not a cost")


def _size_vars(model: Node) -> dict[str, Node]:
    return {c.id: c for c in model.children if c.kind == "size-var"}


def _costs(model: Node) -> list[tuple[Node, Node]]:
    return [(a, c) for a in model.children if a.kind == "action"
            for c in a.children if c.kind == "cost"]


def _boundary_doors(model: Node, which: str) -> list:
    return [d for c in model.children if c.kind == "boundary"
            for d in doors(c.payload.get(which))]


def model_cost(tree: Quern | TreeStore, path: str) -> Conformance:
    """How many cost statements on the model at `path` are not a drawing anyone can hold a
    tape to: a dimension unstated, a variable no size-var declares, an expr that will not
    parse, or growth past what the size-var allows; and the model itself, once, when it
    states costs and no boundary says which doors read or write."""
    model = get_node(tree, path)
    if model is None or model.kind != "model":
        raise ValueError(f"no model at '{path}'")
    sizes = _size_vars(model)
    allowed = {}
    diagnostics: list[str] = []
    for sid, s in sizes.items():
        g = str(s.payload.get("growth") or "linear")
        if g not in GROWTHS:
            diagnostics.append(f"size-var '{sid}': growth {g!r} is not constant, linear or any")
            g = "linear"
        allowed[sid] = GROWTHS[g]
    costs = _costs(model)
    judged = 0
    for action, cost in costs:
        for dim in DIMENSIONS:
            judged += 1
            src = cost.payload.get(dim)
            if src is None:
                diagnostics.append(f"action '{action.id}': its cost states no {dim} — "
                                   "nothing that grows with the data may go unstated")
                continue
            try:
                degrees = growth(str(src))
            except ValueError as e:
                diagnostics.append(f"action '{action.id}' {dim}: {e}")
                continue
            for var, deg in sorted(degrees.items()):
                if var not in sizes:
                    diagnostics.append(f"action '{action.id}' {dim}: names '{var}', which no "
                                       "size-var of the model declares")
                elif deg > allowed[var]:
                    diagnostics.append(f"action '{action.id}' {dim}: degree {deg} in '{var}', "
                                       f"past the {s_growth(sizes[var])} growth it allows")
        for dim in OPTIONAL:
            src = cost.payload.get(dim)
            if src is not None:
                try:
                    for var in growth(str(src)):
                        if var not in sizes:
                            diagnostics.append(f"action '{action.id}' {dim}: names '{var}', "
                                               "which no size-var of the model declares")
                except ValueError as e:
                    diagnostics.append(f"action '{action.id}' {dim}: {e}")
    notes: list[str] = []
    if costs and not _boundary_doors(model, "reads") and not _boundary_doors(model, "writes"):
        notes.append(f"model '{model.id}': states costs and no boundary names the doors that "
                     "read or write — the drawing holds, and conduct/cost could count nothing "
                     "on a tape")
    return Conformance(check="model/cost", violations=len(diagnostics),
                       diagnostics=diagnostics, notes=notes, judged=judged)


def s_growth(size: Node) -> str:
    return str(size.payload.get("growth") or "linear")


# --- the tape: what each act spent, against what its action allows at the tape's sizes -------


def _items(event: dict[str, Any]) -> int:
    """Documents a read returned: a batched read counts each item, a single read counts one
    whether or not the document existed (a store bills the question, not the answer)."""
    res = event.get("res")
    return max(1, len(res)) if isinstance(res, list) else 1


def _bytes(event: dict[str, Any], read: bool) -> int:
    try:
        if read:
            return len(json.dumps(event.get("res"), ensure_ascii=False, default=str))
        return (len(json.dumps(event.get("args") or [], ensure_ascii=False, default=str))
                + len(json.dumps(event.get("kwargs") or {}, ensure_ascii=False, default=str)))
    except (TypeError, ValueError):
        return 0


def _ops(event: dict[str, Any]) -> int:
    """The instruction count a compute event carries; a count that is not a number is 0."""
    try:
        return int(event.get("ops") or 0)
    except (TypeError, ValueError):
        return 0


def _sizes_at(sizes: dict[str, _Projection], stream: list, upto: tuple) -> dict[str, Any]:
    """Each size as the latest read at or before `upto` shows it; absent when none does."""
    out: dict[str, Any] = {}
    for sid, proj in sizes.items():
        for at, e in reversed(stream):
            if at > upto:
                continue
            if not _through(e, proj.doors):
                continue
            try:
                v = proj.value(e)
            except ValueError:
                continue
            if v is not None:
                out[sid] = v
                break
    return out


def conduct_cost(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many acts under `path` spent more than their action's cost allows at the sizes the
    tape shows. Per act (a whole call and each top-level span, when an action binds it) and
    per stated dimension: the raw events through the boundary's read doors, counted as
    documents; through its write doors, as writes; and the bytes of what crossed. A size no
    read at or before the act witnessed is a note — the act is unjudged in it."""
    node, model_node = _confront(tree, path, rel)
    model = _Model(model_node)
    reads = _boundary_doors(model_node, "reads")
    writes = _boundary_doors(model_node, "writes")
    compute = _boundary_doors(model_node, "compute")
    sizes = {sid: _Projection(sid, s.payload["shown"], None)
             for sid, s in _size_vars(model_node).items() if s.payload.get("shown")}
    unshown = [sid for sid in _size_vars(model_node) if sid not in sizes]
    costs = {a.id: c for a, c in _costs(model_node)}
    exprs: dict[tuple[str, str], Any] = {}
    held = DIMENSIONS + (OPTIONAL if compute else ())
    for aid, c in costs.items():
        for dim in held:
            if c.payload.get(dim) is not None:
                exprs[(aid, dim)] = _compile(str(c.payload[dim]), f"cost of '{aid}' {dim}")
    acts, stream = _acts_and_stream(node, path, calls=True)
    diagnostics: list[str] = []
    notes: list[str] = []
    judged = 0
    if not reads and not writes and not compute:
        notes.append(f"model '{model_node.id}': no boundary names the doors that read or "
                     "write — nothing counted")
        return Conformance(check="conduct/cost", violations=0, notes=notes)
    unheld = [aid for aid, c in costs.items() if c.payload.get("compute") is not None]
    if unheld and not compute:
        notes.append(f"model '{model_node.id}': {len(unheld)} cost(s) state compute and no "
                     "boundary names a compute door — stated, unheld")
    for act in acts:
        for action in model.bound(act.span):
            if action.id not in costs:
                continue
            at = _sizes_at(sizes, stream, act.to)
            counted = {"reads": 0, "writes": 0, "bytes": 0, "compute": 0}
            for _, e in act.events:
                if _through(e, reads):
                    counted["reads"] += _items(e)
                    counted["bytes"] += _bytes(e, read=True)
                elif _through(e, writes):
                    counted["writes"] += 1
                    counted["bytes"] += _bytes(e, read=False)
                elif compute and _through(e, compute):
                    counted["compute"] += _ops(e)
            for dim in held:
                run = exprs.get((action.id, dim))
                if run is None:
                    continue
                try:
                    allowed = run({**at, **_LITERALS}, _ENV)
                except (KeyError, ValueError, TypeError, NameError) as e:
                    missing = [s for s in list(unshown) + list(sizes) if s not in at]
                    notes.append(f"{act.path}: '{act.span.kind}' ({action.id}) {dim} — "
                                 f"unwitnessed: no read at or before the act shows "
                                 f"{', '.join(missing) or 'its sizes'} ({e})")
                    continue
                judged += 1
                if counted[dim] > allowed:
                    where = ", ".join(f"{k}={v}" for k, v in sorted(at.items())) or "no size"
                    diagnostics.append(
                        f"{act.path}: '{act.span.kind}' ({action.id}) spent {counted[dim]} "
                        f"{dim}; its cost allows {allowed:g} at {where}")
    return Conformance(check="conduct/cost", violations=len(diagnostics),
                       diagnostics=diagnostics, notes=notes, judged=judged)


def model_cost_count(tree, path) -> float:
    return float(model_cost(tree, path).violations)


def conduct_cost_count(tree, path, rel) -> float:
    return float(conduct_cost(tree, path, rel).violations)


from .spec import CONDUCT_SPEC, SEMANTIC_MODEL_SPEC  # noqa: E402

register_native("model/cost", model_cost_count, SEMANTIC_MODEL_SPEC["model/cost"])
register_native("conduct/cost", conduct_cost_count, CONDUCT_SPEC["conduct/cost"])
