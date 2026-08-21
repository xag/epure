"""The draft: a model's guards and updates, proposed from its tapes and measured against the
ones a person wrote.

A model's frame is generated already - effects, doors and boundaries come off the tapes
(`epure.survey`) - and a person still writes the arithmetic: what each action does to each
variable (`updates`) and when it may happen (`guard`). This reads the same tapes the natives
judge, projects the world before and after every bound act the way `conduct/agrees` does,
and proposes, per (action, variable), the SIMPLEST expression of a small grammar that every
sample satisfies - the frame (no update), a constant, an argument, another variable, an
increment, a saturating increment - and per action the guard its pre-worlds support: a
boolean always true or false, an enum value never seen while the rest were.

A guard is drafted from REFUSALS: a refused bound act (a span whose outcome is `error`,
which `conduct/refusal` already holds to writing nothing) is a world where the guard was
false, and the draft is the simplest predicate of a small grammar - a literal, `var == c`,
`var != c`, `var < c`, `var >= c`, and conjunctions of two - that holds on every taken
pre-world and fails on every refused one. Without a refusal of the act there are no
negatives, and the draft says "positives only": the booleans that never varied, which is
at most necessary and is reported as such, never as a guard.

A row that lacks a value is not thrown away. An act taken before the variable's door ever
showed it (the first pick, before any pick row exists; a Monday act, before the first tick
wrote the clock) still witnesses a constant or an argument - only the candidates that READ
the missing value cannot be judged on it. Such a candidate that fits every row it can be
judged on is reported `partial`, with the observation that would settle it: which act, on
which tape, took place with which operand unread. `--propose` prints exactly those, one per
row the draft could not settle - the next flight to fly, named by the data on hand.

What it is for is a number, not a model. Held against a model a person wrote, it says how
much of that model the tapes already determine - equivalent over the whole finite domain,
not merely on the samples - and the remainder is the human's share: the arithmetic no tape
witnessed, the guard no refusal exercised, the saturation bound no run reached. Two
consumers make the number a measurement rather than a fit. A drafted expression is a
hypothesis about the app, exactly as partial as the tapes that made it: a path no tape took
is a case it cannot see, which is why the draft is compared and counted, never installed.

Equivalence is judged where the world can BE. The domains say what a variable could hold;
the model's own actions say what it can hold while the others hold what they hold, and a
guard says when an act runs at all. So the grid is the reachable set (`epure.prove`'s own
walk), narrowed for an update to the states where its action is enabled - because an update
is arithmetic that never runs in a world its guard refuses. The two equivalences are told
apart and counted apart: `domain`, agreeing everywhere, and `enabled`/`reachable`, agreeing
everywhere the model can be. Both are honest; only the first is unconditional. The same
restriction is what makes `--propose` name an experiment somebody can actually fly, and a
sampled pre-world the model cannot reach is counted out loud rather than quietly dropped -
it is the app in a state the model calls impossible, which is a finding, not a rounding.

    python -m epure.draft --model chores_model.package:MODEL --tapes tests/flights
    python -m epure.draft --model health_model.package:MODEL --tapes scenarios/flights --json
    python -m epure.draft --model ... --tapes ... --propose   # the discriminating flights
"""

from __future__ import annotations

import argparse
import importlib
import itertools
import json
import random
import re
import sys
from pathlib import Path
from typing import Any, Callable

from quern import Node, Quern

from epure.behavior import _LITERALS, _Worlds
from epure.conformance import _normalize
from epure.prove import _compile, _domain, reachable_from_node
from epure.tape import import_scenario

GRID_CAP = 4096   # beyond this many points the grid is sampled, deterministically


# --- samples: what the tapes say each action did ---------------------------------------------


class Samples:
    """Per action: the projected (pre, binding, post) of every bound span act, across tapes,
    and the pre-worlds of every REFUSED one - the worlds where the guard was false."""

    def __init__(self) -> None:
        self.by_action: dict[str, list[tuple[dict, dict, dict]]] = {}
        # where each sample came from, parallel to by_action: (tape, act path, span kind)
        self.where: dict[str, list[tuple[str, str, str]]] = {}
        # per sample, the variables whose door WAS read before the act and showed nothing -
        # the store held no value (a clock before the first tick, a row before the first
        # write). Not the same remainder as an unread variable: the harness read, and the
        # projection said the store says nothing, where the model's init says something.
        self.empty: dict[str, list[set[str]]] = {}
        self.tapes = 0
        self.acts = 0
        # refused acts that bind an action, with the world read before each: the only
        # evidence a guard can be drafted from, since a guard is what is refused
        self.refused: dict[str, list[tuple[dict, dict]]] = {}

    @property
    def refusals(self) -> dict[str, int]:
        return {k: len(v) for k, v in self.refused.items()}

    def add(self, W: _Worlds, tape: str = "") -> None:
        self.tapes += 1
        for w in W.worlds:
            if w.action is None or w.act.is_call:
                continue
            self.acts += 1
            self.by_action.setdefault(w.action["id"], []).append((w.pre, w.binding, w.post))
            self.where.setdefault(w.action["id"], []).append(
                (tape, w.act.path, w.act.span.kind))
            empty: set[str] = set()
            for var, proj in W.projections.items():
                if var in w.pre:
                    continue
                try:
                    if W._read_before(proj, w.act.at) is not None:
                        empty.add(var)
                except ValueError:
                    continue
            self.empty.setdefault(w.action["id"], []).append(empty)
        for a in W.acts:
            if a.span.payload.get("outcome") != "error" or a.is_call:
                continue
            bound = W.model.bound(a.span)
            if len(bound) != 1:
                continue
            action = W.by_id[bound[0].id]
            pre: dict[str, Any] = {}
            for var, proj in W.projections.items():
                try:
                    before = W._read_before(proj, a.at)
                    if before is not None and (v := proj.value(before[1])) is not None:
                        pre[var] = v
                except ValueError:
                    continue
            data = a.span.payload.get("data") or {}
            binding = {n: _normalize(data[n]) for n in action["args"] if n in data}
            self.refused.setdefault(action["id"], []).append((pre, binding))


def collect(model: Node, tapes: list[Path], link: str) -> Samples:
    out = Samples()
    for tape in tapes:
        session = import_scenario(tape)
        session.id = tape.stem
        session.links = {"model": [link]}
        tree = Quern()
        tree.root.children = [model.model_copy(deep=True), session]
        out.add(_Worlds(tree, tape.stem, "model"), tape.stem)
    return out


# --- the grammar of drafts, simplest first ----------------------------------------------------


def _lit(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v) if v >= 0 else f"0 - {-v}"
    return repr(str(v))


def draft_update(var: str, dom: list[Any], samples: list[tuple[dict, dict, dict]],
                 args: list[str], vars: list[str]) -> tuple[str | None, str]:
    """The simplest expression every sample satisfies, as (expr, status). expr None with
    status 'frame' means the tapes say the action leaves the variable alone; None with
    'unwitnessed' that no sample shows the variable after the act; None with 'unresolved'
    that the grammar has no expression for what was seen. A row that lacks a value the
    candidate reads (the variable itself, or the other variable it copies) does not refute
    the candidate and does not confirm it: a candidate that fits every row it can be judged
    on, and cannot be judged on some, is 'partial' - see draft_update_where for which."""
    expr, status, _ = draft_update_where(var, dom, samples, args, vars)
    return expr, status


def draft_update_where(var: str, dom: list[Any], samples: list[tuple[dict, dict, dict]],
                       args: list[str], vars: list[str],
                       names: dict[str, list[Any]] | None = None
                       ) -> tuple[str | None, str, list[tuple[int, str]]]:
    """draft_update, plus the rows (index into `samples`, unread operand) a partial draft
    could not be judged on - empty for a settled verdict. With `names` (the domains of the
    variables and arguments) the grammar reaches further when the simple forms fail: a
    boolean is drafted as the simplest PREDICATE over the world before that is true exactly
    where the sample after is (status 'predicate'); an int as a CONDITIONAL between two simple
    expressions, `e2 + (P) * (e1 - e2)`, the hand's own form (status 'conditional') - the
    richer grammar of 0.13.2, written for the rows the first grammar left unresolved (a
    rhythm's pending flag, a calendar's day), after those rows existed and not before."""
    rows = [(i, pre, b, post[var]) for i, (pre, b, post) in enumerate(samples) if var in post]
    if not rows:
        return None, "unwitnessed", []

    def judged(needs: Callable, fits: Callable) -> tuple[bool, list[tuple[int, str]]]:
        """(every judgeable row fits, the rows that could not be judged)."""
        missing: list[tuple[int, str]] = []
        for i, pre, b, post in rows:
            if (need := needs(pre, b)) is not None:
                missing.append((i, need))
                continue
            if not fits(pre, b, post):
                return False, []
        return True, missing

    # the candidates, simplest first: (status, expr, what a row must show, the test)
    candidates: list[tuple[str, str | None, Callable, Callable]] = []
    candidates.append(("frame", None, lambda pre, b: None if var in pre else var,
                       lambda pre, b, post: post == pre[var]))
    posts = {json.dumps(post, sort_keys=True) for _, _, _, post in rows}
    if len(posts) == 1:
        candidates.append(("constant", _lit(rows[0][3]), lambda pre, b: None,
                           lambda pre, b, post: True))
    for a in args:
        candidates.append(("argument", a, lambda pre, b, a=a: None if a in b else a,
                           lambda pre, b, post, a=a: post == b[a]))
    for other in vars:
        if other != var:
            candidates.append(("variable", other,
                               lambda pre, b, o=other: None if o in pre else o,
                               lambda pre, b, post, o=other: post == pre[o]))
    numeric = all(isinstance(post, (int, float)) and not isinstance(post, bool)
                  for _, _, _, post in rows)
    if numeric:
        deltas = {post - pre[var] for _, pre, _, post in rows
                  if var in pre and isinstance(pre[var], (int, float))}
        if len(deltas) == 1:
            k = deltas.pop()
            candidates.append(("increment",
                               f"{var} + {_lit(k)}" if k >= 0 else f"{var} - {_lit(-k)}",
                               lambda pre, b: None if var in pre else var,
                               lambda pre, b, post, k=k: post == pre[var] + k))
        hi = max((v for v in dom if isinstance(v, (int, float))), default=None)
        if hi is not None:
            for k in (1, 2, 3):
                candidates.append(("saturating", f"min({var} + {k}, {hi})",
                                   lambda pre, b: None if var in pre else var,
                                   lambda pre, b, post, k=k: post == min(pre[var] + k, hi)))
    # the richer grammar, tried only when every simple form has failed (below)
    richer = _richer(var, rows, args, vars, names) if names else None

    # The first candidate no row refutes decides - settled when every row could judge it,
    # partial otherwise. A later candidate every row CAN judge does not outrank it: when no
    # sample shows the value before the act, "the constant 0" and "the frame" are the same
    # evidence, and the simpler claim stands, marked for what it still needs.
    # ...and a candidate no row could judge is not evidence of anything: it is skipped, not
    # proposed - eight completions on a Monday before the clock was ever written do not
    # draft `today` for a counter, they draft the increment every one of them shows.
    frame_judged = any(var in pre for _, pre, _, _ in rows)
    for status, expr, needs, fits in candidates:
        ok, missing = judged(needs, fits)
        if not ok:
            continue
        if len(missing) == len(rows):
            continue
        if not missing:
            if status == "constant" and not frame_judged:
                # the constant every sample shows, with no sample showing the before: the
                # frame is not refuted and not confirmed, and this says so
                return expr, "partial", [(i, var) for i, _, _, _ in rows]
            return expr, status, []
        return expr, "partial", missing
    if richer is not None:
        return richer[0], richer[1], []
    return None, "unresolved", []


def _richer(var: str, rows: list[tuple[int, dict, dict, Any]], args: list[str],
            vars: list[str], names: dict[str, list[Any]]) -> tuple[str, str] | None:
    """The predicate and conditional forms, over rows that show every name they read."""
    worlds = [{**pre, **b} for _, pre, b, _ in rows]
    posts = [post for _, _, _, post in rows]
    if all(isinstance(v, bool) for v in posts):
        taken = [w for w, v in zip(worlds, posts) if v]
        denied = [w for w, v in zip(worlds, posts) if not v]
        pred = _separating(taken, denied, names)
        return (pred, "predicate") if pred else None
    if not all(isinstance(v, (int, float)) for v in posts):
        return None
    ints = [n for n, dom in names.items()
            if all(isinstance(d, (int, float)) and not isinstance(d, bool) for d in dom)]
    simple: list[tuple[str, Callable[[dict], Any]]] = []
    simple.append((var, lambda w: w.get(var)))
    for n in ints:
        if n != var:
            simple.append((n, lambda w, n=n: w.get(n)))
    for n in ints:
        simple.append((f"{n} + 1", lambda w, n=n: None if w.get(n) is None else w[n] + 1))
    for c in sorted({v for v in posts}):
        simple.append((_lit(c), lambda w, c=c: c))
    for (s2, f2), (s1, f1) in itertools.permutations(simple, 2):
        v1 = [f1(w) for w in worlds]
        v2 = [f2(w) for w in worlds]
        if any(v is None for v in v1 + v2):
            continue
        taken, denied = [], []
        ok = True
        for w, post, a, b in zip(worlds, posts, v1, v2):
            if post == a and post != b:
                taken.append(w)
            elif post == b and post != a:
                denied.append(w)
            elif post != a and post != b:
                ok = False
                break
        if not ok or not taken or not denied:
            continue
        pred = _separating(taken, denied, names)
        if pred:
            return f"{s2} + ({pred}) * ({s1} - {s2})", "conditional"
    return None


def draft_guard(pres: list[dict], variables: dict[str, list[Any]],
                refused: list[dict] | None = None, args: dict[str, list[Any]] | None = None,
                bindings: list[dict] | None = None, refused_bindings: list[dict] | None = None
                ) -> str:
    """The guard the worlds support. With REFUSALS - the pre-worlds of acts the app refused -
    the simplest predicate of the grammar (a literal, `x == c`, `x != c`, `x < c`, `x >= c`
    over a variable or an argument, then conjunctions of two) true on every taken pre-world
    and false on every refused one. Without refusals, positives only: every boolean that
    never varied where it was projected - at most necessary, never sufficient, and the enum
    and arithmetic forms are left alone because, from positives alone, they only overfit (an
    assignee never seen is not an assignee forbidden)."""
    if refused:
        names = {**variables, **(args or {})}
        taken = [{**pre, **b} for pre, b in zip(pres, bindings or [{}] * len(pres))]
        denied = [{**pre, **b} for pre, b in
                  zip(refused, refused_bindings or [{}] * len(refused))]
        return _guard_from_negatives(taken, denied, names)
    terms: list[str] = []
    for var, dom in variables.items():
        seen = [pre[var] for pre in pres if var in pre]
        if not seen or not all(isinstance(d, bool) for d in dom):
            continue  # `[0, 1] == [False, True]` in Python; a bool is a bool by type
        if all(seen):
            terms.append(var)
        elif not any(seen):
            terms.append(f"not {var}")
    return " and ".join(terms)


def _atoms(names: dict[str, list[Any]]) -> list[tuple[str, Callable[[dict], bool | None]]]:
    """Every atomic predicate of the grammar over the names, with its evaluator; an
    evaluator answers None where the world does not show a name it reads. Booleans as
    themselves and negated; enums and ints against each value of their domain (==, !=, and
    for ints < and >=); and for each pair of int names the difference against a small
    constant (`a - b >= c`, `a - b < c`, c in 0..3) - the cadence's "two days since",
    which no single-variable atom can say (0.13.2)."""
    out: list[tuple[str, Callable[[dict], bool | None]]] = []
    ints: list[str] = []
    for n, dom in names.items():
        if all(isinstance(d, bool) for d in dom):
            out.append((n, lambda w, n=n: w.get(n) if n in w else None))
            out.append((f"not {n}", lambda w, n=n: (not w[n]) if n in w else None))
            continue
        numeric = all(isinstance(d, (int, float)) for d in dom)
        if numeric:
            ints.append(n)
        for c in dom:
            out.append((f"{n} == {_lit(c)}", lambda w, n=n, c=c: (w[n] == c) if n in w else None))
            out.append((f"{n} != {_lit(c)}", lambda w, n=n, c=c: (w[n] != c) if n in w else None))
            if numeric:
                out.append((f"{n} < {_lit(c)}", lambda w, n=n, c=c: (w[n] < c) if n in w else None))
                out.append((f"{n} >= {_lit(c)}", lambda w, n=n, c=c: (w[n] >= c) if n in w else None))
    for a in ints:
        for b in ints:
            if a == b:
                continue
            for c in (0, 1, 2, 3):
                out.append((f"{a} - {b} >= {c}",
                            lambda w, a=a, b=b, c=c: (w[a] - w[b] >= c) if a in w and b in w else None))
                out.append((f"{a} - {b} < {c}",
                            lambda w, a=a, b=b, c=c: (w[a] - w[b] < c) if a in w and b in w else None))
    return out


def _separating(taken: list[dict], denied: list[dict], names: dict[str, list[Any]]) -> str:
    """The simplest predicate of the grammar true on every taken world and false on every
    denied one: one atom, then a conjunction of two, then a disjunction of two, then of
    three; '' when nothing separates them. An atom some world cannot decide is left out -
    a predicate must be decided on every world it is proposed over."""
    if not taken or not denied:
        return ""
    cols: list[tuple[str, list[bool], list[bool]]] = []
    for src, f in _atoms(names):
        pv = [f(w) for w in taken]
        nv = [f(w) for w in denied]
        if any(v is None for v in pv) or any(v is None for v in nv):
            continue
        if all(pv) and not any(nv):
            return src
        cols.append((src, pv, nv))
    # a conjunction needs atoms true on every taken world; a disjunction, atoms false on
    # every denied one - the rest cannot take part, which keeps the search small
    conj = [c for c in cols if all(c[1])]
    for (s1, p1, n1), (s2, p2, n2) in itertools.combinations(conj, 2):
        if not any(a and b for a, b in zip(n1, n2)):
            return f"{s1} and {s2}"
    disj = [c for c in cols if not any(c[2])]
    for (s1, p1, n1), (s2, p2, n2) in itertools.combinations(disj, 2):
        if all(a or b for a, b in zip(p1, p2)):
            return f"{s1} or {s2}"
    for (s1, p1, _), (s2, p2, _), (s3, p3, _) in itertools.combinations(disj, 3):
        if all(a or b or c for a, b, c in zip(p1, p2, p3)):
            return f"{s1} or {s2} or {s3}"
    return ""


def _guard_from_negatives(taken: list[dict], denied: list[dict], names: dict[str, list[Any]]
                          ) -> str:
    return _separating(taken, denied, names)


# --- equivalence over the finite domain -----------------------------------------------------


_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def _mentions(src: str, names: dict[str, list[Any]]) -> list[str]:
    return sorted({t for t in _IDENT.findall(src.replace("'", " ")) if t in names})


class Reach:
    """The model's own reachable states, as the grid the draft is measured over.

    The domains say what a variable COULD hold; the model's actions say what it can hold
    while the others hold what they hold. A disagreement at a point the model cannot reach
    is a disagreement no flight can put on tape - naming it as the experiment sends a person
    to fly the unflyable, and counting it as a difference charges the draft for a world that
    does not exist. So the grid is the reachable set, and the two equivalences are told
    apart rather than merged: `domain` when the expressions agree everywhere, `reachable`
    when they agree on every state the model reaches and part somewhere it does not.

    An argument is not restricted: it is an input, free over its declared domain in every
    world. The restriction is on the state."""

    def __init__(self, order: list[str], states: set[tuple]) -> None:
        self.order = order
        self.index = {n: i for i, n in enumerate(order)}
        self.states = states
        self._proj: dict[tuple[str, ...], set[tuple]] = {}
        self._where: dict[str, "Reach"] = {}

    @classmethod
    def of(cls, model: Node) -> "Reach":
        order, states = reachable_from_node(model)
        return cls(order, states)

    def project(self, names: list[str]) -> set[tuple]:
        """The distinct values the named variables take TOGETHER over the reachable set."""
        key = tuple(names)
        if key not in self._proj:
            idx = [self.index[n] for n in names]
            self._proj[key] = {tuple(s[i] for i in idx) for s in self.states}
        return self._proj[key]

    def holds(self, world: dict) -> bool:
        """Is this world - however partial, a projection reads what the doors showed - one
        the model reaches? A world of no known variables is vacuously reachable."""
        known = [n for n in world if n in self.index]
        if not known:
            return True
        return tuple(world[n] for n in known) in self.project(known)

    def where(self, guard: str, names: dict[str, list[Any]]) -> "Reach":
        """The reachable states this guard admits - where the action is ENABLED.

        An update is arithmetic that only ever runs when the guard let the act through, so
        a world the guard refuses is no more a place the two expressions can be told apart
        than an unreachable one. A guard over arguments as well as state (`day >= today`)
        restricts no state on its own: some binding may satisfy it, and a state is excluded
        only when nothing decides it in."""
        if not guard.strip():
            return self
        if guard in self._where:
            return self._where[guard]
        mention = [n for n in _mentions(guard, names) if n in self.index]
        if not mention:
            return self
        f = _compile(guard, "guard")
        ok = set()
        for combo in self.project(mention):
            env = {**_LITERALS, **dict(zip(mention, combo))}
            try:
                admitted = bool(f(env))
            except Exception:
                admitted = True   # the guard needs an argument to decide: not a refusal
            if admitted:
                ok.add(combo)
        idx = [self.index[n] for n in mention]
        kept = Reach(self.order, {s for s in self.states if tuple(s[i] for i in idx) in ok})
        self._where[guard] = kept
        return kept


def _grid(free: list[str], names: dict[str, list[Any]], reach: Reach | None
          ) -> Any:
    """The points to try, as environments over `free`: the reachable combinations of the
    state variables among them crossed with the full domains of the arguments, or the whole
    product when there is no reachable set to restrict it. Sampled deterministically past
    GRID_CAP, so a big grid is a sample and never a silent truncation of the first N."""
    state = [n for n in free if reach is not None and n in reach.index]
    rest = [n for n in free if n not in state]
    bases = sorted(reach.project(state), key=repr) if reach is not None else [()]
    doms = [names[n] for n in rest]
    total = len(bases)
    for d in doms:
        total *= len(d)
    if total <= GRID_CAP:
        combos = ((b, t) for b in bases for t in itertools.product(*doms))
    else:
        rng = random.Random(0)
        combos = ((rng.choice(bases), [rng.choice(d) for d in doms]) for _ in range(GRID_CAP))
    for base, tail in combos:
        yield {**dict(zip(state, base)), **dict(zip(rest, tail))}


def equivalent(a: str, b: str, names: dict[str, list[Any]], *, boolean: bool = False,
               reach: Reach | None = None) -> bool:
    """Two expressions agree at every point of the grid over the variables and arguments
    either mentions - the whole finite domain, or, given `reach`, the states the model can
    actually be in; sampled past GRID_CAP either way."""
    fa, fb = _compile(a or "true", "draft"), _compile(b or "true", "hand")
    free = sorted(set(_mentions(a, names)) | set(_mentions(b, names)))
    for pt in _grid(free, names, reach):
        env = {**_LITERALS, **pt}
        try:
            x, y = fa(env), fb(env)
        except Exception:
            continue
        if boolean:
            x, y = bool(x), bool(y)
        else:
            x, y = _normalize(x), _normalize(y)
        if x != y:
            return False
    return True


def _verdict(draft: str, hand: str, names: dict[str, list[Any]], reach: Reach | None,
             *, boolean: bool = False, scope: str = "reachable") -> tuple[str, str]:
    """(verdict, scope): equivalent everywhere - `domain` - or equivalent only over the
    restricted grid `reach` stands for, which the caller names, because the restriction is
    not the same one twice: an update is judged where the model reaches AND the act is
    enabled, a guard only where the model reaches. `different` then means a world exists
    that a flight could actually fly."""
    if equivalent(draft, hand, names, boolean=boolean):
        return "equivalent", "domain"
    if reach is not None and equivalent(draft, hand, names, boolean=boolean, reach=reach):
        return "equivalent", scope
    return "different", "domain" if reach is None else scope


# --- the measurement --------------------------------------------------------------------------


def measure(model: Node, samples: Samples, *, reach: Reach | None = None) -> dict[str, Any]:
    variables = {c.id: _domain(c.payload, f"state-var '{c.id}'")
                 for c in model.children if c.kind == "state-var"}
    projected = {c.id for c in model.children
                 if c.kind == "state-var" and c.payload.get("shown")}
    if reach is None:
        reach = Reach.of(model)
    report: dict[str, Any] = {"tapes": samples.tapes, "acts": samples.acts,
                              "refusals": sum(samples.refusals.values()),
                              "reachable": len(reach.states), "unreachable_pre": 0,
                              "actions": [], "proposals": []}
    tally = {"updates": 0, "updates_equivalent": 0, "updates_different": 0,
             "updates_unwitnessed": 0, "updates_unresolved": 0, "updates_partial": 0,
             "updates_equivalent_enabled": 0,
             "frames": 0, "frames_agreed": 0, "frames_disputed": 0, "frames_unwitnessed": 0,
             "frames_partial": 0,
             "guards": 0, "guards_equivalent": 0, "guards_different": 0,
             "guards_equivalent_reachable": 0,
             "guards_unwitnessed": 0, "unguarded": 0, "unguarded_drafted": 0}
    for c in model.children:
        if c.kind != "action":
            continue
        args = {n: _domain(spec, f"arg '{n}'") for n, spec in (c.payload.get("args") or {}).items()}
        names = {**variables, **args}
        hand = {u["var"]: str(u["expr"]) for u in c.payload.get("updates") or []}
        guard = str(c.payload.get("guard") or "")
        # the updates are judged where the act can actually be taken: reachable AND enabled
        enabled = reach.where(guard, names)
        rows = samples.by_action.get(c.id, [])
        # a sampled pre-world the model cannot reach is not a rounding error: it is the app
        # in a state the model says is impossible, and it is exactly what restricting the
        # grid to the reachable set would otherwise hide. Counted, per run, out loud.
        unreachable = sum(1 for pre, _, _ in rows if not reach.holds(pre))
        report["unreachable_pre"] += unreachable
        row: dict[str, Any] = {"id": c.id, "samples": len(rows),
                               "refusals": samples.refusals.get(c.id, 0),
                               "unreachable_pre": unreachable,
                               "updates": {}, "frames": {}}
        where = samples.where.get(c.id, [])
        empty = samples.empty.get(c.id, [])
        for var in projected:
            expr, status, unsettled = draft_update_where(var, variables[var], rows, list(args),
                                                         list(variables), names)
            if var in hand:
                tally["updates"] += 1
                scope = "domain"
                if status in ("unwitnessed", "partial"):
                    verdict = status
                elif expr is None:
                    verdict = "unresolved" if status == "unresolved" else "different"
                else:
                    verdict, scope = _verdict(expr, hand[var], names, enabled,
                                              scope="enabled")
                tally[f"updates_{verdict}"] += 1
                if verdict == "equivalent" and scope == "enabled":
                    tally["updates_equivalent_enabled"] += 1
                entry = {"hand": hand[var], "draft": expr, "status": status,
                         "verdict": verdict, "scope": scope}
                if unsettled:
                    entry["unsettled"] = [
                        {"tape": where[i][0], "act": where[i][1], "span": where[i][2],
                         "unread": need,
                         "because": ("read, the store showed nothing"
                                     if i < len(empty) and need in empty[i] else "unread")}
                        for i, need in unsettled if i < len(where)]
                row["updates"][var] = entry
                if verdict in ("different", "partial", "unresolved"):
                    report["proposals"].append(_propose(c.id, var, hand[var], expr, verdict,
                                                        entry.get("unsettled"), rows, args,
                                                        names, enabled))
            else:
                tally["frames"] += 1
                verdict = ("unwitnessed" if status == "unwitnessed"
                           else "agreed" if status == "frame"
                           else "partial" if status == "partial"
                           else "disputed")
                tally[f"frames_{verdict}"] += 1
                if verdict == "disputed":
                    row["frames"][var] = {"draft": expr, "status": status, "verdict": verdict}
        refused = samples.refused.get(c.id, [])
        drafted = draft_guard([pre for pre, _, _ in rows], variables,
                              refused=[pre for pre, _ in refused], args=args,
                              bindings=[b for _, b, _ in rows],
                              refused_bindings=[b for _, b in refused]) if rows else ""
        row["guard"] = {"hand": guard, "draft": drafted,
                        "from": "refusals" if refused else "positives only"}
        if guard:
            tally["guards"] += 1
            scope = "domain"
            if not rows:
                verdict = "unwitnessed"
            else:
                verdict, scope = _verdict(drafted, guard, names, reach, boolean=True)
            tally[f"guards_{verdict}"] += 1
            if verdict == "equivalent" and scope == "reachable":
                tally["guards_equivalent_reachable"] += 1
            row["guard"]["verdict"] = verdict
            row["guard"]["scope"] = scope
            if verdict == "different" and not refused and guard.strip() != "true":
                report["proposals"].append({
                    "action": c.id, "var": None, "hand": guard, "draft": drafted,
                    "verdict": "different", "kind": "guard",
                    "experiment": f"take {c.id} in a world where `{guard}` is false: the app "
                                  "refusing puts the first negative on tape, the app "
                                  "proceeding refutes the hand guard"})
        else:
            tally["unguarded"] += 1
            if drafted:
                tally["unguarded_drafted"] += 1
        report["actions"].append(row)
    report["tally"] = tally
    return report


def _propose(action: str, var: str, hand: str, draft: str | None, verdict: str,
             unsettled: list[dict] | None, rows: list[tuple[dict, dict, dict]],
             args: dict[str, list[Any]], names: dict[str, list[Any]] | None = None,
             reach: Reach | None = None) -> dict[str, Any]:
    """The observation that separates the draft from the hand, for one row of the
    measurement: for a partial draft, the act that was taken with an operand unread (read it
    around that act next time); for a different draft, a point near the sampled worlds
    where the two expressions disagree; for an unresolved one, the samples the grammar has
    no word for."""
    out: dict[str, Any] = {"action": action, "var": var, "hand": hand, "draft": draft,
                           "verdict": verdict, "kind": "update"}
    if verdict == "partial":
        unread = [u for u in unsettled or [] if u["because"] == "unread"]
        empty = [u for u in unsettled or [] if u["because"] != "unread"]
        parts = []
        if unread:
            parts.append("read " + ", ".join(sorted({u["unread"] for u in unread}))
                         + " around " + "; ".join(f"{u['tape']} {u['act']}" for u in unread))
        if empty:
            parts.append("the store showed no " + ", ".join(sorted({u["unread"] for u in empty}))
                         + " before " + "; ".join(f"{u['tape']} {u['act']}" for u in empty)
                         + " - the model's init says what an empty store means, the store "
                           "does not; make the store hold it, or make the projection say it")
        out["experiment"] = "; ".join(parts)
        out["unsettled"] = unsettled
    elif verdict == "different" and draft is not None:
        out["experiment"] = f"take {action} where `{draft}` and `{hand}` differ"
        out["separating"] = _separating_point(draft, hand, rows, args, names, reach)
    elif verdict == "different":
        out["experiment"] = (f"the tapes say frame; take {action} in a world where `{hand}` "
                             "moves the variable")
    else:
        out["experiment"] = (f"no expression of the grammar fits the {len(rows)} sample(s); "
                             "a richer grammar, or a read around each act")
    return out


def _separating_point(draft: str, hand: str, rows: list[tuple[dict, dict, dict]],
                      args: dict[str, list[Any]], names: dict[str, list[Any]] | None = None,
                      reach: Reach | None = None) -> dict[str, Any] | None:
    """A point where the two expressions disagree, as near as the grammar can find to a
    world the tapes held: first the sampled pre-worlds with the arguments swept over their
    domains; failing that - a draft that fits every sample differs from the hand only
    elsewhere - the reachable states of the names either mentions, the disagreement fewest
    variables away from some sampled world. The experiment named is then one change to a
    flight that exists, in a world the model can be in - never a point off the reachable
    set, which is an errand nobody can run."""
    fa, fb = _compile(draft, "draft"), _compile(hand, "hand")

    def disagree(env: dict) -> tuple[Any, Any] | None:
        try:
            x, y = _normalize(fa({**_LITERALS, **env})), _normalize(fb({**_LITERALS, **env}))
        except Exception:
            return None
        return None if x == y else (x, y)

    for pre, _, _ in rows:
        if reach is not None and not reach.holds(pre):
            continue
        for combo in (itertools.product(*[args[a] for a in args]) if args else [()]):
            binding = dict(zip(args, combo))
            if (d := disagree({**pre, **binding})) is not None:
                return {"pre": pre, "binding": binding, "draft_says": d[0], "hand_says": d[1]}
    if not names:
        return None
    free = sorted(set(_mentions(draft, names)) | set(_mentions(hand, names)))
    best: dict[str, Any] | None = None
    for env in _grid(free, names, reach):
        if (d := disagree(env)) is None:
            continue
        dist = min((sum(1 for n in free if n in pre and pre[n] != env[n]) for pre, _, _ in rows),
                   default=len(free))
        if best is None or dist < best["away"]:
            best = {"pre": {n: env[n] for n in free if n not in args}, "binding":
                    {n: env[n] for n in free if n in args}, "draft_says": d[0],
                    "hand_says": d[1], "away": dist}
    return best


def render(report: dict[str, Any]) -> str:
    t = report["tally"]
    out = [f"{report['tapes']} tape(s), {report['acts']} bound act(s), "
           f"{report['refusals']} refused; measured over "
           f"{report.get('reachable', 0)} reachable state(s), "
           f"{report.get('unreachable_pre', 0)} sampled pre-world(s) the model cannot reach"]
    for a in report["actions"]:
        if not (a["samples"] or a["updates"] or a["guard"]["hand"]):
            continue  # nothing by hand, nothing on the tapes: nothing to compare
        out.append(f"  {a['id']} ({a['samples']} sample(s), {a['refusals']} refused)")
        for var, u in a["updates"].items():
            mark = (" where the act is enabled"
                    if u.get("scope") == "enabled" and u["verdict"] == "equivalent" else "")
            out.append(f"     {var:<18} hand {u['hand']!s:<28} draft {u['draft']!s:<24} "
                       f"{u['verdict']}{mark} ({u['status']})")
        for var, f in a["frames"].items():
            out.append(f"     {var:<18} hand (frame)                     draft {f['draft']!s:<24} "
                       f"{f['verdict']} ({f['status']})")
        g = a["guard"]
        if g["hand"] or g["draft"]:
            out.append(f"     guard              hand {g['hand']!s:<28} draft {g['draft']!s:<24} "
                       f"{g.get('verdict', 'none by hand')} ({g['from']})")
    out.append("")
    out.append(f"updates: {t['updates']} by hand - {t['updates_equivalent']} drafted equivalent "
               f"({t.get('updates_equivalent_enabled', 0)} of them only where the model reaches "
               f"the act enabled), "
               f"{t['updates_different']} different, {t['updates_partial']} partial, "
               f"{t['updates_unresolved']} unresolved, {t['updates_unwitnessed']} unwitnessed")
    out.append(f"frames: {t['frames']} by hand - {t['frames_agreed']} agreed, "
               f"{t['frames_partial']} partial, {t['frames_disputed']} disputed, "
               f"{t['frames_unwitnessed']} unwitnessed")
    out.append(f"guards: {t['guards']} by hand - {t['guards_equivalent']} drafted equivalent "
               f"({t.get('guards_equivalent_reachable', 0)} of them on the reachable set only), "
               f"{t['guards_different']} different, {t['guards_unwitnessed']} unwitnessed; "
               f"{t['unguarded']} unguarded, {t['unguarded_drafted']} of them drafted a guard")
    return "\n".join(out)


def render_proposals(report: dict[str, Any]) -> str:
    """One line per row the draft could not settle: the experiment that would."""
    ps = report["proposals"]
    if not ps:
        return "nothing to propose: every drafted row is equivalent or unwitnessed"
    out = [f"{len(ps)} proposal(s) - the observation that separates draft from hand:"]
    for p in ps:
        target = f"{p['action']}.{p['var']}" if p["var"] else f"{p['action']} guard"
        out.append(f"  {target:<30} hand {p['hand']!s:<24} draft {p['draft']!s:<20} {p['verdict']}")
        out.append(f"     -> {p['experiment']}")
        if p.get("separating"):
            sp = p["separating"]
            away = f" ({sp['away']} variable(s) from a sampled world)" if "away" in sp else ""
            out.append(f"        at pre={sp['pre']} binding={sp['binding']}{away}: "
                       f"draft says {sp['draft_says']!r}, hand says {sp['hand_says']!r}")
    return "\n".join(out)


def _load(spec: str) -> Node:
    mod, attr = spec.split(":")
    return getattr(importlib.import_module(mod), attr)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m epure.draft", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", required=True, help="module:ATTR of the model Node")
    ap.add_argument("--tapes", nargs="+", type=Path, required=True)
    ap.add_argument("--link", default=None, help="the model id the sessions link to")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--propose", action="store_true",
                    help="print, per unsettled row, the experiment that would settle it")
    ns = ap.parse_args(argv)
    model = _load(ns.model)
    tapes = sorted(p for d in ns.tapes for p in (d.glob("*.jsonl") if d.is_dir() else [d]))
    report = measure(model, collect(model, tapes, ns.link or model.id))
    if ns.json:
        print(json.dumps(report, ensure_ascii=False))
    elif ns.propose:
        print(render_proposals(report))
    else:
        print(render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
