"""The three conformance natives — code <= model, checked mechanically on every tape.

`model/prove` establishes what the model promises; these establish that the running system is
still the thing the model describes. Never proven, so checked on *every* execution, each from
a different angle:

- **model/licensed** — testimony is justified by evidence: every span's claim is convicted or
  acquitted by raw boundary events, per its event-kind's license — its own window by default,
  or evidence NAMED along its lineage (`evidence(pattern, 'enclosing')`): a wider gaze must
  name what it looks for, or widening would quietly license everything.
- **model/total** — no raw event escapes semantics: a boundary exchange no span encloses is
  something the system did that the model does not know it can do. The strongest and
  easiest-to-skip check; silence is a lie.
- **model/refines** — the semantic trace is a behavior of the model: the span sequence, run
  through the automaton, takes only transitions the model admits, and every invariant holds
  at every step — which is what makes a predicate violation in the wild impossible without a
  refinement violation first.

Each is a pure, deterministic function of (tree slice, model) returning a **count of
violations**, so the canonical rule shape is `solve('model/<check>', self, 'model') == 0` —
the same `(path, rel)` composition `grounding/untrusted_via` uses. The convention (the tape
importer's output plus one edit): an imported `scenario`/`session` node carries a link
`model` -> the root of the semantic model it claims to refine. A node that names no model, or
two, is a refusal — a conformance question with nothing to conform to must not read as a pass.

Importing this module is the door: it registers the three natives (and, through
`epure.prove`, the fourth contract of the family) and nothing else. The rich results — every
diagnostic, each naming its offender by path — come from `licensed`/`total`/`refines`
directly; the natives are their counts.

Refinement consumes **top-level spans only** (the direct children of each scenario): a nested
span is its parent act's own decomposition, evidence for licensing, never a second transition
— the decision and the flattening it rejected are journaled in `epure.tree`. A session
refines as one continuous behavior, its scenarios' top-level spans concatenated in tape
order: the calls of one recording ran against one accumulating state, and restarting the
automaton per call would silently forgive exactly the cross-call divergences worth catching.
Refinement stops at the first divergent span: past that point the state is one the model no
longer vouches for, and verdicts computed against it would be noise wearing diagnostics'
clothes. And v0 requires the trace to instantiate actions *deterministically* — a span whose
event-kind enables two actions at once is reported, not guessed about.
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Any, Callable

from pydantic import BaseModel, Field

from quern import Node, Quern, TreeStore, get_node, register_native

from epure.prove import _ENV, _LITERALS, _compile, _domain

# The importer's structural kinds: containers of testimony, never testimony themselves.
_STRUCTURE = ("session", "scenario")


class Conformance(BaseModel):
    """One check's verdict over one slice: how many violations, and each offender named."""

    check: str
    violations: int
    diagnostics: list[str] = Field(default_factory=list)


# --- the convention: one slice, one model ---------------------------------------------


def _confront(tree: Quern | TreeStore, path: str, rel: str) -> tuple[Node, Node]:
    """The (slice, model) pair a check confronts. Exactly one model, and a real one:
    a slice claiming none is unjudgeable, and unjudgeable must never read as green."""
    node = get_node(tree, path)
    if node is None:
        raise ValueError(f"no node at '{path}'")
    targets = node.links.get(rel, [])
    if len(targets) != 1:
        raise ValueError(
            f"'{path}' links '{rel}' to {len(targets)} node(s) — a conformance check "
            "confronts exactly one model; a slice that names none is not passing, "
            "it is unjudged")
    model = get_node(tree, targets[0])
    if model is None or model.kind != "model":
        raise ValueError(f"'{path}' links '{rel}' to '{targets[0]}', which is not a model")
    return node, model


def _events(model: Node) -> dict[str, dict[str, Any]]:
    """The alphabet: event-kind id -> declared args and compiled licenses."""
    out: dict[str, dict[str, Any]] = {}
    for c in model.children:
        if c.kind != "event-kind":
            continue
        out[c.id] = {
            "args": list(c.payload.get("args") or {}),
            "licenses": [(lc.id, _compile(lc.payload.get("expr", ""),
                                          f"license '{lc.id}' of event-kind '{c.id}'"))
                         for lc in c.children if lc.kind == "license"],
        }
    return out


def _automaton(model: Node) -> tuple[list[tuple[str, list[Any], Any]],
                                     list[dict[str, Any]],
                                     list[tuple[str, Callable]]]:
    """The transition system, compiled: (state-vars, actions, invariants). Same reading
    of the same payloads as `model/prove` — one grammar, one evaluator, and here one
    loader family, so the automaton a tape is judged by IS the object that was proven."""
    variables: list[tuple[str, list[Any], Any]] = []
    for c in model.children:
        if c.kind != "state-var":
            continue
        dom = _domain(c.payload, f"state-var '{c.id}'")
        init = c.payload.get("init")
        if init not in dom:
            raise ValueError(f"state-var '{c.id}': init {init!r} is outside its own domain")
        variables.append((c.id, dom, init))
    actions: list[dict[str, Any]] = []
    for c in model.children:
        if c.kind != "action":
            continue
        args = c.payload.get("args") or {}
        guard_src = c.payload.get("guard", "")
        actions.append({
            "id": c.id,
            "args": {n: _domain(args[n], f"action '{c.id}' arg '{n}'") for n in args},
            "guard": (_compile(guard_src, f"action '{c.id}' guard") if guard_src
                      else (lambda _env: True)),
            "updates": [(u["var"], _compile(u["expr"],
                                            f"action '{c.id}' update of '{u['var']}'"))
                        for u in c.payload.get("updates") or []],
            "events": [o.payload.get("event") for o in c.children
                       if o.kind == "observation"],
        })
    invariants = [(c.id, _compile(c.payload.get("expr", ""), f"invariant '{c.id}'"))
                  for c in model.children if c.kind == "invariant"]
    return variables, actions, invariants


def _normalize(value: Any) -> Any:
    """The grammar's numbers are floats; domains are declared in ints."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


# --- model/licensed: testimony is justified by evidence -------------------------------


def _named(event: dict[str, Any]) -> str:
    """A raw event's name, as the estate already reads one: the called function for an
    effect, the operation for a store exchange, the kind for everything else."""
    return str(event.get("fn") or event.get("op") or event.get("k") or "")


def licensed(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many spans under `path` claim more than the evidence their licenses name.

    Every testimony node — top-level acts, nested decomposition, points alike — is held to
    its event-kind's licenses, each expr evaluated with the event's declared args bound from
    the span's data and two evidence readers in the environment:

    - `ctx('events')` — the claiming span's OWN raw window, exactly as in v0.
    - `evidence(pattern, scope='own')` — the raw events whose name (fn / op / k) matches the
      fnmatch `pattern`; scope `'enclosing'` widens the pool to the claim's lineage: its own
      window plus every raw event a testimony ancestor directly encloses, outermost first.

    The cut is deliberate: a license may look beyond its own window ONLY by naming what it
    looks for — a bare count over an ancestor's window would be satisfied by any unrelated
    I/O above the claim, which is the `true` expr with extra steps. Structural nodes
    contribute nothing to any lineage: raw events parked on a scenario are totality
    violations, and behavior the model does not know exists must never license a claim.

    A kind naming no event-kind of the model counts too: unknown testimony is unlicensed by
    definition. Each offending span counts once, whatever the number of its failures.
    """
    node, model = _confront(tree, path, rel)
    alphabet = _events(model)
    diagnostics: list[str] = []

    def judge(p: str, span: Node, lineage: list[dict[str, Any]]) -> None:
        entry = alphabet.get(span.kind)
        if entry is None:
            diagnostics.append(f"{p}: '{span.kind}' names no event-kind of the model — "
                               "unknown testimony is unlicensed by definition")
            return
        data = span.payload.get("data") or {}
        missing = [a for a in entry["args"] if a not in data]
        if missing:
            diagnostics.append(f"{p}: '{span.kind}' claims without its declared "
                               f"arg(s) {missing} — the testimony is not even well-formed")
            return
        window = span.payload.get("events") or []

        def ctx(name: str, scope: str | None = None, _w=window):
            if scope is not None:
                raise ValueError("ctx sees the claiming span's own raw events and nothing "
                                 "else — a license that reaches beyond its own window "
                                 "names its evidence: evidence(pattern, 'enclosing')")
            if name != "events":
                raise ValueError(f"nothing named '{name}' in a license's context — "
                                 "it sees the claiming span's raw events and nothing else")
            return _w

        def evidence(pattern: str, scope: str = "own", _w=window, _lineage=lineage):
            if scope == "own":
                pool = _w
            elif scope == "enclosing":
                pool = _lineage + _w
            else:
                raise ValueError(f"unknown evidence scope '{scope}' — a license looks in "
                                 "'own' (the claiming span's window) or 'enclosing' "
                                 "(its window plus its testimony ancestors')")
            return [e for e in pool if fnmatch(_named(e), pattern)]

        env = {**_ENV, "ctx": ctx, "evidence": evidence}
        variables = {**{a: data[a] for a in entry["args"]}, **_LITERALS}
        for lid, expr in entry["licenses"]:
            try:
                ok = expr(variables, env)
            except ValueError as e:
                diagnostics.append(f"{p}: '{span.kind}' license '{lid}' cannot be "
                                   f"evaluated against this claim: {e}")
                break
            if not ok:
                diagnostics.append(
                    f"{p}: '{span.kind}' license '{lid}' is not satisfied by the "
                    f"{len(window)} raw event(s) the span encloses "
                    f"({len(lineage)} more along its lineage)")
                break

    def walk(p: str, span: Node, lineage: list[dict[str, Any]]) -> None:
        if span.kind in _STRUCTURE:
            for c in span.children:
                walk(f"{p}/{c.id}", c, [])
            return
        judge(p, span, lineage)
        below = lineage + (span.payload.get("events") or [])
        for c in span.children:
            walk(f"{p}/{c.id}", c, below)

    walk(path, node, [])
    return Conformance(check="model/licensed", violations=len(diagnostics),
                       diagnostics=diagnostics)


# --- model/total: no raw event escapes semantics ---------------------------------------


def total(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many raw boundary events under `path` are enclosed by no span.

    The importer parks these on each scenario's own payload; every one is something the
    system did at the boundary that the model does not know it can do. The model link is
    validated like the others' — the count does not read the model, but a slice that names
    none has opted out of the family, and this check must not be the quiet exception.
    """
    _confront(tree, path, rel)
    diagnostics: list[str] = []
    for p, node in tree.walk(path):
        if node.kind != "scenario":
            continue
        for e in node.payload.get("events") or []:
            diagnostics.append(f"{p}: raw '{e.get('k', '?')}' event enclosed by no span — "
                               "boundary behavior the model does not know exists")
    return Conformance(check="model/total", violations=len(diagnostics),
                       diagnostics=diagnostics)


# --- model/refines: the semantic trace is a behavior of the model ----------------------


def refines(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """Whether the trace under `path` is a legal path of the model — 0 or 1, with the
    first divergent span named: which guard or invariant, in which state.

    Top-level spans only (see the module docstring and the journaled decision); a session's
    scenarios refine as one continuous behavior. Each act must instantiate exactly one
    enabled action among those `observed-as` its event-kind, args bound from the span's
    data and inside their declared domains; its updates (pre-state, simultaneous — the
    prover's semantics, necessarily) must stay in domain; every invariant must hold after.
    """
    node, model = _confront(tree, path, rel)
    variables, actions, invariants = _automaton(model)
    state = {name: init for name, _, init in variables}

    scenarios = ([(f"{path}/{c.id}", c) for c in node.children]
                 if node.kind == "session" else [(path, node)])
    trace = [(f"{sp}/{c.id}", c) for sp, s in scenarios for c in s.children]

    def divergence(why: str) -> Conformance:
        return Conformance(check="model/refines", violations=1, diagnostics=[
            why + f" — state at failure: {state}"])

    for p, span in trace:
        candidates = [a for a in actions if span.kind in a["events"]]
        if not candidates:
            return divergence(f"{p}: '{span.kind}' is not testimony to any action of the "
                              "model (unknown or unwitnessed event kind)")
        data = span.payload.get("data") or {}
        enabled: list[tuple[dict[str, Any], dict[str, Any]]] = []
        reasons: list[str] = []
        for a in candidates:
            binding: dict[str, Any] = {}
            reason = ""
            for arg, dom in a["args"].items():
                if arg not in data:
                    reason = f"'{a['id']}' needs arg '{arg}', absent from the span's data"
                    break
                value = _normalize(data[arg])
                if value not in dom:
                    reason = (f"'{a['id']}' arg '{arg}' = {value!r} is outside its "
                              "declared domain")
                    break
                binding[arg] = value
            if reason:
                reasons.append(reason)
                continue
            env = {**state, **binding, **_LITERALS}
            try:
                held = a["guard"](env)
            except ValueError as e:
                reasons.append(f"'{a['id']}' guard cannot be evaluated: {e}")
                continue
            if held:
                enabled.append((a, binding))
            else:
                reasons.append(f"'{a['id']}' guard is false")
        if not enabled:
            return divergence(f"{p}: '{span.kind}' instantiates no enabled action "
                              f"({'; '.join(reasons)})")
        if len(enabled) > 1:
            return divergence(
                f"{p}: '{span.kind}' instantiates {len(enabled)} enabled actions "
                f"({', '.join(a['id'] for a, _ in enabled)}) — v0 refines deterministic "
                "traces only; disambiguate the guards or split the event kinds")
        action, binding = enabled[0]
        env = {**state, **binding, **_LITERALS}
        succ = dict(state)
        for var, expr in action["updates"]:
            value = _normalize(expr(env))
            if var not in succ:
                return divergence(f"{p}: action '{action['id']}' updates '{var}', "
                                  "which no state-var declares")
            dom = next(d for name, d, _ in variables if name == var)
            if value not in dom:
                return divergence(f"{p}: action '{action['id']}' drives '{var}' to "
                                  f"{value!r}, outside its domain")
            succ[var] = value
        state = succ
        inv_env = {**state, **_LITERALS}
        for inv, expr in invariants:
            if not expr(inv_env):
                return divergence(f"{p}: invariant '{inv}' is violated after "
                                  f"'{span.kind}' ('{action['id']}')")
    return Conformance(check="model/refines", violations=0)


# --- the natives: counts behind solve() -------------------------------------------------


def licensed_count(tree: Quern | TreeStore, path: str, rel: str) -> float:
    return float(licensed(tree, path, rel).violations)


def total_count(tree: Quern | TreeStore, path: str, rel: str) -> float:
    return float(total(tree, path, rel).violations)


def refines_count(tree: Quern | TreeStore, path: str, rel: str) -> float:
    return float(refines(tree, path, rel).violations)


register_native("model/licensed", licensed_count)
register_native("model/total", total_count)
register_native("model/refines", refines_count)
