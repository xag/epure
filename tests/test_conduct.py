"""The conduct catalogue holds its shape, and its debts are accounted, not hidden.

Same two failures as test_package.py, plus the one this catalogue adds: an uncited law is
red BY DESIGN under a-law-cites-a-source, and the guard here is that every such red is
declared on the node that carries it — reckon() must sort the ledger into exactly {the five
unsourced families} carried, nothing new, nothing stale. A sixth uncited law arriving
without its accounting breaks this test, and so does sourcing a family without withdrawing
the note that excused it.
"""

from __future__ import annotations

import os
from pathlib import Path

from quern import reckon, run_rules
from quern.library import Library, package_digest, read_lock, validate_package

from epure.conduct import CONDUCT_LAWS, CONDUCT_PACKAGE

_ROOT = Path(__file__).resolve().parents[1]

UNSOURCED = {"shown-once-shown-until-touched", "the-effect-is-checkable"}

# The laws no native holds yet — each owed to a debt the ledger carries.
OWED = {"what-is-promised-eventually-happens"}   # liveness: the third source's one owed item


def test_the_pin_is_this_content():
    refs = {r.name: r for r in read_lock(_ROOT / "quern.lock")}
    assert "conduct" in refs, "conduct is not pinned in quern.lock"
    assert refs["conduct"].sha256 == package_digest(CONDUCT_PACKAGE), (
        "the authored package and the pinned digest disagree — epure/conduct.py has "
        "drifted from what was published. Versions are immutable: bump the version and "
        "republish; never edit a published meaning in place")


def test_the_package_still_demonstrates_itself(tmp_path):
    # The closure (grounding@, semantic-model@) comes from the registry when a sibling
    # checkout exists, and from the repo's own committed cache otherwise — CI has no
    # registry, by decision (see test.yml). semantic-model's native contracts must be
    # in-process for its own re-validation beneath this one.
    import epure.behavior  # noqa: F401
    import epure.conformance  # noqa: F401
    import epure.prove  # noqa: F401
    registry = Path(os.environ.get("QUERN_REGISTRY", _ROOT.parent / "quern-registry"))
    source = Library(registry if registry.exists() else _ROOT / ".quern" / "library")
    log = validate_package(CONDUCT_PACKAGE, tmp_path, source)
    assert any("4 rule(s) exercised" in line for line in log), log
    assert any("refuted by their counter-example" in line for line in log), log
    held = [line for line in log if line.startswith("contract 'conduct/")]
    assert len(held) == 17, log


def test_every_law_is_checked_or_owed_and_the_owed_are_these():
    """A law names the native that holds it or says why none does — never both, never
    neither — and the natives named are contracts the package declares."""
    declared = {s.name for s in CONDUCT_PACKAGE.solvers}
    for law in CONDUCT_LAWS:
        native, owed = law.payload.get("native"), law.payload.get("owed")
        assert bool(native) != bool(owed), law.id
        for n in (native.split(", ") if native else []):
            assert n in declared | {"model/prove"}, f"{law.id} names {n}, which is not declared"
    assert {law.id for law in CONDUCT_LAWS if law.payload.get("owed")} == OWED
    # ...and every declared contract is some law's: a native no law names is a check with
    # no claim behind it
    assert {n for law in CONDUCT_LAWS for n in (law.payload.get("native") or "").split(", ")
            if n} == declared | {"model/prove"}


def test_every_rule_carries_a_counter_example():
    named = {r.name for r in CONDUCT_PACKAGE.rules}
    refuting = {ce.rule for ce in CONDUCT_PACKAGE.counter_examples}
    assert named == refuting, f"rules without a refutation: {sorted(named - refuting)}"


def test_the_catalogue_is_twenty_one_laws_and_the_census_says_how_many_it_holds():
    """Not a census count — the census is tests/test_census.py. This is the catalogue's own
    length, kept here so a law added or dropped is a diff somebody reads."""
    assert len(CONDUCT_LAWS) == 21
    assert len({law.id for law in CONDUCT_LAWS}) == 21


def test_every_citation_carries_its_quote():
    """A citation without the words is a citation nobody can check — the package's own
    KindDef says so, and the authored content is held to it here, since the repo's laws
    do not pass through the publish gate."""
    for law in CONDUCT_LAWS:
        for child in law.children:
            if child.kind == "citation":
                assert child.payload.get("url"), f"{law.id}: citation without a url"
                assert child.payload.get("quote"), f"{law.id}: citation without the quote"


def test_the_unsourced_families_are_accounted_and_only_they_are():
    """authority.grounded, the citation children, and the expected:-note must agree on
    every law — three statements of the same fact, kept from drifting apart."""
    for law in CONDUCT_LAWS:
        cited = any(c.kind == "citation" for c in law.children)
        accounted = "expected:a-law-cites-a-source" in law.meta
        assert law.params["authority"].grounded == cited, (
            f"{law.id}: authority provenance disagrees with the citations it claims")
        assert accounted == (not cited), (
            f"{law.id}: an uncited law carries its accounting; a cited one carries none")
    assert {law.id for law in CONDUCT_LAWS
            if not law.params["authority"].grounded} == UNSOURCED


def test_the_ledger_carries_exactly_the_declared_red():
    """The whole-tree statement: reckon over the built ledger finds no news, no stale
    expectations, and the carried set is exactly the five unsourced families."""
    from epure.tree import build

    tree = build()
    news, carried, stale = reckon(tree, run_rules(tree))
    assert not news, [f"{r.rule} @ {r.node}" for r in news]
    assert not stale, stale
    assert {r.node for r in carried} == UNSOURCED
