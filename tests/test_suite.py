"""The conformance driver, exercised by an app that is not chores.

`epure.suite` is chores' `tools/conformance.py` with its five app-shaped constants lifted into
a `Suite` (xag/epure#15). The point of extracting it was that a second adopter should not copy
346 lines of machinery — so these tests drive it from the turnstile model in `epure.package`,
which is exactly such an adopter: a model the harness has never seen, tapes built inline, and a
receipt written into a tmp repo root.

What they pin is the harness's own decisions, not the three checks (those are
test_conformance.py's job): what a class is held to, when silence is a failure, what a missing
budget means, and what makes a receipt worth committing.

ONE THING THE TURNSTILE CANNOT DO, and it is worth knowing before adopting: none of its
event-kinds carries an `args` map, so `bound_kinds` is empty and every tape judged against it
is VACUOUS. Held to a gated class it would be red forever, however lawful the ride. That is the
model being honest — acts that bind nothing cannot be convicted by refinement — but it means
the estate's only public worked example exercises the ungated path alone. The gated rules are
therefore pinned against `Verdict.red()` directly, which is where they live, rather than
through a model that cannot reach them.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from epure.package import EXAMPLES
from epure.suite import Suite, TapeClass, Verdict, judge, main, write_receipt

MODEL = EXAMPLES[0]          # the turnstile: coin, push


def _sem(name: str, phase: str, sid: int, **kw) -> dict:
    return {"k": "sem", "name": name, "phase": phase, "sid": sid, **kw}


_RIDE = [_sem("coin", "begin", 1),
         {"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {}, "res": 1},
         _sem("coin", "end", 1, outcome="ok"),
         _sem("push", "begin", 2),
         {"k": "fx", "fn": "sensor.read", "args": [], "kwargs": {}, "res": 1},
         _sem("push", "end", 2, outcome="ok")]

_SILENT = [{"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {}, "res": 1}]


def _tape(directory: Path, stem: str, *calls: list) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{stem}.jsonl"
    lines = [{"ev": "session", "version": 1, "python": "3"}]
    lines += [{"ev": "call", "seq": i + 1, "fn": "ride", "events": events, "ts": "t", "ms": 1}
              for i, events in enumerate(calls)]
    path.write_text("\n".join(json.dumps(ln) for ln in lines) + "\n", encoding="utf-8")
    return path


def _suite(root: Path, *, gated: bool = False, budget: dict | None = None,
           receipt: bool = False) -> Suite:
    (root / "quern.lock").write_text(
        json.dumps({"packages": [{"name": "turnstile", "version": "1.0.0"}]}), encoding="utf-8")
    return Suite(
        model=MODEL, model_name="turnstile", root=root,
        classes={"ride": TapeClass(directory=root / "rides", refines_gated=gated)},
        budget={} if budget is None else budget,
        receipt=(root / "receipt.json") if receipt else None)


def _verdict(tmp_path, *, bound: int, total: int = 0, budget: dict | None = None) -> Verdict:
    """A judged tape's answers, without a model. The gate is a function of the class and the
    three numbers, and the rules below are about the gate."""
    v = Verdict(tmp_path / "rides" / "t.jsonl", "ride",
                _suite(tmp_path, gated=True, budget=budget))
    v.bound, v.acts = bound, max(bound, 1)
    v.checks = {"licensed": (0, ""), "total": (total, ""), "refines": (0, "")}
    return v


def test_a_lawful_ride_is_green_for_an_app_the_harness_has_never_seen(tmp_path):
    """The extraction's whole claim: the machinery is not chores-shaped."""
    v = judge(_suite(tmp_path), _tape(tmp_path / "rides", "lawful", _RIDE), "ride")
    assert v.red() == []
    assert v.checks["licensed"][0] == 0
    assert v.checks["refines"][0] == 0
    assert v.checks["total"][0] == 0


def test_silence_refines_which_is_why_vacuity_is_a_failure(tmp_path):
    """The subtlest rule in the harness. A tape that claims nothing REFINES PERFECTLY, because
    refinement has nothing to refuse — so a report counting greens would call the emptiest tape
    the healthiest. `bound` is what stops that.

    The first assertion is the trap, on the real path; the second is the rule that answers it."""
    real = judge(_suite(tmp_path), _tape(tmp_path / "rides", "silent", _SILENT), "ride")
    assert real.checks["refines"][0] == 0 and real.vacuous

    assert "vacuity (a tape that emits no act)" in _verdict(tmp_path, bound=0,
                                                            budget={"t": 99}).red()


def test_the_same_silence_is_not_a_failure_for_an_ungated_class(tmp_path):
    """A class that cannot refine is not held to refinement, and vacuity is a refinement
    argument. Held to licensing alone, an act-free tape has nothing to answer for."""
    v = judge(_suite(tmp_path), _tape(tmp_path / "rides", "silent", _SILENT), "ride")
    assert v.vacuous and v.red() == []


def test_a_gated_tape_with_no_budget_is_red_rather_than_assumed_zero(tmp_path):
    """A missing number must not read as zero. The ratchet is a decision per tape, and a tape
    nobody has decided about is a tape nobody has triaged."""
    assert any("no totality budget" in r for r in _verdict(tmp_path, bound=3, budget={}).red())


def test_the_ratchet_fires_only_above_its_high_water_mark(tmp_path):
    """At the mark is green; one over is red. A high-water mark, not a target."""
    assert _verdict(tmp_path, bound=3, total=5, budget={"t": 5}).red() == []
    assert any("totality ratchet" in r
               for r in _verdict(tmp_path, bound=3, total=6, budget={"t": 5}).red())


def test_bound_kinds_are_read_off_the_model_not_restated(tmp_path):
    """A copy of this list would be a second source of truth, and the second source is always
    the one that is wrong."""
    assert _suite(tmp_path).bound_kinds == {
        c.id for c in MODEL.children
        if c.kind == "event-kind" and (c.payload.get("args") or {})}


def test_the_receipt_names_each_tape_by_digest_and_the_model_by_its_pin(tmp_path):
    """A receipt saying "green" is worth nothing on its own — anyone can write one. It is worth
    something because a gate can ask whether the tapes on disk are the tapes it judged."""
    s = _suite(tmp_path, receipt=True)
    tape = _tape(tmp_path / "rides", "lawful", _RIDE)
    write_receipt(s, [judge(s, tape, "ride")])
    got = json.loads((tmp_path / "receipt.json").read_text(encoding="utf-8"))

    assert got["green"] is True
    assert got["model"] == "turnstile@1.0.0", "the version is the pin, never typed"
    assert "timestamp" not in got, "a field that changes every run teaches people to skip it"
    assert got["tapes"][0]["sha256"] == hashlib.sha256(tape.read_bytes()).hexdigest()

    # Edit the evidence and the receipt stops describing it — the property a gate leans on.
    tape.write_bytes(tape.read_bytes() + b"\n")
    assert got["tapes"][0]["sha256"] != hashlib.sha256(tape.read_bytes()).hexdigest()


def test_a_run_over_a_named_directory_leaves_no_receipt(tmp_path):
    """Judging somebody's production tapes is a question being asked, not this app's own tapes
    being certified. Grounding a gate on it would let an arbitrary directory decide whether the
    repo may ship."""
    s = _suite(tmp_path, receipt=True)
    _tape(tmp_path / "elsewhere", "lawful", _RIDE)
    assert main(s, [str(tmp_path / "elsewhere"), "--as", "ride"]) == 0
    assert not (tmp_path / "receipt.json").exists()


def test_the_default_run_walks_every_class_and_leaves_one(tmp_path):
    s = _suite(tmp_path, receipt=True)
    _tape(tmp_path / "rides", "lawful", _RIDE)
    assert main(s, []) == 0
    assert (tmp_path / "receipt.json").is_file()
