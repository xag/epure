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

THE TWO-STRETCH LAWS compare worlds around two acts rather than one, all over the same
projections (`_worlds` computes, once per tape, the projected world before and after every
act):

- **conduct/twice** — *twice-is-once*. Two adjacent acts of the same kind and data, bound to
  one action whose guard still admits it in the world after the first: the world after the
  second equals the world after the first. A guard that refuses the repeat exits the family
  (that is refusal's law).
- **conduct/last-write** — *last-write-wins*. Two adjacent acts on one entity whose update
  reads the argument and not the entity (an overwrite): the value after the second is the
  second's update applied to the world BEFORE THE FIRST.
- **conduct/commute** — *independent-writes-commute*. A stretch A;B on disjoint entities, and
  elsewhere on the tape the stretch B;A from an equal projected world: equal worlds after.
- **conduct/undo** — *undo-restores*. A `creates` of E followed by a `deletes` of E: the world
  after the delete equals the world before the create, on every projected variable.
- **conduct/durable** — *shown-once-shown-until-touched*. Once a read after an act shows a
  variable at v, every later read of it projects v until an act that updates it.
- **conduct/same-story** — *same-state-same-story* and *equivalent-worlds-stay-equivalent*.
  Two acts of the same kind and data from equal projected worlds leave equal projected worlds.
- **conduct/constructible** — *every-world-is-constructible*. Every projected world read off
  the tape agrees with some state the model can reach from init (the prover's own walk).

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
from typing import Any, Callable, Iterable

from quern import Node, Quern, TreeStore, register_native

from epure.conformance import _STRUCTURE, Conformance, _automaton, _confront, _named, _normalize
from epure.prove import _ENV, _LITERALS, _compile, _domain, reachable

EFFECTS = ("creates", "mutates", "deletes", "merges")

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
    # the event's own fields last: `name` of a semantic point, `op` of a store exchange -
    # what lets a door admit the app's stated decision (`{"event": "sem", "where":
    # {"name": "board-shown"}}`) and not only its stored reads
    return event.get(key)


def _render(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, ensure_ascii=False)
    return str(value)


def door(spec: Any) -> Door:
    """One door as a predicate over raw events: a name pattern, optionally narrowed by
    argument patterns. `{"event": "app.storage.put_field", "where": {"field": "done.*"}}`
    admits a field write to the completions map and nothing else; `{"event": "sem",
    "where": {"name": "board-shown"}}` admits the app's own statement at a point."""
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
        # a DERIVED view (0.11.0): the stored variables this one is a function of. Its
        # writers are theirs - a read of it is stale once any of them was written - and its
        # door is typically the point where the app states the value it computed, read as
        # `res` from the point's data. Hughes' warning is why the shape is this and not an
        # expr over several reads: a projection that reimplements the operation tests
        # nothing; one that reads the app's decision holds the model to the app.
        self.derived_from: list[str] = [str(v) for v in (spec.get("derived_from") or [])]

    def value(self, event: dict[str, Any]) -> Any:
        """The variable's value as this read shows it — or None when the read shows nothing
        for it (the path is absent, the date is missing): not a disagreement, an unwitnessed
        act, and the caller treats it as no read. A validator has no domain: its value is
        opaque."""
        res = event["res"] if "res" in event else event.get("data")
        out = _normalize(self.expr({"res": res, **_LITERALS}, _projection_env(res)))
        if out is None or self.domain is None:
            return out
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
        self.other: dict[str, str] = dict(p.get("other") or {})      # merges: var -> arg
        self.absent: dict[str, Any] = dict(p.get("absent") or {})    # merges: var -> empty
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
            # the testimony itself re-enters the stream as one `sem` entry at its own mark:
            # the importer lifted it out of the raw window into a node, and a projection
            # reading the app's STATEMENT at a point (0.11.0, the derived view) must find it
            # where it was said - name and data, nothing the raw event did not carry
            def said(n: Node) -> None:
                at = (ci, n.payload.get("at", -1))
                to = n.payload.get("to")
                stream.append((at, {
                    "k": "sem", "name": n.kind, "data": n.payload.get("data") or {},
                    "phase": "point" if to is None or to == at[1] else "begin"}))
                for d in n.children:
                    said(d)
            said(c)
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
    judged = 0

    for i, act in enumerate(acts):
        if act.span.payload.get("outcome") == "error":
            continue  # a refused act promises nothing; conduct/refusal holds it instead
        for eff in _effects_of(model, act):
            if eff.kind == "merges":
                continue  # held by value, by conduct/merge
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
                judged += 1
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
                judged += 1
                for r in reads:
                    res = r.get("res")
                    if (any(_within(res, v) for v in targets)
                            or any(_names(res, x) for x in idents)):
                        diagnostics.append(
                            f"{where}: a {eff.shown_spec!r} read after the act still shows "
                            "the entity — the removal did not remove")
                        break
    return Conformance(check="conduct/effect", violations=len(diagnostics),
                       diagnostics=diagnostics, notes=notes, judged=judged)


# --- conduct/faithful: what was made from the inputs agrees with the inputs ---------------


def faithful(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many effects under `path` wrote something that disagrees with the inputs their
    `from` names: each named argument's value, as the span testified it, must appear in
    what the `via` write carried. An effect with an empty `from`, or with no write inside
    the act, is not this check's to judge. An input the entity's update READS into a
    projected entity (assignee := member) is held by value by conduct/agrees, which knows
    that the model's `none` is the store's null where containment cannot; the inputs it
    does not read (the chore that selects the act, a coat that `held := 1` ignores) are
    held here, by containment."""
    node, model_node = _confront(tree, path, rel)
    model = _Model(model_node)
    projected = set(_projections(model_node))
    update_src = {c.id: {u["var"]: str(u["expr"]) for u in c.payload.get("updates") or []}
                  for c in model_node.children if c.kind == "action"}
    acts, _ = _acts_and_stream(node, path, calls=True)
    diagnostics: list[str] = []
    for act in acts:
        if act.span.payload.get("outcome") == "error":
            continue
        data = act.span.payload.get("data") or {}
        for eff in _effects_of(model, act):
            if eff.kind in ("deletes", "merges") or not eff.inputs or not eff.via:
                continue
            src = update_src.get(eff.action, {}).get(eff.entity, "")
            words = set(src.replace("'", " ").replace("(", " ").replace(")", " ").split())
            # an input the update reads into a projected entity is held by value by agrees;
            # the others (an input that selects the act, a coat the update ignores) by
            # containment here
            by_value = words if eff.entity in projected else set()
            carried = [v for _, e in act.events if _through(e, eff.via) for v in _carried(e)]
            if not carried:
                continue
            missing = [a for a in eff.inputs if a not in by_value
                       and a in data and not any(_within(v, data[a]) for v in carried)]
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
            if e.kind == "merges":
                unknown = [v for v in e.other if v not in model.state_vars]
                if not e.other:
                    why.append("a merge names no variable it absorbs (`other`)")
                if unknown:
                    why.append(f"`other` names {unknown}, which no state-var declares")
            elif e.entity not in model.state_vars:
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


# --- the projected world around every act, computed once per tape -------------------------


class _World:
    """One act with the projected world before it and after it, and the single action it
    binds (None when it binds none or several). `pre[var]`/`post[var]` are present only
    where a read through the variable's door exists on that side and shows a value."""

    def __init__(self, index: int, act: _Act, action: dict | None,
                 pre: dict[str, Any], post: dict[str, Any], binding: dict[str, Any]):
        self.index = index
        self.act = act
        self.action = action
        self.pre = pre
        self.post = post
        self.binding = binding

    @property
    def kind(self) -> str:
        return self.act.span.kind

    @property
    def data(self) -> dict[str, Any]:
        return self.act.span.payload.get("data") or {}

    def updates(self) -> set[str]:
        """The variables this act moves: its own action's updates and, for a call, those
        of every span it encloses — a call answers for its spans' writes as its own."""
        out = {var for var, _ in self.action["updates"]} if self.action else set()
        return out | self.inner_updates

    inner_updates: set[str] = set()
    stamp_before: Any = None
    stamp_after: Any = None


class _Worlds:
    def __init__(self, tree, path: str, rel: str):
        self.node, self.model_node = _confront(tree, path, rel)
        self.model = _Model(self.model_node)
        self.projections = _projections(self.model_node)
        variables, actions, _ = _automaton(self.model_node)
        self.variables = variables
        self.by_id = {a["id"]: a for a in actions}
        # the update exprs' SOURCE, for the overwrite test last-write needs
        self.update_src: dict[str, dict[str, str]] = {}
        self.guard_src: dict[str, str] = {}
        for c in self.model_node.children:
            if c.kind == "action":
                self.update_src[c.id] = {u["var"]: u["expr"]
                                         for u in c.payload.get("updates") or []}
                self.guard_src[c.id] = str(c.payload.get("guard", ""))
        self.acts, self.stream = _acts_and_stream(self.node, path, calls=True)
        # the stamp: a validator is read like a projection whose writers are every door the
        # model knows - any write may bump it, so a read is a world-before only if nothing
        # was written since, and a world-after only if nothing is written before it
        self.validators: list[_Projection] = []
        for c in self.model_node.children:
            if c.kind == "validator":
                v = _Projection.__new__(_Projection)
                v.var = c.id
                v.doors = doors(c.payload.get("door"))
                v.src = str(c.payload.get("expr", ""))
                v.expr = _compile(v.src, f"validator '{c.id}'")
                v.domain = None
                self.validators.append(v)
        # the doors that write each projected variable: the EFFECT doors (`via`) of every
        # action that updates it - the writes that carry its value, not the stamps and rows
        # the action's boundary also admits. A read is a valid world before an act only if
        # nothing passed through them between the read and the act, and a valid world after
        # only if nothing passed through them between the act and the read.
        writes_all: dict[str, list[Door]] = {}
        for a in self.model.actions:
            moved = {var for var, _ in self.by_id[a.id]["updates"]} if a.id in self.by_id else set()
            for e in a.effects:
                moved.add(e.entity)
            ds = [d for e in a.effects for d in e.via] or list(a.touches_via)
            for var in moved:
                writes_all.setdefault(var, []).extend(ds)
        # ...and a derived view is written whenever anything it derives from is: the
        # closure over `derived_from`, so a view of a view inherits the whole chain
        derived = {v: p.derived_from for v, p in self.projections.items()}

        def writers(var: str, seen: frozenset = frozenset()) -> list[Door]:
            out = list(writes_all.get(var, []))
            for d in derived.get(var, []):
                if d not in seen:
                    out.extend(writers(d, seen | {var}))
            return out
        self.writes_of: dict[str, list[Door]] = {v: writers(v) for v in self.projections}
        self.notes: list[str] = []
        self.errors: list[str] = []
        self.worlds: list[_World] = []
        self._compute()
        # the variables this tape can show at all: "the same world" means equal on these
        self.shown: set[str] = {v for v, proj in self.projections.items()
                                if any(_through(e, proj.doors) for _, e in self.stream)}

    def _read_before(self, proj: _Projection, at: tuple):
        """The latest read of the variable before `at` — unless a write through one of the
        variable's own doors came after it, in which case the read is stale and there is
        no pre-world for this variable."""
        for pos, e in reversed(self.stream):
            if pos >= at:
                continue
            if _through(e, self.writes_of.get(proj.var, [])):
                return None
            if _through(e, proj.doors):
                return e
        return None

    def _stamps(self, act: _Act) -> tuple[Any, Any]:
        """The validator's value read before the act with no write since, and after it
        with no write before; None where unread. One validator per model is the case
        served; several are read in declaration order and the first that shows decides."""
        before = after = None
        for v in self.validators:
            for pos, e in reversed(self.stream):
                if pos >= act.at:
                    continue
                if _through(e, v.doors):
                    if (val := v.value(e)) is not None:   # a read that shows no stamp is no read
                        before = val
                        break
                    continue
                if _through(e, self.model.known):
                    break
            for pos, e in self.stream:
                if pos <= act.to:
                    continue
                if _through(e, v.doors):
                    if (val := v.value(e)) is not None:
                        after = val
                        break
                    continue
                if _through(e, self.model.known):
                    break
            if before is not None or after is not None:
                break
        return before, after

    def _read_after(self, proj: _Projection, to: tuple):
        """The first read of the variable after `to` — unless a write through one of the
        variable's own doors comes first, in which case the world after this act was never
        read for this variable."""
        for pos, e in self.stream:
            if pos <= to:
                continue
            if _through(e, self.writes_of.get(proj.var, [])):
                return None
            if _through(e, proj.doors):
                return e
        return None

    def reads_between(self, proj: _Projection, lo: tuple, hi: tuple) -> list[dict]:
        return [e for pos, e in self.stream if lo < pos < hi and _through(e, proj.doors)]

    def _compute(self) -> None:
        for i, act in enumerate(self.acts):
            if act.span.payload.get("outcome") == "error":
                continue
            bound = self.model.bound(act.span)
            where = f"{act.path}: '{act.span.kind}'"
            action = self.by_id[bound[0].id] if len(bound) == 1 else None
            if action is None:
                self.notes.append(f"{where} binds {len(bound)} action(s) — not judged")
            pre: dict[str, Any] = {}
            post: dict[str, Any] = {}
            for var, proj in self.projections.items():
                try:
                    before = self._read_before(proj, act.at)
                    if before is not None and (v := proj.value(before)) is not None:
                        pre[var] = v
                    after = self._read_after(proj, act.to)
                    if after is not None and (v := proj.value(after)) is not None:
                        post[var] = v
                except ValueError as e:
                    self.errors.append(f"{where}: {e}")
            data = act.span.payload.get("data") or {}
            binding = ({a: _normalize(data[a]) for a in action["args"] if a in data}
                       if action else {})
            w = _World(i, act, action, pre, post, binding)
            w.inner_updates = {var for inner in act.inner for a in self.model.bound(inner.span)
                               for var, _ in self.by_id[a.id]["updates"]}
            w.stamp_before, w.stamp_after = self._stamps(act)
            self.worlds.append(w)

    def adjacent(self) -> list[tuple[_World, _World]]:
        """Pairs (w1, w2) where w2 is the first bound act that begins after w1 ends — no
        other bound act between them. Calls are skipped as stretch members: a call encloses
        its spans, and a stretch is made of the acts that move the world."""
        spans = [w for w in self.worlds if w.action is not None and not w.act.is_call]
        out = []
        for a, b in zip(spans, spans[1:]):
            if b.act.at > a.act.to:
                out.append((a, b))
        return out

    def apply(self, action: dict, world: dict[str, Any], binding: dict[str, Any]
              ) -> dict[str, Any] | None:
        """The action's own updates on a projected world — None if a variable it reads
        is not projected there."""
        env = {**world, **binding, **_LITERALS}
        out = dict(world)
        try:
            for var, expr in action["updates"]:
                out[var] = _normalize(expr(env))
        except ValueError:
            return None
        return out


def _same(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """The projected variables present in both worlds that disagree."""
    return [v for v in a if v in b and a[v] != b[v]]


def _equal_on(a: dict[str, Any], b: dict[str, Any], vars: Iterable[str]) -> bool:
    vars = list(vars)
    return all(v in a and v in b and a[v] == b[v] for v in vars)


# --- conduct/agrees: the world, projected, agrees with the model's own updates -------------


def agrees(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """How many (act, projected state-var) pairs under `path` disagree with the model.

    For each act bound to exactly one action, and each state-var with a projection: the
    pre-value is the latest read through its door BEFORE the act with no write through the
    variable's own doors after it; the post-value is the first read through its door AFTER
    the act and before the next act writes anything through a door the model knows. With
    every pre-value the action's updates read, the expected post-value is the update applied
    to the pre-values (the model's own semantics, the prover's) — or the pre-value itself for
    a variable the action does not update, which is the frame. A call answers for its spans'
    updates as its own. A missing read is a note, never a count; an act that binds no action,
    or two, is skipped and noted.
    """
    W = _Worlds(tree, path, rel)
    diagnostics: list[str] = list(W.errors)
    notes: list[str] = list(W.notes)
    judged = 0
    if not W.projections:
        notes.append(f"{path}: the model projects no state-var — nothing to agree on")
        return Conformance(check="conduct/agrees", violations=0, notes=notes)
    for w in W.worlds:
        if w.action is None:
            continue
        where = f"{w.act.path}: '{w.kind}'"
        updated = {var: expr for var, expr in w.action["updates"]}
        for var, proj in W.projections.items():
            if var in w.inner_updates and var not in updated:
                continue  # a span inside this call moved it, and answers for it
            if var not in w.post:
                notes.append(f"{where} ({w.action['id']}): no {proj.src!r} read of '{var}' "
                             "after the act — unwitnessed")
                continue
            if var in updated:
                env = {**w.pre, **w.binding, **_LITERALS}
                try:
                    expected = _normalize(updated[var](env))
                except ValueError as e:
                    notes.append(f"{where} ({w.action['id']}): '{var}' cannot be computed "
                                 f"from the projected world — {e}")
                    continue
                judged += 1
                if w.post[var] != expected:
                    diagnostics.append(
                        f"{where} ({w.action['id']}) updates '{var}' to {expected!r} from the "
                        f"projected world {w.pre}; the world shows {w.post[var]!r} after")
            elif var in w.pre:
                judged += 1
                if w.post[var] != w.pre[var]:
                    diagnostics.append(
                        f"{where} ({w.action['id']}) does not update '{var}', and the world "
                        f"shows it moved from {w.pre[var]!r} to {w.post[var]!r} — the frame, "
                        "by value")
            else:
                notes.append(f"{where} ({w.action['id']}): '{var}' has no read before the act "
                             "— its frame cannot be judged")
    return Conformance(check="conduct/agrees", violations=len(diagnostics),
                       diagnostics=diagnostics, notes=notes, judged=judged)


# --- the two-stretch natives ----------------------------------------------------------------


def _stretch_check(check: str, tree, path, rel, judge) -> Conformance:
    """The common frame: compute the worlds, let `judge` fill diagnostics/notes, count."""
    try:
        W = _Worlds(tree, path, rel)
    except ValueError:
        raise
    diagnostics: list[str] = list(W.errors)
    notes: list[str] = list(W.notes)
    if not W.projections:
        notes.append(f"{path}: the model projects no state-var — nothing to compare")
        return Conformance(check=check, violations=0, notes=notes)
    judged = judge(W, diagnostics, notes)
    return Conformance(check=check, violations=len(diagnostics), diagnostics=diagnostics,
                       notes=notes, judged=judged)


def twice(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """twice-is-once: two adjacent acts, same kind and data, one action, whose guard still
    admits the repeat in the world after the first — the world after the second equals the
    world after the first. A guard that refuses the repeat is refusal's law, not this one."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        for a, b in W.adjacent():
            if a.kind != b.kind or a.data != b.data or a.action is not b.action:
                continue
            env = {**a.post, **a.binding, **_LITERALS}
            try:
                readmits = a.action["guard"](env)
            except ValueError:
                notes.append(f"{b.act.path}: the guard of '{a.action['id']}' cannot be "
                             "read off the projected world — not judged")
                continue
            if not readmits:
                continue
            if not set(a.post) & set(b.post):
                notes.append(f"{b.act.path}: a repeat of '{a.kind}' with no read after both "
                             "— unwitnessed")
                continue
            judged += 1
            moved = _same(a.post, b.post)
            if moved:
                diagnostics.append(
                    f"{b.act.path}: '{b.kind}' repeated with the same inputs and the world "
                    f"moved on {moved}: after once {a.post}, after twice {b.post}")
        return judged
    return _stretch_check("conduct/twice", tree, path, rel, judge)


def last_write(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """last-write-wins: two adjacent acts whose actions update the same entity by an
    OVERWRITE (the update reads arguments, not the entity): the entity after the second is
    the second's update applied to the world before the first."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        for a, b in W.adjacent():
            shared = a.updates() & b.updates() & set(W.projections)
            for var in sorted(shared):
                src = W.update_src.get(b.action["id"], {}).get(var, "")
                if var in src.replace("'", " ").split() or f" {var} " in f" {src} ":
                    continue  # reads itself: a counter, not an overwrite
                if var not in b.post or not a.pre:
                    notes.append(f"{b.act.path}: '{var}' written twice, the world before the "
                                 "first or after the second unread — unwitnessed")
                    continue
                expected = W.apply(b.action, a.pre, b.binding)
                if expected is None or var not in expected:
                    notes.append(f"{b.act.path}: '{var}' after the second write cannot be "
                                 "computed from the world before the first — not judged")
                    continue
                judged += 1
                if b.post[var] != expected[var]:
                    diagnostics.append(
                        f"{b.act.path}: '{var}' written by '{a.kind}' then '{b.kind}'; the "
                        f"last write says {expected[var]!r}, the world shows {b.post[var]!r}")
        return judged
    return _stretch_check("conduct/last-write", tree, path, rel, judge)


def commute(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """independent-writes-commute: a stretch A;B whose actions update disjoint variables,
    and elsewhere on the tape B;A from an equal projected world — equal worlds after. A
    stretch with no reverse on the tape is noted, never counted."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        pairs = [(a, b) for a, b in W.adjacent()
                 if a.updates() and b.updates() and not (a.updates() & b.updates())]
        seen: set[tuple[int, int]] = set()
        for a, b in pairs:
            for c, d in pairs:
                if (c.index, d.index) <= (a.index, b.index) or (c.index, d.index) in seen:
                    continue
                if not (c.kind == b.kind and c.data == b.data
                        and d.kind == a.kind and d.data == a.data):
                    continue
                shared_pre = set(a.pre) & set(c.pre) & set(W.projections)
                if not shared_pre or not _equal_on(a.pre, c.pre, shared_pre):
                    continue
                shared_post = set(b.post) & set(d.post)
                if not shared_post:
                    notes.append(f"{d.act.path}: the reverse of '{a.kind}';'{b.kind}' found, "
                                 "but no read after both stretches — unwitnessed")
                    continue
                seen.add((c.index, d.index))
                judged += 1
                moved = _same(b.post, d.post)
                if moved:
                    diagnostics.append(
                        f"{d.act.path}: '{a.kind}' then '{b.kind}' leaves {b.post}; the same "
                        f"two from the same world in the other order leave {d.post} — they "
                        f"disagree on {moved}")
        if pairs and not judged and not any("reverse" in n for n in notes):
            notes.append(f"{path}: {len(pairs)} independent stretch(es) and no reverse of any "
                         "on the tape — unwitnessed")
        return judged
    return _stretch_check("conduct/commute", tree, path, rel, judge)


def undo(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """undo-restores: a `creates` of E followed by a `deletes` of E — the world after the
    delete equals the world before the create, on every projected variable read on both
    sides."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        bound = {w.act.span.id: w for w in W.worlds}
        for a, b in W.adjacent():
            made = {e.entity for x in W.model.bound(a.act.span) for e in x.effects
                    if e.kind == "creates"}
            gone = {e.entity for x in W.model.bound(b.act.span) for e in x.effects
                    if e.kind == "deletes"}
            if not (made & gone):
                continue
            both = set(a.pre) & set(b.post)
            if not both:
                notes.append(f"{b.act.path}: '{a.kind}' then '{b.kind}' on "
                             f"{sorted(made & gone)}, the world unread before or after — "
                             "unwitnessed")
                continue
            judged += 1
            residue = _same(a.pre, b.post)
            if residue:
                diagnostics.append(
                    f"{b.act.path}: '{b.kind}' unmade '{a.kind}' and the world differs from "
                    f"before it on {residue}: before {a.pre}, after {b.post} — residue")
        return judged
    return _stretch_check("conduct/undo", tree, path, rel, judge)


def durable(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """shown-once-shown-until-touched: once the first read after an act shows a variable it
    updated at v, every later read of it projects v until the next act that updates it."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        for w in W.worlds:
            if w.action is None:
                continue
            for var in sorted(w.updates() & set(W.projections) & set(w.post)):
                proj = W.projections[var]
                # the horizon: the next act (after this one ends) whose action updates var
                horizon = (len(W.acts) + 10 ** 9, float("inf"))
                for later in W.worlds:
                    if later.act.at > w.act.to and later.action and var in later.updates():
                        horizon = later.act.at
                        break
                later_reads = W.reads_between(proj, w.act.to, horizon)[1:]
                # ...and stop at the first write through the variable's own doors as well
                cut = next((pos for pos, e in W.stream
                            if pos > w.act.to and _through(e, W.writes_of.get(var, []))), None)
                if cut is not None:
                    later_reads = [r for r in later_reads
                                   if next(p for p, e in W.stream if e is r) < cut]
                if not later_reads:
                    continue
                judged += 1
                for r in later_reads:
                    try:
                        got = proj.value(r)
                    except ValueError as e:
                        diagnostics.append(f"{w.act.path}: {e}")
                        break
                    if got is not None and got != w.post[var]:
                        diagnostics.append(
                            f"{w.act.path}: '{w.kind}' left '{var}' at {w.post[var]!r}; a "
                            f"later read shows {got!r} with no act declaring it changed")
                        break
        return judged
    return _stretch_check("conduct/durable", tree, path, rel, judge)


def same_story(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """same-state-same-story: two acts of the same kind and data, from projected worlds
    equal on every projected variable, leave worlds equal on every variable read after
    both. Equivalent worlds stay equivalent: the same comparison, since equivalence IS
    projected equality."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        spans = [w for w in W.worlds if w.action is not None]
        for i, a in enumerate(spans):
            for b in spans[i + 1:]:
                if a.kind != b.kind or a.data != b.data:
                    continue
                # "the same state": known and equal on every variable this tape can show
                if not W.shown or not (W.shown <= set(a.pre) and W.shown <= set(b.pre)):
                    continue
                if not _equal_on(a.pre, b.pre, W.shown):
                    continue
                both = set(a.post) & set(b.post)
                if not both:
                    notes.append(f"{b.act.path}: '{b.kind}' twice from one world, no read "
                                 "after both — unwitnessed")
                    continue
                judged += 1
                moved = _same(a.post, b.post)
                if moved:
                    diagnostics.append(
                        f"{b.act.path}: '{b.kind}' with {b.data} from the world {b.pre} "
                        f"left {b.post}; the same act from the same world at "
                        f"{a.act.path} left {a.post} — an undeclared input on {moved}")
        return judged
    return _stretch_check("conduct/same-story", tree, path, rel, judge)


def constructible(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """every-world-is-constructible: every projected world read off the tape — each act's
    world before and after, on the variables read — agrees with some state the model
    reaches from init. The prover's own walk, pointed at the tape's worlds."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        node_path = None
        # the model's path in the tree: the link target of the slice
        targets = W.node.links.get(rel, [])
        node_path = targets[0]
        order, states = reachable(tree, node_path)
        idx = {v: order.index(v) for v in W.projections if v in order}
        seen: set[tuple] = set()
        judged = 0
        for w in W.worlds:
            for side, world in (("before", w.pre), ("after", w.post)):
                vars_ = sorted(v for v in world if v in idx)
                if not vars_:
                    continue
                key = tuple((v, world[v]) for v in vars_)
                if key in seen:
                    continue
                seen.add(key)
                judged += 1
                if not any(all(st[idx[v]] == world[v] for v in vars_) for st in states):
                    diagnostics.append(
                        f"{w.act.path}: the world {side} '{w.kind}' reads {dict(key)}, "
                        "which no sequence of the model's actions reaches from init")
        return judged
    return _stretch_check("conduct/constructible", tree, path, rel, judge)


def merge(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """a-merge-keeps-both-and-prefers-the-left: after an act declaring `merges`, each merged
    variable projects to its own value before if that was not the absent value, else to the
    other world's (the argument) — which makes a self-merge a no-op; and where two merges b
    then c from a world a, and elsewhere one merge of (b merged with c) from a, both appear,
    the worlds after agree (associativity)."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0

        def merges_of(w: _World) -> list[_Effect]:
            return [e for x in W.model.bound(w.act.span) for e in x.effects if e.kind == "merges"]

        def leftbias(mine: dict[str, Any], other: dict[str, Any], eff: _Effect) -> dict[str, Any]:
            return {v: (mine[v] if mine.get(v) != eff.absent.get(v) and v in mine else other.get(v))
                    for v in eff.other}

        merged = []
        for w in W.worlds:
            if w.action is None:
                continue
            for eff in merges_of(w):
                other = {v: _normalize(w.data.get(arg)) for v, arg in eff.other.items()}
                if any(v not in w.pre for v in eff.other):
                    notes.append(f"{w.act.path}: '{w.kind}' merges with no read of "
                                 f"{[v for v in eff.other if v not in w.pre]} before — unwitnessed")
                    continue
                expected = leftbias(w.pre, other, eff)
                shown = {v: w.post[v] for v in eff.other if v in w.post}
                if not shown:
                    notes.append(f"{w.act.path}: '{w.kind}' merged and nothing read after")
                    continue
                judged += 1
                wrong = [v for v in shown if shown[v] != expected[v]]
                if wrong:
                    diagnostics.append(
                        f"{w.act.path}: '{w.kind}' absorbed {other} into {w.pre}; left-biased, "
                        f"the world should show {expected}, it shows {shown} — wrong on {wrong}")
                merged.append((w, eff, other, expected))
        # associativity: (b then c) from a, against one merge of (b ⊔ c) from a
        for i, (w1, e1, b, _) in enumerate(merged):
            for w2, e2, c_, _ in merged[i + 1:]:
                if w2.act.at <= w1.act.to or e1 is not e2:
                    continue
                if not _equal_on(w1.post, w2.pre, e1.other):
                    continue  # not adjacent on these variables
                bc = leftbias(b, c_, e1)
                for w3, e3, d, _ in merged:
                    if w3 in (w1, w2) or e3 is not e1 or d != bc:
                        continue
                    if not _equal_on(w1.pre, w3.pre, e1.other):
                        continue
                    shared = [v for v in e1.other if v in w2.post and v in w3.post]
                    if not shared:
                        continue
                    judged += 1
                    moved = [v for v in shared if w2.post[v] != w3.post[v]]
                    if moved:
                        diagnostics.append(
                            f"{w3.act.path}: merging {b} then {c_} from {w1.pre} leaves "
                            f"{w2.post}; merging their merge {bc} from the same world leaves "
                            f"{w3.post} — not associative on {moved}")
        return judged
    return _stretch_check("conduct/merge", tree, path, rel, judge)


def stamped(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """a-change-moves-the-validator: whenever an act moved a projected variable, the
    validator read after the act differs from the one read before it. RFC 9110's strong
    validator, the direction the RFC states; a stamp that moves without a change is not
    forbidden by the source and is not counted here."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        if not W.validators:
            notes.append(f"{path}: the model declares no validator — nothing stamped")
            return 0
        judged = 0
        for w in W.worlds:
            if w.action is None or w.act.is_call:
                continue
            moved = [v for v in W.projections if v in w.pre and v in w.post
                     and w.pre[v] != w.post[v]]
            if not moved:
                continue
            if w.stamp_before is None or w.stamp_after is None:
                notes.append(f"{w.act.path}: '{w.kind}' moved {moved} and the stamp was not "
                             "read on both sides — unwitnessed")
                continue
            judged += 1
            if w.stamp_before == w.stamp_after:
                diagnostics.append(
                    f"{w.act.path}: '{w.kind}' moved {moved} and the validator still reads "
                    f"{w.stamp_after!r} — a change that did not move the stamp")
        return judged
    return _stretch_check("conduct/stamped", tree, path, rel, judge)


def conditional(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """a-conditional-write-compares-before-it-writes: an act whose action `requires` a
    validator argument proceeds (outcome ok) when the stamp it was handed equals the stamp
    the world showed before it, and refuses — error outcome, no write through any door
    the model knows — when it does not. If-Match and 412, on a tape."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        requires = {c.id: (c.payload.get("requires") or {}).get("validator")
                    for c in W.model_node.children if c.kind == "action"}
        for i, act in enumerate(W.acts):
            bound = W.model.bound(act.span)
            arg = next((requires.get(a.id) for a in bound if requires.get(a.id)), None)
            if not arg:
                continue
            data = act.span.payload.get("data") or {}
            if arg not in data:
                continue
            handed = _normalize(data[arg])
            w = next((x for x in W.worlds if x.act is act), None)
            # the stamp before, read here directly: an errored act has no _World
            before = None
            for v in W.validators:
                for pos, e in reversed(W.stream):
                    if pos >= act.at:
                        continue
                    if _through(e, v.doors):
                        if (val := v.value(e)) is not None:
                            before = val
                            break
                        continue
                    if _through(e, W.model.known):
                        break
                if before is not None:
                    break
            if before is None:
                notes.append(f"{act.path}: '{act.span.kind}' was handed {handed!r} and the "
                             "stamp was not read before it — unwitnessed")
                continue
            judged += 1
            outcome = act.span.payload.get("outcome")
            wrote = [_named(e) for _, e in act.events if _through(e, W.model.known)]
            if handed == before:
                if outcome != "ok":
                    diagnostics.append(
                        f"{act.path}: '{act.span.kind}' was handed the current stamp "
                        f"{handed!r} and refused — a match that did not proceed")
            else:
                if outcome == "ok" or wrote:
                    diagnostics.append(
                        f"{act.path}: '{act.span.kind}' was handed {handed!r}, the world's "
                        f"stamp was {before!r}, and it {'proceeded' if outcome == 'ok' else 'wrote ' + str(sorted(set(wrote)))} "
                        "— a precondition that did not hold and a write that happened anyway")
        return judged
    return _stretch_check("conduct/conditional", tree, path, rel, judge)


# --- conduct/eventually: what the model promises, happens within the horizon ----------------


def eventually(tree: Quern | TreeStore, path: str, rel: str) -> Conformance:
    """what-is-promised-eventually-happens: for each `promise` of the model and each act
    whose projected world after satisfies `when`, some later act's world after — within
    `within` acts — satisfies `then` or `unless`. A promise with no `within` cannot be
    refuted by a finite tape and is only noted while open; a promise whose horizon runs
    past the tape's end is noted, not counted."""
    def judge(W: _Worlds, diagnostics, notes) -> int:
        judged = 0
        promises = []
        for c in W.model_node.children:
            if c.kind == "promise":
                when = _compile(str(c.payload.get("when", "")), f"promise '{c.id}' when")
                then = _compile(str(c.payload.get("then", "")), f"promise '{c.id}' then")
                unless_src = str(c.payload.get("unless", "")).strip()
                unless = _compile(unless_src, f"promise '{c.id}' unless") if unless_src else None
                promises.append((c.id, when, then, unless, c.payload.get("within")))
        if not promises:
            notes.append(f"{path}: the model makes no promise — nothing to keep")
            return 0
        spans = [w for w in W.worlds if w.action is not None and not w.act.is_call]

        def holds(expr, world):
            try:
                return bool(expr({**world, **_LITERALS}))
            except ValueError:
                return None  # a variable the world did not show

        for pid, when, then, unless, within in promises:
            for i, w in enumerate(spans):
                made = holds(when, w.post)
                if not made:
                    continue
                later = spans[i + 1:]
                window = later[:within] if within else later
                kept = None
                for j, x in enumerate(window):
                    if holds(then, x.post) or (unless is not None and holds(unless, x.post)):
                        kept = j
                        break
                if kept is not None:
                    judged += 1
                    continue
                if within is None or len(later) < within:
                    notes.append(f"{w.act.path}: '{pid}' made by '{w.kind}' and still open "
                                 f"when the tape ends ({len(later)} act(s) later"
                                 f"{f', horizon {within}' if within else ', no horizon'}) — "
                                 "unwitnessed, not broken")
                    continue
                judged += 1
                diagnostics.append(
                    f"{w.act.path}: '{w.kind}' left the world in the state that makes "
                    f"'{pid}' ({w.post}), and {within} act(s) later it is still not kept — "
                    "a promise broken within its horizon")
        return judged
    return _stretch_check("conduct/eventually", tree, path, rel, judge)


# --- conduct/doors: every write function the boundary records is some action's door --------


def doors_census(tree: Quern | TreeStore, path: str) -> Conformance:
    """How many write functions the model's `boundary` declares that no action admits through
    any door — `via` of an effect or `touches.via`. On the model, like conduct/checkable. A
    model declaring no boundary is noted: its frame holds declared doors only."""
    from quern import get_node
    node = get_node(tree, path)
    if node is None:
        raise ValueError(f"no node at '{path}'")
    if node.kind != "model":
        raise ValueError(f"'{path}' is a '{node.kind}', not a model")
    writes = [w for c in node.children if c.kind == "boundary"
              for w in (c.payload.get("writes") or [])]
    if not writes:
        return Conformance(check="conduct/doors", violations=0,
                           notes=[f"{path}: no `boundary` declares the write functions — the "
                                  "frame holds declared doors only, not the whole state"])
    # every door pattern any action admits, as the name pattern it matches
    admitted: list[str] = []
    for c in node.children:
        if c.kind != "action":
            continue
        for k in c.children:
            specs = []
            if k.kind in EFFECTS:
                specs = k.payload.get("via")
            elif k.kind == "touches":
                specs = k.payload.get("via")
            for spec in (specs if isinstance(specs, list) else [specs]):
                if isinstance(spec, str):
                    admitted.append(spec)
                elif isinstance(spec, dict) and spec.get("event"):
                    admitted.append(str(spec["event"]))
    diagnostics = []
    for w in writes:
        # a boundary function is covered if some admitted door's name pattern would match a
        # call of it — or the boundary's own pattern matches the door's name
        if not any(fnmatch(w, a) or fnmatch(a, w) for a in admitted):
            diagnostics.append(f"{path}: the boundary records '{w}' as a write and no action "
                               "admits it through any door — a write the frame could never see")
    return Conformance(check="conduct/doors", violations=len(diagnostics),
                       diagnostics=diagnostics, judged=len(writes))


def doors_count(tree, path) -> float:
    return float(doors_census(tree, path).violations)


# --- vocabulary coverage: what of the world is declared at all ------------------------------


def declared(model: Node, tools: Iterable[str] = ()) -> dict[str, tuple[int, int]]:
    """How much of a model's world is declared in the vocabulary, per kind — the number that
    bounds what any law can see. Laws bind by kind and grow on their own; this is the side
    that has to grow by hand, app by app, and the one the report should show:

    - `projected`: state-vars with a projection / all state-vars
    - `effects`: actions declaring an effect (creates/mutates/deletes/merges) / all actions
    - `bounded`: actions declaring a boundary (touches) / all actions
    - `validators`: validators declared (0 or 1 is the common case)
    - `tools`: tools the model names as event-kinds / tools the app registers (when given)
    """
    vars_ = [c for c in model.children if c.kind == "state-var"]
    actions = [c for c in model.children if c.kind == "action"]
    kinds = {c.id for c in model.children if c.kind == "event-kind"}
    out = {
        "projected": (sum(1 for v in vars_ if v.payload.get("shown")), len(vars_)),
        "effects": (sum(1 for a in actions if any(k.kind in EFFECTS for k in a.children)),
                    len(actions)),
        "bounded": (sum(1 for a in actions if any(k.kind == "touches" for k in a.children)),
                    len(actions)),
        "validators": (sum(1 for c in model.children if c.kind == "validator"), 1),
    }
    tools = list(tools)
    if tools:
        out["tools"] = (sum(1 for t in tools if t in kinds), len(tools))
    return out


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


def _count_of(fn):
    return lambda tree, path, rel: float(fn(tree, path, rel).violations)


from .spec import CONDUCT_SPEC  # noqa: E402

register_native("conduct/effect", effect_count, CONDUCT_SPEC["conduct/effect"])
register_native("conduct/faithful", faithful_count, CONDUCT_SPEC["conduct/faithful"])
register_native("conduct/frame", frame_count, CONDUCT_SPEC["conduct/frame"])
register_native("conduct/refusal", refusal_count, CONDUCT_SPEC["conduct/refusal"])
register_native("conduct/checkable", checkable_count, CONDUCT_SPEC["conduct/checkable"])
register_native("conduct/agrees", agrees_count, CONDUCT_SPEC["conduct/agrees"])
register_native("conduct/doors", doors_count, CONDUCT_SPEC["conduct/doors"])
for _name, _fn in (("twice", twice), ("last-write", last_write), ("commute", commute),
                   ("undo", undo), ("durable", durable), ("same-story", same_story),
                   ("constructible", constructible), ("merge", merge), ("stamped", stamped),
                   ("conditional", conditional), ("eventually", eventually)):
    register_native(f"conduct/{_name}", _count_of(_fn), CONDUCT_SPEC[f"conduct/{_name}"])
