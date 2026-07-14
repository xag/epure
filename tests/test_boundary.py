"""The boundary declaration, and the seam it rests on.

A boundary is a claim about where this program's nondeterminism enters. The claim is only
worth what it is checked against: an effect naming a function that no longer exists is a
declaration that lies, and it lies in the direction that matters — the recorder cannot record
an input it was never told about, so the tape looks clean and the hole is invisible.
"""

from __future__ import annotations

import json

import pytest

from epure.boundary import boundary
from epure.tape import read_tape


def test_every_declared_effect_exists():
    b = boundary()
    assert b.effects, "a boundary that declares nothing declares nothing true"
    for entry in b.effects:
        module, names = entry[0], entry[1]
        for name in names:
            assert getattr(module, name, None) is not None, \
                f"{module!r} declares an effect '{name}' it does not have"


def test_the_tape_seam_is_the_one_declared():
    """`read_tape` is named by the boundary because it is the only door to the disk."""
    b = boundary()
    declared = {name for entry in b.effects for name in entry[1]}
    assert "read_tape" in declared


def test_read_tape_reads_a_tape(tmp_path):
    tape = tmp_path / "flight.jsonl"
    tape.write_text(
        json.dumps({"ev": "session", "version": 1, "python": "3.12.0"}) + "\n"
        + json.dumps({"ev": "call", "seq": 1, "fn": "turn", "events": []}) + "\n",
        encoding="utf-8")
    lines = read_tape(tape)
    assert [ln["ev"] for ln in lines] == ["session", "call"]


def test_read_tape_discards_a_torn_final_line(tmp_path):
    """The one corruption the format permits: the process died mid-write. A reader MUST
    tolerate it (spec/tape-v1.md), and a tape that ends this way is a normal end for a tape —
    a crashed run is precisely the run somebody wants to read."""
    tape = tmp_path / "flight.jsonl"
    tape.write_text(
        json.dumps({"ev": "session", "version": 1, "python": "3.12.0"}) + "\n"
        + json.dumps({"ev": "call", "seq": 1, "fn": "turn", "events": []}) + "\n"
        + '{"ev": "call", "seq": 2, "fn": "tur',
        encoding="utf-8")
    lines = read_tape(tape)
    assert [ln["ev"] for ln in lines] == ["session", "call"]


def test_read_tape_refuses_a_torn_line_in_the_middle(tmp_path):
    """Only the FINAL line may be torn. Corruption anywhere else is not a dead process, it is
    a damaged file, and silently skipping it would hand a checker a tape with a hole in it."""
    tape = tmp_path / "flight.jsonl"
    tape.write_text(
        json.dumps({"ev": "session", "version": 1, "python": "3.12.0"}) + "\n"
        + '{"ev": "call", "seq": 1, "fn": "tur' + "\n"
        + json.dumps({"ev": "call", "seq": 2, "fn": "turn", "events": []}) + "\n",
        encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        read_tape(tape)
