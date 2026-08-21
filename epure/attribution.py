"""The attribution counter: reds met against reds a tool named right, from the claims.

The hypothesis `a-red-is-attributed-by-a-rule-not-a-reader` (the ledger) bets that a red
from the conduct natives can be attributed - model, app, or harness - by a rule over facts
the native already holds. The bet is measured, not trusted, and this is the measure: every
red a session met is a `diagnosis` claim in the repo's `claims.jsonl` carrying a `red`
record, and the counter reads those records and nothing else.

    {"kind": "diagnosis", "text": "the hoover done Sunday still due",
     "red": {"check": "conduct/agrees", "culprit": "harness", "tool_named": "harness"},
     "session": "..."}

  culprit     who was wrong, as established - the thing that was changed to make it green
  tool_named  who the tool wrote on the violation, or null when no tool wrote one; a tool
              that said `unnamed` is counted as having named nothing

    python -m epure.attribution claims.jsonl [more.jsonl ...] [--session ID]

prints one line - `reds met N, tool named M, named right R` - and exits 0. The ratio the
falsification watches is R/N per session; a session with no reds prints 0 0 0 and proves
nothing either way.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Attribution:
    met: int
    named: int
    right: int
    by_check: dict[str, tuple[int, int, int]]

    def line(self) -> str:
        out = f"reds met {self.met}, tool named {self.named}, named right {self.right}"
        if self.by_check:
            parts = [f"{c}: {m}/{n}/{r}" for c, (m, n, r) in sorted(self.by_check.items())]
            out += " (" + ", ".join(parts) + ")"
        return out


def _reds(claims: list[dict], session: str | None) -> list[dict]:
    out = []
    for c in claims:
        if c.get("kind") != "diagnosis" or not isinstance(c.get("red"), dict):
            continue
        if session is not None and c.get("session") != session:
            continue
        out.append(c["red"])
    return out


def count(claims: list[dict], session: str | None = None) -> Attribution:
    met = named = right = 0
    by_check: dict[str, list[int]] = {}
    for red in _reds(claims, session):
        culprit = red.get("culprit")
        tool = red.get("tool_named")
        if tool in (None, "", "unnamed"):
            tool = None
        check = str(red.get("check") or "?")
        row = by_check.setdefault(check, [0, 0, 0])
        met += 1
        row[0] += 1
        if tool is not None:
            named += 1
            row[1] += 1
            if tool == culprit:
                right += 1
                row[2] += 1
    return Attribution(met, named, right, {k: tuple(v) for k, v in by_check.items()})


def read(paths: list[Path]) -> list[dict]:
    claims: list[dict] = []
    for p in paths:
        with p.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    claims.append(json.loads(line))
    return claims


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m epure.attribution", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("claims", nargs="+", type=Path)
    ap.add_argument("--session", default=None, help="count one session's reds only")
    ns = ap.parse_args(argv)
    print(count(read(ns.claims), ns.session).line())
    return 0


if __name__ == "__main__":
    sys.exit(main())
