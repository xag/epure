"""One table, two readers: the model generates its effect nodes from it, the source is held
to it. The point under test is that the two cannot disagree about one act."""

from __future__ import annotations

import pytest

from epure.testimony import Acts

WRITE = {"event": "hook.write"}
TABLE = {
    "deposit": {
        "args": ["coat"],
        "creates": [{"entity": "held_{coat}", "from": ["coat"],
                     "via": WRITE, "shown_by": "hook.read"}],
        "touches": {"only": ["held_{coat}"], "via": [WRITE]},
    },
    "reclaim": {
        "deletes": {"entity": "held", "via": "hook.delete", "shown_by": "hook.read"},
        "touches": {"only": ["held"], "via": ["hook.delete"]},
    },
    "look": {"touches": {"only": [], "via": []}},
}


def test_an_act_instantiates_per_action_with_its_binding():
    acts = Acts.from_table(TABLE)
    kids = acts.children("deposit", "check-red", coat="red")
    assert [(k.kind, k.id) for k in kids] == [
        ("creates", "check-red-creates-held_red"), ("touches", "check-red-touches")]
    assert kids[0].payload == {"entity": "held_red", "from": ["coat"],
                               "via": WRITE, "shown_by": "hook.read"}
    assert kids[1].payload == {"only": ["held_red"], "via": [WRITE]}


def test_also_names_what_one_action_moves_beyond_the_template():
    kids = Acts.from_table(TABLE).children("deposit", "check-blue", also=["tally"],
                                           coat="blue")
    assert kids[1].payload["only"] == ["held_blue", "tally"]


def test_an_unmodeled_entity_is_dropped_where_the_model_abstracts_it():
    kids = Acts.from_table(TABLE).children("deposit", "check-red", unmodeled=["held_red"],
                                           coat="red")
    assert [k.kind for k in kids] == ["touches"] and kids[0].payload["only"] == []


def test_a_template_over_an_unbound_argument_is_refused():
    with pytest.raises(ValueError, match="binds no \\['coat'\\]"):
        Acts.from_table(TABLE).children("deposit", "check")


def test_a_delete_carries_no_from():
    (deletes, _) = Acts.from_table(TABLE).children("reclaim", "reclaim-coat")
    assert deletes.payload == {"entity": "held", "via": "hook.delete", "shown_by": "hook.read"}


def test_a_malformed_declaration_is_refused_at_the_table():
    with pytest.raises(ValueError, match="names its entity"):
        Acts.from_table({"x": {"mutates": ["held"]}})
    with pytest.raises(ValueError, match="unknown key"):
        Acts.from_table({"x": {"mutate": []}})


def test_the_source_is_held_to_the_table(tmp_path):
    src = tmp_path / "app.py"
    src.write_text(
        'with fr.span("deposit", coat=c):\n'
        '    fr.note("look")\n'
        'with span(\'vanish\'):\n'
        "    pass\n", encoding="utf-8")
    acts = Acts.from_table(TABLE)
    assert acts.undeclared([src]) == [f"{src}:3: vanish"]
    assert acts.emitted([src]) == {"deposit", "look", "vanish"}


def test_emitting_through_the_table_refuses_an_undeclared_or_underbound_act():
    acts = Acts.from_table(TABLE)
    with pytest.raises(KeyError, match="not a declared act"):
        acts.span("vanish")
    with pytest.raises(ValueError, match="lacks \\['coat'\\]"):
        acts.span("deposit")
