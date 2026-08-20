"""The census is the sources', not the catalogue's: every item maps to a law that exists,
carries one status, and every owed item points at a debt the ledger actually carries."""

from __future__ import annotations

from collections import Counter

from quern import get_node

from epure.census import HUGHES, ITEMS, LAMPORT, RFC, STATUSES, census, laws_named
from epure.conduct import CONDUCT_LAWS


def test_every_item_names_a_law_that_exists_or_is_set_aside():
    laws = {law.id for law in CONDUCT_LAWS}
    for it in ITEMS:
        if it["status"] == "aside":
            assert not it["law"], it["id"]
        else:
            assert it["law"] in laws, f"{it['id']} names '{it['law']}', which is no law"


def test_every_item_has_exactly_one_status_and_a_reason():
    for it in ITEMS:
        assert it["status"] in STATUSES, it["id"]
        assert it["because"].strip(), f"{it['id']}: a status without a reason is a filter"
    ids = [it["id"] for it in ITEMS]
    assert len(ids) == len(set(ids))


def test_the_counts_on_the_node_are_computed_over_the_items():
    node = census()
    counts = Counter(it["status"] for it in ITEMS)
    assert node.params["items"].value == len(ITEMS) == len(node.children)
    for s in STATUSES:
        assert node.params[s].value == counts[s], s
        assert node.params[s].grounded and node.params[s].provenance == "computed"
    # the honest size, stated once here so a change is a diff somebody reads
    assert (counts["covered"], counts["weakened"], counts["owed"], counts["aside"]) == \
        (64, 1, 1, 8)
    assert Counter(it["source"] for it in ITEMS) == {HUGHES: 57, RFC: 14, LAMPORT: 3}


def test_every_owed_item_points_at_a_debt_the_ledger_carries():
    """The harness: an `owed` whose debt is a sentence is a remainder in prose."""
    from epure.tree import build

    tree = build()
    for it in ITEMS:
        if it["status"] != "owed":
            continue
        debt = get_node(tree, it["because"])
        assert debt is not None and debt.kind == "debt", \
            f"{it['id']} is owed to '{it['because']}', which is no debt in the ledger"


def test_every_law_the_census_names_carries_its_coverage():
    """A law's `covers` is computed from the census; a law the census never names covers
    nothing and says so — the gate that keeps a law from claiming a source it lacks."""
    named = laws_named()
    for law in CONDUCT_LAWS:
        covers = law.payload["covers"]
        assert set(covers) == set(STATUSES)
        if law.id in named:
            assert sum(covers.values()) >= 1, law.id
        else:
            assert sum(covers.values()) == 0, law.id


def test_an_owed_law_owes_every_item_it_covers_and_a_native_law_holds_some():
    """A law with a native has at least one covered or weakened item; a law with none has
    only owed items. The payload and the census cannot say two things."""
    for law in CONDUCT_LAWS:
        covers = law.payload["covers"]
        if sum(covers.values()) == 0:
            continue
        if law.payload.get("native"):
            assert covers["covered"] + covers["weakened"] >= 1, law.id
        else:
            assert covers["covered"] == covers["weakened"] == 0, law.id
