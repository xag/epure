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
from epure.prove import _compile, _domain
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
                       args: list[str], vars: list[str]
                       ) -> tuple[str | None, str, list[tuple[int, str]]]:
    """draft_update, plus the rows (index into `samples`, unread operand) a partial draft
    could not be judged on - empty for a settled verdict."""
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
    # The first candidate no row refutes decides - settled when every row could judge it,
    # partial otherwise. A later candidate every row CAN judge does not outrank it: when no
    # sample shows the value before the act, "the constant 0" and "the frame" are the same
    # evidence, and the simpler claim stands, marked for what it still needs.
    for status, expr, needs, fits in candidates:
        ok, missing = judged(needs, fits)
        if not ok:
            continue
        if not missing:
            return expr, status, []
        return expr, "partial", missing
    return None, "unresolved", []


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
    evaluator answers None where the world does not show the name."""
    out: list[tuple[str, Callable[[dict], bool | None]]] = []
    for n, dom in names.items():
        if all(isinstance(d, bool) for d in dom):
            out.append((n, lambda w, n=n: w.get(n) if n in w else None))
            out.append((f"not {n}", lambda w, n=n: (not w[n]) if n in w else None))
            continue
        numeric = all(isinstance(d, (int, float)) for d in dom)
        for c in dom:
            out.append((f"{n} == {_lit(c)}", lambda w, n=n, c=c: (w[n] == c) if n in w else None))
            out.append((f"{n} != {_lit(c)}", lambda w, n=n, c=c: (w[n] != c) if n in w else None))
            if numeric:
                out.append((f"{n} < {_lit(c)}", lambda w, n=n, c=c: (w[n] < c) if n in w else None))
                out.append((f"{n} >= {_lit(c)}", lambda w, n=n, c=c: (w[n] >= c) if n in w else None))
    return out


def _guard_from_negatives(taken: list[dict], denied: list[dict], names: dict[str, list[Any]]
                          ) -> str:
    """The simplest predicate true on every taken world and false on every denied one; ''
    when none of the grammar separates them. A world that does not show a name the
    predicate reads neither confirms nor refutes it - but a predicate must be decided on at
    least one world of each side to count as separating anything."""
    atoms = _atoms(names)

    def separates(fs: list[Callable[[dict], bool | None]]) -> bool:
        def val(w: dict) -> bool | None:
            vs = [f(w) for f in fs]
            if any(v is None for v in vs):
                return None
            return all(vs)
        t = [val(w) for w in taken]
        d = [val(w) for w in denied]
        if any(v is False for v in t) or any(v is True for v in d):
            return False
        return any(v is True for v in t) and any(v is False for v in d)

    for src, f in atoms:
        if separates([f]):
            return src
    for (s1, f1), (s2, f2) in itertools.combinations(atoms, 2):
        if separates([f1, f2]):
            return f"{s1} and {s2}"
    return ""


# --- equivalence over the finite domain -----------------------------------------------------


_IDENT = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def _mentions(src: str, names: dict[str, list[Any]]) -> list[str]:
    return sorted({t for t in _IDENT.findall(src.replace("'", " ")) if t in names})


def equivalent(a: str, b: str, names: dict[str, list[Any]], *, boolean: bool = False) -> bool:
    """Two expressions agree at every point of the grid over the variables and arguments
    either mentions - the whole finite domain, sampled past GRID_CAP."""
    fa, fb = _compile(a or "true", "draft"), _compile(b or "true", "hand")
    free = sorted(set(_mentions(a, names)) | set(_mentions(b, names)))
    doms = [names[n] for n in free]
    total = 1
    for d in doms:
        total *= len(d)
    if total <= GRID_CAP:
        points = itertools.product(*doms)
    else:
        rng = random.Random(0)
        points = ([rng.choice(d) for d in doms] for _ in range(GRID_CAP))
    for pt in points:
        env = {**_LITERALS, **dict(zip(free, pt))}
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


# --- the measurement --------------------------------------------------------------------------


def measure(model: Node, samples: Samples) -> dict[str, Any]:
    variables = {c.id: _domain(c.payload, f"state-var '{c.id}'")
                 for c in model.children if c.kind == "state-var"}
    projected = {c.id for c in model.children
                 if c.kind == "state-var" and c.payload.get("shown")}
    report: dict[str, Any] = {"tapes": samples.tapes, "acts": samples.acts,
                              "refusals": sum(samples.refusals.values()), "actions": [],
                              "proposals": []}
    tally = {"updates": 0, "updates_equivalent": 0, "updates_different": 0,
             "updates_unwitnessed": 0, "updates_unresolved": 0, "updates_partial": 0,
             "frames": 0, "frames_agreed": 0, "frames_disputed": 0, "frames_unwitnessed": 0,
             "frames_partial": 0,
             "guards": 0, "guards_equivalent": 0, "guards_different": 0,
             "guards_unwitnessed": 0, "unguarded": 0, "unguarded_drafted": 0}
    for c in model.children:
        if c.kind != "action":
            continue
        args = {n: _domain(spec, f"arg '{n}'") for n, spec in (c.payload.get("args") or {}).items()}
        names = {**variables, **args}
        hand = {u["var"]: str(u["expr"]) for u in c.payload.get("updates") or []}
        rows = samples.by_action.get(c.id, [])
        row: dict[str, Any] = {"id": c.id, "samples": len(rows),
                               "refusals": samples.refusals.get(c.id, 0),
                               "updates": {}, "frames": {}}
        where = samples.where.get(c.id, [])
        empty = samples.empty.get(c.id, [])
        for var in projected:
            expr, status, unsettled = draft_update_where(var, variables[var], rows, list(args),
                                                         list(variables))
            if var in hand:
                tally["updates"] += 1
                if status in ("unwitnessed", "partial"):
                    verdict = status
                elif expr is None:
                    verdict = "unresolved" if status == "unresolved" else "different"
                else:
                    verdict = ("equivalent" if equivalent(expr, hand[var], names)
                               else "different")
                tally[f"updates_{verdict}"] += 1
                entry = {"hand": hand[var], "draft": expr, "status": status, "verdict": verdict}
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
                                                        entry.get("unsettled"), rows, args))
            else:
                tally["frames"] += 1
                verdict = ("unwitnessed" if status == "unwitnessed"
                           else "agreed" if status == "frame"
                           else "partial" if status == "partial" and expr is None
                           else "disputed")
                tally[f"frames_{verdict}"] += 1
                if verdict == "disputed":
                    row["frames"][var] = {"draft": expr, "status": status, "verdict": verdict}
        guard = str(c.payload.get("guard") or "")
        refused = samples.refused.get(c.id, [])
        drafted = draft_guard([pre for pre, _, _ in rows], variables,
                              refused=[pre for pre, _ in refused], args=args,
                              bindings=[b for _, b, _ in rows],
                              refused_bindings=[b for _, b in refused]) if rows else ""
        row["guard"] = {"hand": guard, "draft": drafted,
                        "from": "refusals" if refused else "positives only"}
        if guard:
            tally["guards"] += 1
            if not rows:
                verdict = "unwitnessed"
            else:
                verdict = "equivalent" if equivalent(drafted, guard, names, boolean=True) \
                    else "different"
            tally[f"guards_{verdict}"] += 1
            row["guard"]["verdict"] = verdict
            if verdict == "different" and not refused:
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
             args: dict[str, list[Any]]) -> dict[str, Any]:
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
        out["separating"] = _separating_point(draft, hand, rows, args)
    elif verdict == "different":
        out["experiment"] = (f"the tapes say frame; take {action} in a world where `{hand}` "
                             "moves the variable")
    else:
        out["experiment"] = (f"no expression of the grammar fits the {len(rows)} sample(s); "
                             "a richer grammar, or a read around each act")
    return out


def _separating_point(draft: str, hand: str, rows: list[tuple[dict, dict, dict]],
                      args: dict[str, list[Any]]) -> dict[str, Any] | None:
    """A point near the sampled worlds where the two expressions disagree: each pre-world
    the tapes held, with the arguments swept over their domains - so the experiment named
    is one act away from a flight that exists."""
    fa, fb = _compile(draft, "draft"), _compile(hand, "hand")
    for pre, _, _ in rows:
        for combo in (itertools.product(*[args[a] for a in args]) if args else [()]):
            binding = dict(zip(args, combo))
            env = {**_LITERALS, **pre, **binding}
            try:
                x, y = _normalize(fa(env)), _normalize(fb(env))
            except Exception:
                continue
            if x != y:
                return {"pre": pre, "binding": binding, "draft_says": x, "hand_says": y}
    return None


def render(report: dict[str, Any]) -> str:
    t = report["tally"]
    out = [f"{report['tapes']} tape(s), {report['acts']} bound act(s), "
           f"{report['refusals']} refused"]
    for a in report["actions"]:
        if not (a["samples"] or a["updates"] or a["guard"]["hand"]):
            continue  # nothing by hand, nothing on the tapes: nothing to compare
        out.append(f"  {a['id']} ({a['samples']} sample(s), {a['refusals']} refused)")
        for var, u in a["updates"].items():
            out.append(f"     {var:<18} hand {u['hand']!s:<28} draft {u['draft']!s:<24} "
                       f"{u['verdict']} ({u['status']})")
        for var, f in a["frames"].items():
            out.append(f"     {var:<18} hand (frame)                     draft {f['draft']!s:<24} "
                       f"{f['verdict']} ({f['status']})")
        g = a["guard"]
        if g["hand"] or g["draft"]:
            out.append(f"     guard              hand {g['hand']!s:<28} draft {g['draft']!s:<24} "
                       f"{g.get('verdict', 'none by hand')} ({g['from']})")
    out.append("")
    out.append(f"updates: {t['updates']} by hand - {t['updates_equivalent']} drafted equivalent, "
               f"{t['updates_different']} different, {t['updates_partial']} partial, "
               f"{t['updates_unresolved']} unresolved, {t['updates_unwitnessed']} unwitnessed")
    out.append(f"frames: {t['frames']} by hand - {t['frames_agreed']} agreed, "
               f"{t['frames_partial']} partial, {t['frames_disputed']} disputed, "
               f"{t['frames_unwitnessed']} unwitnessed")
    out.append(f"guards: {t['guards']} by hand - {t['guards_equivalent']} drafted equivalent, "
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
            out.append(f"        at pre={sp['pre']} binding={sp['binding']}: "
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
