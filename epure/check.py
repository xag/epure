"""Run the ledger's own rules. `uv run python -m epure.check`

Exit 1 when something is UNACCOUNTED FOR — a red no node expects, or an expectation whose
red has gone. Not on red as such: this ledger ships red on purpose since the conduct
catalogue landed (five of its nine families cite nobody, which is their honest state), and
a gate that fails on every run it will ever have tells nobody anything when it fails. A
decision that names no rejected alternative, a belief with nothing that could kill it, an
uncited law with no accounting: each is red here, and none can be made green by editing
this file. Green comes from doing the work the red node names — or, when a red is meant,
from the node saying so itself: `meta['expected:<rule>'] = '<why>'`, refused as stale the
day the rule goes green.
"""

from __future__ import annotations

import sys

from quern import expectations, get_node, reckon, run_rules

from .tree import build


def main() -> int:
    tree = build()
    results = run_rules(tree)
    # `news` is red nobody accounted for; `carried` is red a node declares it expects, by
    # rule name, in its own meta; `stale` is an expectation whose red has gone, which must
    # be withdrawn rather than left as a standing licence.
    news, carried, stale = reckon(tree, results)

    # ASCII only: this prints to a Windows console under cp1252, which mangles anything
    # prettier and turns a clear report into mojibake exactly when it matters.
    expected_at = {(r.node, r.rule) for r in carried}
    for r in sorted(results, key=lambda r: (r.ok, r.rule, r.node)):
        mark = ("ok  " if r.ok else
                "red*" if (r.node, r.rule) in expected_at else "RED ")
        at = f" @ {r.node}" if r.node else ""
        detail = f" - {r.detail}" if r.detail else ""
        print(f"{mark}{r.rule}{at}{detail}")

    print()
    # Carried reds are reported on a PASSING run too. They are the ledger's standing
    # debts, and a gate that goes quiet about them the moment they are accounted for
    # would trade one silence for another.
    if carried:
        print(f"{len(carried)} red carried on purpose, of {len(results)} rule(s):")
        for r in carried:
            node = get_node(tree, r.node) if r.node else None
            why = (expectations(node).get(r.rule) if node else "") or ""
            print(f"  red* {r.node or r.rule}: {why}")
        print()

    if not news and not stale:
        print(f"{len(results)} rule(s), nothing unaccounted for.")
        return 0

    if news:
        print(f"{len(news)} of {len(results)} rule(s) RED and unaccounted for.")
    if stale:
        print(f"{len(stale)} expectation(s) outlived the red they excused.")
    print()
    for r in news:
        node = get_node(tree, r.node) if r.node else None
        why = (node.payload.get("note") if node else None) or r.detail or ""
        print(f"  {r.node or r.rule}: {why}")
    for line in stale:
        print(f"  {line}")
    print()
    print("Discharge a red node by doing the work it names - never by editing the ledger.")
    print("If a red is intended, say so where it is red: the node's")
    print("meta['expected:<rule>'] = '<why>'. It is refused once that rule goes green.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
