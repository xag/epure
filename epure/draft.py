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

What it is for is a number, not a model. Held against a model a person wrote, it says how
much of that model the tapes already determine - equivalent over the whole finite domain,
not merely on the samples - and the remainder is the human's share: the arithmetic no tape
witnessed, the guard no refusal exercised, the saturation bound no run reached. Two
consumers make the number a measurement rather than a fit. A drafted expression is a
hypothesis about the app, exactly as partial as the tapes that made it: a path no tape took
is a case it cannot see, which is why the draft is compared and counted, never installed.

    python -m epure.draft --model chores_model.package:MODEL --tapes tests/flights
    python -m epure.draft --model health_model.package:MODEL --tapes scenarios/flights --json
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
    """Per action: the projected (pre, binding, post) of every bound span act, across tapes."""

    def __init__(self) -> None:
        self.by_action: dict[str, list[tuple[dict, dict, dict]]] = {}
        self.tapes = 0
        self.acts = 0
        # refused acts that bind an action: the worlds where a guard was FALSE - the only
        # evidence a guard can be drafted from, since a guard is what is refused
        self.refusals: dict[str, int] = {}

    def add(self, W: _Worlds) -> None:
        self.tapes += 1
        for w in W.worlds:
            if w.action is None or w.act.is_call:
                continue
            self.acts += 1
            self.by_action.setdefault(w.action["id"], []).append((w.pre, w.binding, w.post))
        for a in W.acts:
            if a.span.payload.get("outcome") == "error" and not a.is_call:
                for bound in W.model.bound(a.span):
                    self.refusals[bound.id] = self.refusals.get(bound.id, 0) + 1


def collect(model: Node, tapes: list[Path], link: str) -> Samples:
    out = Samples()
    for tape in tapes:
        session = import_scenario(tape)
        session.id = tape.stem
        session.links = {"model": [link]}
        tree = Quern()
        tree.root.children = [model.model_copy(deep=True), session]
        out.add(_Worlds(tree, tape.stem, "model"))
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
    'unwitnessed' that no sample shows both worlds; None with 'unresolved' that the grammar
    has no expression for what was seen."""
    rows = [(pre, b, post[var]) for pre, b, post in samples if var in post and var in pre]
    if not rows:
        return None, "unwitnessed"
    if all(post == pre[var] for pre, _, post in rows):
        return None, "frame"
    posts = {json.dumps(post, sort_keys=True) for _, _, post in rows}
    if len(posts) == 1:
        return _lit(rows[0][2]), "constant"
    for a in args:
        if all(a in b and post == b[a] for _, b, post in rows):
            return a, "argument"
    for other in vars:
        if other != var and all(other in pre and post == pre[other] for pre, _, post in rows):
            return other, "variable"
    if all(isinstance(post, (int, float)) and isinstance(pre[var], (int, float))
           and not isinstance(post, bool) for pre, _, post in rows):
        deltas = {post - pre[var] for pre, _, post in rows}
        if len(deltas) == 1:
            k = deltas.pop()
            return (f"{var} + {_lit(k)}" if k >= 0 else f"{var} - {_lit(-k)}"), "increment"
        hi = max(v for v in dom if isinstance(v, (int, float)))
        for k in (1, 2, 3):
            if all(post == min(pre[var] + k, hi) for pre, _, post in rows):
                return f"min({var} + {k}, {hi})", "saturating"
    return None, "unresolved"


def draft_guard(pres: list[dict], variables: dict[str, list[Any]]) -> str:
    """The conjunction the pre-worlds support: every boolean that never varied where it was
    projected. Positives only - a guard is what is REFUSED, and a tape with no refusal of the
    act holds no world where the guard was false; what this drafts is at most necessary,
    never sufficient, and the enum and arithmetic forms are left alone because, from
    positives alone, they only overfit (an assignee never seen is not an assignee
    forbidden)."""
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
                              "refusals": sum(samples.refusals.values()), "actions": []}
    tally = {"updates": 0, "updates_equivalent": 0, "updates_different": 0,
             "updates_unwitnessed": 0, "updates_unresolved": 0,
             "frames": 0, "frames_agreed": 0, "frames_disputed": 0, "frames_unwitnessed": 0,
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
        for var in projected:
            expr, status = draft_update(var, variables[var], rows, list(args), list(variables))
            if var in hand:
                tally["updates"] += 1
                if status == "unwitnessed":
                    verdict = "unwitnessed"
                elif expr is None:
                    verdict = "unresolved" if status == "unresolved" else "different"
                else:
                    verdict = ("equivalent" if equivalent(expr, hand[var], names)
                               else "different")
                tally[f"updates_{verdict}"] += 1
                row["updates"][var] = {"hand": hand[var], "draft": expr, "status": status,
                                       "verdict": verdict}
            else:
                tally["frames"] += 1
                verdict = ("unwitnessed" if status == "unwitnessed"
                           else "agreed" if status == "frame" else "disputed")
                tally[f"frames_{verdict}"] += 1
                if verdict == "disputed":
                    row["frames"][var] = {"draft": expr, "status": status, "verdict": verdict}
        guard = str(c.payload.get("guard") or "")
        drafted = draft_guard([pre for pre, _, _ in rows], variables) if rows else ""
        row["guard"] = {"hand": guard, "draft": drafted}
        if guard:
            tally["guards"] += 1
            if not rows:
                verdict = "unwitnessed"
            else:
                verdict = "equivalent" if equivalent(drafted, guard, names, boolean=True) \
                    else "different"
            tally[f"guards_{verdict}"] += 1
            row["guard"]["verdict"] = verdict
        else:
            tally["unguarded"] += 1
            if drafted:
                tally["unguarded_drafted"] += 1
        report["actions"].append(row)
    report["tally"] = tally
    return report


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
                       f"{g.get('verdict', 'none by hand')}")
    out.append("")
    out.append(f"updates: {t['updates']} by hand - {t['updates_equivalent']} drafted equivalent, "
               f"{t['updates_different']} different, {t['updates_unresolved']} unresolved, "
               f"{t['updates_unwitnessed']} unwitnessed")
    out.append(f"frames: {t['frames']} by hand - {t['frames_agreed']} agreed, "
               f"{t['frames_disputed']} disputed, {t['frames_unwitnessed']} unwitnessed")
    out.append(f"guards: {t['guards']} by hand - {t['guards_equivalent']} drafted equivalent, "
               f"{t['guards_different']} different, {t['guards_unwitnessed']} unwitnessed; "
               f"{t['unguarded']} unguarded, {t['unguarded_drafted']} of them drafted a guard")
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
    ns = ap.parse_args(argv)
    model = _load(ns.model)
    tapes = sorted(p for d in ns.tapes for p in (d.glob("*.jsonl") if d.is_dir() else [d]))
    report = measure(model, collect(model, tapes, ns.link or model.id))
    print(json.dumps(report, ensure_ascii=False) if ns.json else render(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
