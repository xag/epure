"""The conduct natives — the behavior laws of `epure.conduct`, held against a tape.

`model/licensed`, `model/total` and `model/refines` establish that a recorded run is a
behavior of the model. These establish something the model's automaton cannot see: that the
REAL system's writes and reads agree with what each action declared it does. A refined trace
can be a perfect path of the automaton while the store underneath it lost a write, wrote the
wrong value, or wrote three things the act never admitted to — the automaton moves its own
variables and is satisfied. The conduct laws are about the world, and the world is only on the
tape as raw events; so these checks read the raw events, and they read them through the DOORS
an action declares (semantic-model@0.5.0): `via`, the write that materializes an effect, and
`shown_by`, the read through which the world shows it back.

Six natives. The first five read presences through doors; the sixth reads VALUES through
projections and is the one Hughes ranks first:

- **conduct/effect** — *the-effect-is-shown*. An act declaring `creates`/`mutates` encloses a
  `via` write, and a `shown_by` read after the act returns what that write carried; one
  declaring `deletes` encloses its `via` write, and no `shown_by` read after it still returns
  what an earlier effect on the same entity wrote (or names what the removal named).
- **conduct/faithful** — *the-effect-matches-its-inputs*. Every argument the effect's `from`
  names appears in what the `via` write carried.
- **conduct/frame** — *the-frame-holds*. Of the doors the model knows as writes (every `via`
  any effect or `touches` in it declares), an act passes only through those its own
  `touches.via` and its effects' `via` admit.
- **conduct/refusal** — *refusal-changes-nothing*. A span whose outcome is `error` encloses
  no write through any door the model knows.
- **conduct/checkable** — *the-effect-is-checkable*. On the model, not a tape: every effect
  names a state-var and both doors, every `touches.only` names state-vars.
- **conduct/agrees** — *the-world-agrees-with-the-model* (model-based). For every act bound
  to one action, and every state-var that declares a projection (`shown`: a read door and
  an expr over the read's result): project the world from the last reads BEFORE the act,
  apply the action's own updates, and compare with the world projected from the first reads
  AFTER it. Hoare's commuting diagram, Hughes's `toList (insert k v t) === L.insert (k, v)
  (toList t)`, read off a tape. A variable the action does not update must project the same
  value after as before — that is the frame law in its VALUE form; a variable it updates
  from an argument must project to that argument — faithfulness in its value form; the
  entity's projected value after must be what the update computed — the effect law in its
  value form.

THE CALL IS AN ACT. flight-recorder instruments every tool call completely — its name, its
inputs, every boundary event — so a call is testimony too: its kind is the tool's name, its
data the kwargs, its window the whole call. A model that declares an event-kind named for a
tool (witnessed by an action, usually a no-op with a `touches` boundary) binds the call the
way it binds a span, and the frame and refusal laws then hold the tool's OWN writes — the
ones outside any domain span, which totality used to be the only check to count. The
boundary of a call admits its own doors plus those of every act it encloses: a write inside
a domain span answers to that span's declaration, a write outside answers to the tool's.
Refinement is unchanged — the automaton moves by the domain acts, and a call binds no
transition. A call the model does not name is counted, never judged: the suite reports
declared calls over all calls, which is the coverage number.

What no native holds is on the census (`epure.census`), item by item, each owed to a debt
in the ledger with its discharge — never a sentence.

WHAT "AFTER" MEANS. The importer records every event's position in its call's stream and every
span's begin/end marks, so "after the act" is `(call index, position) > (call index, end)`,
across calls — one recording is one accumulating world. The horizon is the next act that
declares an effect on the same entity: a read past that point answers for that act, not this
one. A read through the door that never comes is NOT a violation: the law is convicted by a
read that disagrees, and a tape on which the app never looked says nothing either way — that
is reported as a note, counted apart, so a green that rests on silence is visible as such.

WHAT "SHOWS" MEANS. A write carries the container values among its arguments (a dict or a
list — a bare scalar has no identity to find again); a read shows one when its result contains
it, at any depth, as a structural subset (every key the write carried, with the value it
carried — a store that stamps fields of its own onto the document still shows the document).
For a removal, the identifiers are the string arguments of the removing write and the last
path segment of each, and showing is containing one as a key or as an `id`.

Every check is a pure function of (tree slice, model) returning a count, so the rule shape is
`solve('conduct/<check>', self, 'model') == 0`, the same `(path, rel)` composition as the
model/* family. Importing this module registers the five natives and nothing else.
"""

from __future__ import annotations

import json
from fnmatch import fnmatch
from typing import Any, Callable

from quern import Node, Quern, TreeStore, register_native

from epure.conformance import _STRUCTURE, Conformance, _automaton, _confront, _named, _normalize
from epure.prove import _ENV, _LITERALS, _compile, _domain

EFFECTS = ("creates", "mutates", "deletes")

Door = Callable[[dict[str, Any]], bool]


# --- doors: the binding from a model's words to a tape's events -------------------------


def _arg(event: dict[str, Any], key: str) -> Any:
    """A write's argument by kwarg name, or by positional index spelt as a string."""
    kwargs = event.get("kwargs") or {}
    if key in kwargs:
        return kwargs[key]
    args = event.get("args") or []
    if key.isdigit() and int(key) < len(args):
        return args[int(key)]
    return None


def _render(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def door(spec: Any) -> Door:
    """One door as a predicate over raw events: a name pattern, optionally narrowed by
    argument patterns. `{"event": "app.storage.put_field", "where": {"field": "done.*"}}`
    admits a field write to the completions map and nothing else."""
    if isinstance(spec, str):
        pattern, where = spec, {}
    elif isinstance(spec, dict):
        pattern, where = str(spec.get("event", "")), dict(spec.get("where") or {})
    else:
        raise ValueError(f"a door is a name pattern or {{event, where}}, not {spec!r}")
    if not pattern:
        raise ValueError(f"a door names the event it admits; {spec!r} names none")

    def admits(event: dict[str, Any]) -> bool:
        if not fnmatch(_named(event), pattern):
            return False
        for key, pat in where.items():
            value = _arg(event, key)
            if value is None or not fnmatch(_render(value), str(pat)):
                return False
        return True

    return admits


def doors(spec: Any) -> list[Door]:
    """Zero, one or several doors, as the declaration spelt them."""
    if spec is None:
        return []
    if isinstance(spec, list):
        return [door(s) for s in spec]
    return [door(spec)]


def _through(event: dict[str, Any], ds: list[Door]) -> bool:
    return any(d(event) for d in ds)


# --- what a write carries, and whether a read shows it ----------------------------------


def _carried(event: dict[str, Any]) -> list[Any]:
    """The values a write put into the world: its container arguments. A bare scalar has
    no identity to find again in a later read, so it is not a witness."""
    values = list(event.get("args") or []) + list((event.get("kwargs") or {}).values())
    return [v for v in values if isinstance(v, (dict, list)) and v]


def _subsumes(hay: Any, needle: Any) -> bool:
    """`needle` is a structural subset of `hay`: every key with its value (recursively),
    every list member somewhere in the list, scalars equal."""
    if isinstance(needle, dict):
        return isinstance(hay, dict) and all(
            k in hay and _subsumes(hay[k], v) for k, v in needle.items())
    if isinstance(needle, list):
        return isinstance(hay, list) and all(
            any(_subsumes(h, n) for h in hay) for n in needle)
    return hay == needle


def _within(hay: Any, needle: Any) -> bool:
    """`needle` appears in `hay` at any depth."""
    if _subsumes(hay, needle):
        return True
    if isinstance(hay, dict):
        return any(_within(v, needle) for v in hay.values())
    if isinstance(hay, list):
        return any(_within(v, needle) for v in hay)
    return False


def _identifiers(event: dict[str, Any]) -> list[str]:
    """What a removal named: its string arguments, and the last path segment of each."""
    out: list[str] = []
    for v in list(event.get("args") or []) + list((event.get("kwargs") or {}).values()):
        if isinstance(v, str) and v:
            out.append(v)
            tail = v.rstrip("/").rsplit("/", 1)[-1]
            if tail and tail != v:
                out.append(tail)
    return out


def _names(hay: Any, ident: str) -> bool:
    """`hay` still holds `ident` as a key, or as the value of an `id`."""
    if isinstance(hay, dict):
        if ident in hay or hay.get("id") == ident:
            return True
        return any(_names(v, ident) for v in hay.values())
    if isinstance(hay, list):
        return any(_names(v, ident) for v in hay)
    return False


# --- projections: the abstraction function, per state-var ---------------------------------


def _at(res: Any, path: str, default: Any = None) -> Any:
    """A dotted path into a read's result; `*` takes the first value of a map or list."""
    cur = res
    for part in [p for p in str(path).split(".") if p]:
        if isinstance(cur, dict):
            if part == "*":
                cur = next(iter(cur.values()), None)
            else:
                cur = cur.get(part)
        elif isinstance(cur, list):
            try:
                cur = cur[0] if part == "*" else cur[int(part)]
            except (ValueError, IndexError):
                cur = None
        else:
            cur = None
        if cur is None:
            return default
    return cur


def _members(xs: Any, *filters: Any) -> list[dict[str, Any]]:
    """The dict members of a map or list that match every (key, value) pair in `filters`."""
    members = list(xs.values()) if isinstance(xs, dict) else list(xs or [])
    pairs = list(zip(filters[0::2], filters[1::2]))
    return [m for m in members if isinstance(m, dict)
            and all(m.get(k) == v for k, v in pairs)]


def _count(xs: Any, *filters: Any) -> float:
    """`count(xs, key, value, key2, value2, ...)`: members matching every pair."""
    return float(len(_members(xs, *filters)))


def _latest(xs: Any, field: str, *filters: Any) -> Any:
    """`latest(xs, field, key, value, ...)`: the greatest `field` among matching members, or
    None when none match — the last day something was done, the newest stamp."""
    values = [m.get(field) for m in _members(xs, *filters) if m.get(field) is not None]
    return max(values) if values else None


def _weekday(iso: Any, absent: Any = None) -> Any:
    """`weekday(iso[, absent])`: 0 = Monday; `absent` when there is no date to read."""
    if iso is None:
        if absent is None:
            raise ValueError("weekday of nothing — pass an `absent` value")
        return absent
    from datetime import date
    return float(date.fromisoformat(str(iso)[:10]).weekday())


def _projection_env(res: Any) -> dict[str, Any]:
    return {**_ENV,
            "at": lambda path, default=None: _at(res, path, default),
            "exists": lambda: 1.0 if res not in (None, False, {}, [], "", 0) else 0.0,
            "count": _count,
            "latest": _latest,
            "weekday": _weekday}


class _Projection:
    def __init__(self, var: str, spec: dict[str, Any], domain: list[Any]):
        self.var = var
        self.doors = doors(spec.get("door"))
        self.src = str(spec.get("expr", ""))
        if not self.doors or not self.src:
            raise ValueError(f"state-var '{var}': a projection names a door and an expr")
        self.expr = _compile(self.src, f"projection of '{var}'")
        self.domain = domain

    def value(self, event: dict[str, Any]) -> Any:
        res = event.get("res")
        out = _normalize(self.expr({"res": res, **_LITERALS}, _projection_env(res)))
        if out not in self.domain:
            raise ValueError(f"the world shows '{self.var}' as {out!r}, outside its domain")
        return out


def _projections(model: Node) -> dict[str, _Projection]:
    out: dict[str, _Projection] = {}
    for c in model.children:
        if c.kind == "state-var" and c.payload.get("shown"):
            out[c.id] = _Projection(c.id, c.payload["shown"],
                                    _domain(c.payload, f"state-var '{c.id}'"))
    return out


# --- the model's declarations, compiled once --------------------------------------------


class _Effect:
    def __init__(self, action: str, node: Node):
        p = node.payload
        self.action = action
        self.id = node.id
        self.kind = node.kind
        self.entity = str(p.get("entity", ""))
        self.inputs = list(p.get("from") or [])
        self.via_spec = p.get("via")
        self.shown_spec = p.get("shown_by")
        self.via = doors(self.via_spec)
        self.shown_by = doors(self.shown_spec)


class _Action:
    def __init__(self, node: Node):
        self.id = node.id
        args = node.payload.get("args") or {}
        self.args = {n: _domain(args[n], f"action '{node.id}' arg '{n}'") for n in args}
        self.events = [o.payload.get("event") for o in node.children if o.kind == "observation"]
        self.effects = [_Effect(node.id, c) for c in node.children if c.kind in EFFECTS]
        touches = [c for c in node.children if c.kind == "touches"]
        self.touches: Node | None = touches[0] if touches else None
        self.touches_only = list(self.touches.payload.get("only") or []) if self.touches else []
        self.touches_via = doors(self.touches.payload.get("via")) if self.touches else []

    def binds(self, data: dict[str, Any]) -> bool:
        """The span's data instantiates this action's arguments, inside their domains."""
        for arg, dom in self.args.items():
            if arg not in data or _normalize(data[arg]) not in dom:
                return False
        return True


class _Model:
    def __init__(self, model: Node):
        self.state_vars = {c.id for c in model.children if c.kind == "state-var"}
        self.actions = [_Action(c) for c in model.children if c.kind == "action"]
        # Every door the model knows as a write: the frame's universe.
        self.known: list[Door] = []
        for a in self.actions:
            self.known.extend(a.touches_via)
            for e in a.effects:
                self.known.extend(e.via)

    def bound(self, span: Node) -> list[_Action]:
        data = span.payload.get("data") or {}
        return [a for a in self.actions if span.kind in a.events and a.binds(data)]


# --- the tape as one stream ---------------------------------------------------------------


class _Act:
    """One top-level span — or one whole call — placed in the session's stream."""

    def __init__(self, call: int, path: str, span: Node, is_call: bool = False):
        self.call = call
        self.path = path
        self.span = span
        self.is_call = is_call
        self.inner: list[_Act] = []   # a call's top-level span acts
        self.own: list[tuple[tuple[int, int], dict[str, Any]]] = []  # a call's unenclosed events
        self.at = (call, span.payload.get("at", -1))
        self.to = (call, span.payload.get("to") if span.payload.get("to") is not None
                   else float("inf"))
        self.events: list[tuple[tuple[int, int], dict[str, Any]]] = []
        self._collect(span)

    def _collect(self, node: Node) -> None:
        for pos, e in zip(node.payload.get("pos") or [], node.payload.get("events") or []):
            self.events.append(((self.call, pos), e))
        for c in node.children:
            self._collect(c)


def _acts_and_stream(node: Node, path: str, calls: bool = False
                     ) -> tuple[list[_Act], list[tuple[tuple[int, int], dict]]]:
    """The top-level acts in order, and every raw event in the slice with its place. With
    `calls`, each scenario is an act too — kind: the tool's name, data: its kwargs, window:
    the whole call, events: all of them — placed before the spans it encloses."""
    scenarios = ([(f"{path}/{c.id}", c) for c in node.children]
                 if node.kind == "session" else [(path, node)])
    acts: list[_Act] = []
    stream: list[tuple[tuple[int, int], dict[str, Any]]] = []
    for ci, (sp, s) in enumerate(scenarios):
        for pos, e in zip(s.payload.get("pos") or [], s.payload.get("events") or []):
            stream.append(((ci, pos), e))
        inner = []
        for c in s.children:
            act = _Act(ci, f"{sp}/{c.id}", c)
            inner.append(act)
            stream.extend(act.events)
        if calls and s.kind == "scenario":
            whole = Node(id=s.id, kind=s.name or "", payload={
                "data": s.payload.get("data") or {}, "outcome": s.payload.get("outcome"),
                "events": [], "pos": [], "at": -1, "to": s.payload.get("to")})
            call = _Act(ci, sp, whole, is_call=True)
            call.own = [((ci, pos), e) for pos, e in
                        zip(s.payload.get("pos") or [], s.payload.get("events") or [])]
            call.events = list(call.own)
            for a in inner:
                call.events.extend(a.events)
            call.events.sort(key=lambda t: t[0])
            call.inner = inner
            acts.append(call)
        acts.extend(inner)
    stream.sort(key=lambda t: t[0])
    return acts, stream


def _after(acts: list[_Act], i: int) -> list[_Act]:
    """The acts that begin after this one ENDS — a call's own spans are inside it, not after."""
    return [a for a in acts[i + 1:] if a.at > acts[i].to]


def _horizon(acts: list[_Act], model: _Model, i: int, entity: str) -> tuple[int, float]:
    """Where this act stops answering for `entity`: the start of the next act that declares
    an effect on it, or the end of the tape."""
    for later in _after(acts, i):
        if any(e.entity == entity for a in model.bound(later.span) for e in a.effects):
            return later.at
    return (len(acts) + 10 ** 9, float("inf"))


def _effects_of(model: _Model, act: _Act) -> list[_Effect]:
    """The effect declarations this act inherits, one per (kind, entity)."""
    seen: dict[tuple[str, str], _Effect] = {}
    for a in model.bound(act.span):
        for e in a.effects:
            seen.setdefault((e.kind, e.entity), e)
    return list(seen.values())


# --- conduct/effect: what an action declares it does, the world shows afterward -----------


def effect(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many declared effects under `path` the world failed to show.

    Per top-level act, per effect it inherits that names both doors: a `via` write must
    sit inside the act (else the effect is a verb with nothing under it); for creates and
    mutates, some `shown_by` read after the act and before the entity's next act returns
    what the write carried; for deletes, no such read still returns what an earlier effect
    on the entity carried, nor names what the removal named. A read that never comes is a
    note, not a violation.
    """
    node, model_node = _confront(tree, path, rel)
    model = _Model(model_node)
    acts, stream = _acts_and_stream(node, path, calls=True)
    diagnostics: list[str] = []
    notes: list[str] = []

    for i, act in enumerate(acts):
        if act.span.payload.get("outcome") == "error":
            continue  # a refused act promises nothing; conduct/refusal holds it instead
        for eff in _effects_of(model, act):
            if not eff.via or not eff.shown_by:
                continue  # conduct/checkable's finding, not a tape's
            writes = [e for _, e in act.events if _through(e, eff.via)]
            where = f"{act.path}: '{act.span.kind}' ({eff.action}) declares {eff.kind} '{eff.entity}'"
            if not writes:
                diagnostics.append(f"{where} via {eff.via_spec!r}, and no such write is "
                                   "inside the act — a verb with nothing under it")
                continue
            until = _horizon(acts, model, i, eff.entity)
            reads = [e for at, e in stream
                     if act.to < at < until and _through(e, eff.shown_by)]
            if eff.kind in ("creates", "mutates"):
                carried = [v for w in writes for v in _carried(w)]
                if not carried:
                    notes.append(f"{where}: the via write carries no container value to "
                                 "find again — unwitnessable as written")
                    continue
                if not reads:
                    notes.append(f"{where}: no {eff.shown_spec!r} read after the act — "
                                 "unwitnessed, not shown")
                    continue
                if not any(_within(r.get("res"), v) for r in reads for v in carried):
                    diagnostics.append(
                        f"{where}: {len(reads)} read(s) through {eff.shown_spec!r} after "
                        f"the act, none returns what the {len(writes)} write(s) carried")
            else:
                targets = [v for j in range(i) for e2 in _effects_of(model, acts[j])
                           if e2.entity == eff.entity and e2.kind != "deletes"
                           for _, w in acts[j].events if _through(w, e2.via)
                           for v in _carried(w)]
                idents = [x for w in writes for x in _identifiers(w)]
                if not reads:
                    notes.append(f"{where}: no {eff.shown_spec!r} read after the act — "
                                 "unwitnessed, not shown absent")
                    continue
                for r in reads:
                    res = r.get("res")
                    if (any(_within(res, v) for v in targets)
                            or any(_names(res, x) for x in idents)):
                        diagnostics.append(
                            f"{where}: a {eff.shown_spec!r} read after the act still shows "
                            "the entity — the removal did not remove")
                        break
    return Conformance(check="conduct/effect", violations=len(diagnostics),
                       diagnostics=diagnostics, notes=notes)


# --- conduct/faithful: what was made from the inputs agrees with the inputs ---------------


def faithful(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many effects under `path` wrote something that disagrees with the inputs their
    `from` names: each named argument's value, as the span testified it, must appear in
    what the `via` write carried. An effect with an empty `from`, or with no write inside
    the act, is not this check's to judge."""
    node, model_node = _confront(tree, path, rel)
    model = _Model(model_node)
    acts, _ = _acts_and_stream(node, path, calls=True)
    diagnostics: list[str] = []
    for act in acts:
        if act.span.payload.get("outcome") == "error":
            continue
        data = act.span.payload.get("data") or {}
        for eff in _effects_of(model, act):
            if eff.kind == "deletes" or not eff.inputs or not eff.via:
                continue
            carried = [v for _, e in act.events if _through(e, eff.via) for v in _carried(e)]
            if not carried:
                continue
            missing = [a for a in eff.inputs
                       if a in data and not any(_within(v, data[a]) for v in carried)]
            if missing:
                diagnostics.append(
                    f"{act.path}: '{act.span.kind}' ({eff.action}) declares {eff.kind} "
                    f"'{eff.entity}' from {eff.inputs}, and what it wrote does not carry "
                    f"{', '.join(f'{a}={data[a]!r}' for a in missing)} — made from one "
                    "value, written as another")
    return Conformance(check="conduct/faithful", violations=len(diagnostics),
                       diagnostics=diagnostics)


# --- conduct/frame: a value is the same if it wasn't changed ------------------------------


def frame(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many writes under `path` pass through a door the model knows that the act's own
    boundary does not admit. The universe is every `via` any effect or `touches` in the
    model declares; an act's boundary is its `touches.via` plus its effects' `via`. An act
    whose actions declare no `touches` is outside the law — the trigger is the declaration."""
    node, model_node = _confront(tree, path, rel)
    model = _Model(model_node)
    acts, _ = _acts_and_stream(node, path, calls=True)
    diagnostics: list[str] = []

    def admitted(bound: list[_Action]) -> list[Door]:
        return [d for a in bound for d in a.touches_via] + \
               [d for a in bound for e in a.effects for d in e.via]

    for act in acts:
        bound = model.bound(act.span)
        if not any(a.touches is not None for a in bound):
            continue
        allowed = admitted(bound)
        # a call answers for the writes no span encloses; a write inside a domain span
        # answers to that span's own declaration
        for _, e in (act.own if act.is_call else act.events):
            if _through(e, model.known) and not _through(e, allowed):
                diagnostics.append(
                    f"{act.path}: '{act.span.kind}' ({', '.join(a.id for a in bound)}) "
                    f"writes through '{_named(e)}' "
                    f"{_render(e.get('kwargs') or e.get('args') or '')[:80]}, a door "
                    "outside its declared boundary — something moved that the act never "
                    "claimed to touch")
    return Conformance(check="conduct/frame", violations=len(diagnostics),
                       diagnostics=diagnostics)


# --- conduct/refusal: an action the guard refuses leaves every value untouched ------------


def refusal(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many spans under `path` ended in error having written through a door the model
    knows. Outermost errored span only: its whole subtree is the half-done act."""
    node, model_node = _confront(tree, path, rel)
    model = _Model(model_node)
    diagnostics: list[str] = []

    def writes_under(n: Node) -> list[str]:
        out = [_named(e) for e in n.payload.get("events") or [] if _through(e, model.known)]
        for c in n.children:
            out.extend(writes_under(c))
        return out

    def walk(p: str, n: Node) -> None:
        if n.payload.get("outcome") == "error":
            wrote = writes_under(n)
            what = f"the call '{n.name}'" if n.kind in _STRUCTURE else f"'{n.kind}'"
            if wrote:
                diagnostics.append(
                    f"{p}: {what} failed and still wrote through {sorted(set(wrote))} "
                    "— a refusal that half-did the thing")
            return
        for c in n.children:
            walk(f"{p}/{c.id}", c)

    walk(path, node)
    return Conformance(check="conduct/refusal", violations=len(diagnostics),
                       diagnostics=diagnostics)


# --- conduct/checkable: every declared effect names something the tape can show ------------


def checkable(tree: Quern | TreeStore, path: str) -> Conformance:
    """How many declarations of the model at `path` no tape could ever witness: an effect
    whose entity is no state-var, or that names no `via`, or no `shown_by`; a `touches`
    naming a state-var the model lacks. This is the gate the other checks assume — an
    effect they silently skip is one this one counts."""
    from quern import get_node
    node = get_node(tree, path)
    if node is None:
        raise ValueError(f"no node at '{path}'")
    if node.kind != "model":
        raise ValueError(f"'{path}' is a '{node.kind}', not a model — conduct/checkable "
                         "reads declarations, and a tape declares nothing")
    model = _Model(node)
    diagnostics: list[str] = []
    for a in model.actions:
        for e in a.effects:
            why = []
            if e.entity not in model.state_vars:
                why.append(f"entity '{e.entity}' is no state-var of the model")
            if not e.via:
                why.append("no `via` door — nothing on a tape materializes it")
            if not e.shown_by:
                why.append("no `shown_by` door — nothing on a tape shows it back")
            if why:
                diagnostics.append(f"{path}/{a.id}/{e.id}: {e.kind} — {'; '.join(why)}")
        unknown = [v for v in a.touches_only if v not in model.state_vars]
        if unknown:
            diagnostics.append(f"{path}/{a.id}/{a.touches.id}: touches.only names "
                               f"{unknown}, which no state-var declares")
    return Conformance(check="conduct/checkable", violations=len(diagnostics),
                       diagnostics=diagnostics)


# --- conduct/agrees: the world, projected, agrees with the model's own updates -------------


def agrees(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many (act, projected state-var) pairs under `path` disagree with the model.

    For each top-level act bound to exactly one enabled-by-arguments action, and each
    state-var with a projection: the pre-value is the latest read through its door BEFORE
    the act; the post-value is the first read through its door AFTER the act and before the
    next act writes anything through a door the model knows. With every pre-value the
    action's updates read, the expected post-value is the update applied to the pre-values
    (the model's own semantics, the prover's) — or the pre-value itself for a variable the
    action does not update, which is the frame. A missing read is a note, never a count;
    an act that binds no action, or two, is skipped and noted.
    """
    node, model_node = _confront(tree, path, rel)
    model = _Model(model_node)
    projections = _projections(model_node)
    variables, actions, _ = _automaton(model_node)
    by_id = {a["id"]: a for a in actions}
    acts, stream = _acts_and_stream(node, path, calls=True)
    diagnostics: list[str] = []
    notes: list[str] = []
    if not projections:
        notes.append(f"{path}: the model projects no state-var — nothing to agree on")
        return Conformance(check="conduct/agrees", violations=0, notes=notes)

    def read_before(proj: _Projection, at: tuple) -> tuple[Any, Any] | None:
        for pos, e in reversed(stream):
            if pos < at and _through(e, proj.doors):
                return pos, e
        return None

    def read_after(proj: _Projection, to: tuple, limit: tuple) -> dict | None:
        for pos, e in stream:
            if to < pos < limit and _through(e, proj.doors):
                return e
        return None

    for i, act in enumerate(acts):
        if act.span.payload.get("outcome") == "error":
            continue
        bound = model.bound(act.span)
        where = f"{act.path}: '{act.span.kind}'"
        if len(bound) != 1:
            notes.append(f"{where} binds {len(bound)} action(s) — not judged")
            continue
        action = by_id[bound[0].id]
        # the world after this act ends where the next act (after it ENDS) first writes
        limit = (len(acts) + 10 ** 9, float("inf"))
        following = _after(acts, i)
        if following:
            nxt = following[0]
            limit = nxt.at
            for pos, e in nxt.events:
                if _through(e, model.known):
                    limit = pos
                    break
        pre: dict[str, Any] = {}
        post: dict[str, Any] = {}
        for var, proj in projections.items():
            try:
                before = read_before(proj, act.at)
                if before is not None:
                    pre[var] = proj.value(before[1])
                after = read_after(proj, act.to, limit)
                if after is not None:
                    post[var] = proj.value(after)
            except ValueError as e:
                diagnostics.append(f"{where} ({action['id']}): {e}")
        data = act.span.payload.get("data") or {}
        binding = {a: _normalize(data[a]) for a in action["args"] if a in data}
        updated = {var: expr for var, expr in action["updates"]}
        for var, proj in projections.items():
            if var not in post:
                notes.append(f"{where} ({action['id']}): no {proj.src!r} read of '{var}' "
                             "after the act — unwitnessed")
                continue
            if var in updated:
                env = {**pre, **binding, **_LITERALS}
                try:
                    expected = _normalize(updated[var](env))
                except ValueError as e:
                    notes.append(f"{where} ({action['id']}): '{var}' cannot be computed from "
                                 f"the projected world — {e}")
                    continue
                if post[var] != expected:
                    diagnostics.append(
                        f"{where} ({action['id']}) updates '{var}' to {expected!r} from the "
                        f"projected world {pre}; the world shows {post[var]!r} after")
            elif var in pre:
                if post[var] != pre[var]:
                    diagnostics.append(
                        f"{where} ({action['id']}) does not update '{var}', and the world "
                        f"shows it moved from {pre[var]!r} to {post[var]!r} — the frame, by "
                        "value")
            else:
                notes.append(f"{where} ({action['id']}): '{var}' has no read before the act "
                             "— its frame cannot be judged")
    return Conformance(check="conduct/agrees", violations=len(diagnostics),
                       diagnostics=diagnostics, notes=notes)


# --- the natives: counts behind solve() ---------------------------------------------------


def effect_count(tree, path, rel) -> float:
    return float(effect(tree, path, rel).violations)


def faithful_count(tree, path, rel) -> float:
    return float(faithful(tree, path, rel).violations)


def frame_count(tree, path, rel) -> float:
    return float(frame(tree, path, rel).violations)


def refusal_count(tree, path, rel) -> float:
    return float(refusal(tree, path, rel).violations)


def checkable_count(tree, path) -> float:
    return float(checkable(tree, path).violations)


def agrees_count(tree, path, rel) -> float:
    return float(agrees(tree, path, rel).violations)


from .spec import CONDUCT_SPEC  # noqa: E402

register_native("conduct/effect", effect_count, CONDUCT_SPEC["conduct/effect"])
register_native("conduct/faithful", faithful_count, CONDUCT_SPEC["conduct/faithful"])
register_native("conduct/frame", frame_count, CONDUCT_SPEC["conduct/frame"])
register_native("conduct/refusal", refusal_count, CONDUCT_SPEC["conduct/refusal"])
register_native("conduct/checkable", checkable_count, CONDUCT_SPEC["conduct/checkable"])
register_native("conduct/agrees", agrees_count, CONDUCT_SPEC["conduct/agrees"])
