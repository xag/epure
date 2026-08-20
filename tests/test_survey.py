"""The survey drafts doors from tapes: generalized, split by who wrote them, never a value."""

from __future__ import annotations

import json

from epure.survey import _general, draft, survey


def test_identifiers_generalize_and_names_stay():
    assert _general("households/7ykgh6Ck9PU/log/l_G1IA9_VJj38") == "households/*/log/*"
    assert _general("done.c_SYF3T78G37A") == "done.*"
    assert _general("rev") == "rev"
    assert _general("index/wake") == "index/wake"


def test_a_tools_own_writes_are_told_from_its_spans(tmp_path):
    lines = [{"ev": "session", "version": 1, "python": "3"},
             {"ev": "call", "seq": 1, "fn": "tick", "kwargs": {}, "ts": "t", "ms": 1,
              "events": [{"k": "fx", "fn": "store.put", "args": [], "res": None,
                          "kwargs": {"path": "index/wake", "data": {"at": 1}}},
                         {"k": "sem", "name": "day-ticked", "phase": "begin", "sid": 1},
                         {"k": "fx", "fn": "store.create", "args": [], "res": True,
                          "kwargs": {"path": "claims/sweep_2026", "data": {}}},
                         {"k": "sem", "name": "day-ticked", "phase": "end", "sid": 1,
                          "outcome": "ok"}]}]
    tape = tmp_path / "t.jsonl"
    tape.write_text("\n".join(json.dumps(l) for l in lines) + "\n", encoding="utf-8")
    found = survey([tape], ["store.put*", "store.create"])
    assert found["tick"]["calls"] == 1
    assert list(found["tick"]["own"]) == [("store.put", (("path", "index/wake"),))]
    assert list(found["tick"]["inside"]["day-ticked"]) == \
        [("store.create", (("path", "claims/*"),))]
    table = draft(found)
    assert table["tick"] == {"touches": {"only": [], "via": [
        {"event": "store.put", "where": {"path": "index/wake"}}]}}
