"""The ledger's own rules, asserted as what they are: green today, and red the moment a
founding decision stops naming what it rejected.

The suite asserts what is TRUE, never what we wish were true. If this repo ever carries a
deliberate debt, this test does not get skipped and it does not get loosened — it states the
red, and `epure.check` carries the signal to CI. A skipped guard guards nothing.
"""

from __future__ import annotations

from quern import run_rules

from epure.tree import build


def test_the_ledger_is_green():
    results = run_rules(build())
    red = [f"{r.rule} @ {r.node}: {r.detail}" for r in results if not r.ok]
    assert not red, "the ledger is red:\n" + "\n".join(red)


def test_the_founding_record_is_actually_there():
    """A green ledger with nothing in it is green for the wrong reason."""
    tree = build()
    kinds = [c.kind for c in tree.root.children]
    assert kinds.count("decision") >= 3
    assert kinds.count("hypothesis") >= 1


def test_the_rules_are_the_pinned_packages_own():
    """The rules that judge this ledger are `ledger@0.5.0`'s — not re-authored ones.

    A project that quietly redefines `a-decision-names-what-it-rejected` to mean something
    laxer has a green check and no guard at all, and the check reads exactly the same. The
    tree's own vocabulary always wins over a package's (that is quern's precedence rule, and it
    is the right rule), which is precisely why "we did not use it here" is worth pinning.

    The list is exact, so a version bump lands here deliberately: reading the new rules and
    saying they are the ones now judging this ledger is the point of the guard, and a set
    loosened to `>=` would let a rule vanish silently — the one thing it exists to catch.
    """
    tree = build()
    assert {r.name for r in tree.rules} == {
        "a-decision-names-what-it-rejected",
        "a-hypothesis-is-falsifiable",
        "a-debt-states-how-it-is-discharged",
        "nothing-unsound-passes-a-gate",
        # 0.2.0: an entry goes red when the grounds it declared are withdrawn.
        "what-a-decision-rests-on-still-stands",
        "what-a-hypothesis-rests-on-still-stands",
        "what-a-debt-rests-on-still-stands",
        # 0.2.0/0.4.0: removal is a recorded act, and a finished argument has an exit.
        "a-retraction-names-what-it-buried",
        "a-compaction-names-what-it-buried",
        # 0.4.0: an entry is priced at what a reader pays for it.
        "a-decision-fits-its-reader",
        "a-hypothesis-fits-its-reader",
        "a-debt-fits-its-reader",
    }, "the effective rules are not the twelve ledger@0.5.0 ships — has one been redefined here?"

    fired = {r.rule for r in run_rules(tree)}
    assert "a-decision-names-what-it-rejected" in fired
    assert "a-hypothesis-is-falsifiable" in fired
