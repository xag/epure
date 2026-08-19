"""The ledger's own rules, asserted as what they are: green today, and red the moment a
founding decision stops naming what it rejected.

The suite asserts what is TRUE, never what we wish were true. If this repo ever carries a
deliberate debt, this test does not get skipped and it does not get loosened — it states the
red, and `epure.check` carries the signal to CI. A skipped guard guards nothing.
"""

from __future__ import annotations

from quern import reckon, run_rules

from epure.tree import build


def test_the_red_is_exactly_the_declared_red():
    """The repo now carries a deliberate debt — five conduct families cite nobody — so
    per this file's own docstring the test states the red rather than wishing it away:
    every red is one an entry declared on itself, no declaration outlives its red, and
    the set is names, never a count."""
    tree = build()
    news, carried, stale = reckon(tree, run_rules(tree))
    assert not news, "unaccounted red:\n" + "\n".join(
        f"{r.rule} @ {r.node}: {r.detail}" for r in news)
    assert not stale, "expectations that outlived their red:\n" + "\n".join(stale)
    assert {(r.node, r.rule) for r in carried} == {
        (law, "a-law-cites-a-source")
        for law in ("refusal-changes-nothing", "undo-restores", "same-state-same-story",
                    "shown-once-shown-until-touched", "the-effect-is-checkable")}


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
        # conduct@0.1.0: the law shape's own gates, judging the nine families this
        # repo mounts as content.
        "a-law-can-be-violated-observably",
        "a-law-is-switched-on-by-something",
        "a-law-cites-a-source",
        # ...and its requirement staged beneath it: conduct@ names semantic-model@0.4.0
        # (the effect kinds its triggers bind to), and a closure travels whole — these
        # judge any model node this ledger ever mounts, which is the right default.
        "a-model-declares-its-alphabet",
        "an-event-kind-carries-a-license",
        "an-action-is-observable",
    }, ("the effective rules are not the twelve ledger@0.6.0 + three conduct@0.1.0 + "
        "three semantic-model@0.4.0 ship — has one been redefined here?")

    fired = {r.rule for r in run_rules(tree)}
    assert "a-decision-names-what-it-rejected" in fired
    assert "a-hypothesis-is-falsifiable" in fired
