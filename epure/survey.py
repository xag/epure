"""The survey: what each tool writes, read off its tapes, drafted as doors.

Declaring a boundary for ninety tools by hand is the cost that makes "instrument the whole
thing" a project instead of an afternoon. The tapes already hold the answer: every call
record names its tool, and every write it made is a raw event with a function and its
arguments. This reads them all and drafts, per tool, the doors it was seen to pass through —
generalized (an id becomes `*`, a keyed field becomes `prefix.*`) so the draft is a pattern
and not a replay — and says which writes happened OUTSIDE every domain span, which is what
the call-level boundary must admit.

A draft is a hypothesis about the app's I/O, drawn from the tapes that happen to exist, and
it is wrong in exactly the way a tape is partial: a door a tool passes through only on a path
no tape recorded is absent. That is why the output is a draft table to be read and checked,
and why the frame law stays on: the first tape that takes the unrecorded path convicts the
draft, and the declaration is corrected where it lives.

    python -m epure.survey tests/flights tests/recordings --writes 'app.storage.put*' \\
        --writes 'app.storage.create' --writes 'app.storage.del*'
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Iterable

from .tape import import_scenario

_ID = re.compile(r"[0-9]|_|^[A-Za-z]{12,}$")


def _general(value: Any) -> str:
    """A path or key with its identifiers replaced by `*`: `households/7yk/log/l_G1IA` becomes
    `households/*/log/*`; `done.c_SYF3` becomes `done.*`; `rev` stays `rev`."""
    if not isinstance(value, str):
        return "*"
    if "/" in value:
        parts = value.split("/")
        return "/".join("*" if _ID.search(p) or len(p) > 10 else p for p in parts)
    if "." in value:
        head, _ = value.split(".", 1)
        return f"{head}.*"
    return "*" if _ID.search(value) and len(value) > 6 else value


def _shape(event: dict[str, Any]) -> tuple[str, tuple[tuple[str, str], ...]]:
    """A write's door shape: its function and the generalized scalar arguments that tell one
    write from another (paths, fields, keys) — never the values it carried."""
    kwargs = event.get("kwargs") or {}
    where = tuple(sorted((k, _general(v)) for k, v in kwargs.items()
                         if isinstance(v, str) and k in ("path", "field", "key", "collection",
                                                         "doc", "table", "name")))
    if not where:
        args = [a for a in event.get("args") or [] if isinstance(a, str)]
        if args:
            where = (("0", _general(args[0])),)
    return str(event.get("fn") or event.get("op") or event.get("k")), where


def survey(tapes: Iterable[Path], writes: list[str]) -> dict[str, dict[str, Any]]:
    """Per tool: the write doors seen, split into those OUTSIDE every span (the call's own)
    and those inside a span (that span's), each with a count; the spans the tool encloses;
    and how many calls were read."""
    out: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "calls": 0, "own": Counter(), "inside": defaultdict(Counter), "spans": Counter()})

    def is_write(e: dict[str, Any]) -> bool:
        name = str(e.get("fn") or e.get("op") or "")
        return any(fnmatch(name, w) for w in writes)

    def under(node, sink: Counter) -> None:
        for e in node.payload.get("events") or []:
            if is_write(e):
                sink[_shape(e)] += 1
        for c in node.children:
            under(c, sink)

    for tape in tapes:
        session = import_scenario(tape)
        for call in session.children:
            tool = out[call.name]
            tool["calls"] += 1
            for e in call.payload.get("events") or []:
                if is_write(e):
                    tool["own"][_shape(e)] += 1
            for span in call.children:
                tool["spans"][span.kind] += 1
                under(span, tool["inside"][span.kind])
    return out


def _door(shape: tuple[str, tuple[tuple[str, str], ...]]) -> dict[str, Any]:
    fn, where = shape
    return {"event": fn, "where": dict(where)} if where else {"event": fn}


def draft(found: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The table entries the survey supports: per tool, `touches.via` = the doors its own
    (unenclosed) writes passed through, `only: []` (the survey sees writes, not the model's
    variables — naming those is the author's). A tool seen writing nothing of its own gets
    `via: []`, which is the frame at its sharpest and the draft most worth checking."""
    table: dict[str, dict[str, Any]] = {}
    for tool in sorted(found):
        doors = [_door(shape) for shape, _ in sorted(found[tool]["own"].items(),
                                                     key=lambda kv: -kv[1])]
        table[tool] = {"touches": {"only": [], "via": doors}}
    return table


def render(found: dict[str, dict[str, Any]], table: dict[str, dict[str, Any]]) -> str:
    lines = ["# Drafted by `python -m epure.survey` from the tapes on hand. A door absent here",
             "# is a path no tape took; the frame law convicts the first tape that takes it.",
             "CALLS: dict[str, dict] = {"]
    for tool, entry in table.items():
        f = found[tool]
        inside = ", ".join(f"{k}:{v}" for k, v in sorted(f["spans"].items())) or "none"
        lines.append(f"    # {f['calls']} call(s); spans inside: {inside}")
        lines.append(f"    {tool!r}: {json.dumps(entry, ensure_ascii=False)},")
    lines.append("}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m epure.survey",
                                 description=__doc__.splitlines()[0])
    ap.add_argument("directories", nargs="+", type=Path)
    ap.add_argument("--writes", action="append", required=True,
                    help="fnmatch pattern of a write function (repeatable)")
    ns = ap.parse_args(argv)
    tapes = [t for d in ns.directories for t in sorted(d.glob("*.jsonl"))]
    found = survey(tapes, ns.writes)
    print(render(found, draft(found)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
