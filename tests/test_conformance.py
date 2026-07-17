"""The conformance natives, end to end: a tape is imported, linked to its model, judged.

Fixture tapes are built inline — synthetic turnstile rides, sem events over a coin acceptor
and a rotation sensor, nothing drawn from anyone's real system — and run through the real
importer, so what these tests exercise is the exact path a consumer's CI will: tape bytes ->
scenario subtree -> `solve('model/<check>', self, 'model')`. Every red case asserts its
diagnostic names the offender; a count with no name is an alarm nobody can act on.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quern import Quern, Rule, run_rules

from epure.conformance import licensed, refines, total
from epure.package import EXAMPLES
from epure.tape import import_scenario


def _sem(name: str, phase: str, sid: int, **kw) -> dict:
    return {"k": "sem", "name": name, "phase": phase, "sid": sid, **kw}


_COIN = [_sem("coin", "begin", 1),
         {"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {}, "res": 1},
         _sem("coin", "end", 1, outcome="ok")]
_PUSH = [_sem("push", "begin", 2),
         {"k": "fx", "fn": "sensor.read", "args": [], "kwargs": {}, "res": 1},
         _sem("push", "end", 2, outcome="ok")]


def _tape(tmp_path: Path, *calls: list) -> Path:
    path = tmp_path / "ride.jsonl"
    lines = [{"ev": "session", "version": 1, "python": "3"}]
    lines += [{"ev": "call", "seq": i + 1, "fn": "ride", "events": events,
               "ts": "t", "ms": 1} for i, events in enumerate(calls)]
    path.write_text("\n".join(json.dumps(ln) for ln in lines) + "\n", encoding="utf-8")
    return path


def _tree(tmp_path: Path, *calls: list, link: bool = True) -> Quern:
    session = import_scenario(_tape(tmp_path, *calls))
    if link:
        session.links = {"model": ["turnstile"]}
    tree = Quern()
    tree.root.children = [EXAMPLES[0].model_copy(deep=True), session]
    return tree


# --- green: a lawful ride passes all three ----------------------------------------------


def test_a_lawful_ride_is_licensed_total_and_refining(tmp_path):
    tree = _tree(tmp_path, _COIN + _PUSH)
    assert licensed(tree, "session", "model").violations == 0
    assert total(tree, "session", "model").violations == 0
    assert refines(tree, "session", "model").violations == 0


def test_the_natives_answer_in_the_rule_language(tmp_path):
    tree = _tree(tmp_path, _COIN + _PUSH)
    tree.rules.append(Rule(
        name="the-tape-conforms", kind="session",
        expr="solve('model/licensed', self, 'model') == 0 and "
             "solve('model/total', self, 'model') == 0 and "
             "solve('model/refines', self, 'model') == 0"))
    assert all(r.ok for r in run_rules(tree) if r.rule == "the-tape-conforms")


# --- model/licensed ----------------------------------------------------------------------


def test_an_unlicensed_span_is_convicted_by_name(tmp_path):
    empty_coin = [_sem("coin", "begin", 1), _sem("coin", "end", 1, outcome="ok")]
    tree = _tree(tmp_path, empty_coin + _PUSH)
    verdict = licensed(tree, "session", "model")
    assert verdict.violations == 1
    (diag,) = verdict.diagnostics
    assert "session/call1/s0" in diag and "coin-license" in diag
    # the same tape still refines — licensing and refinement are different questions
    assert refines(tree, "session", "model").violations == 0


def test_unknown_testimony_is_unlicensed_by_definition(tmp_path):
    tree = _tree(tmp_path, _COIN + [_sem("jump", "point", 9, data={})])
    verdict = licensed(tree, "session", "model")
    assert verdict.violations == 1
    assert "names no event-kind" in verdict.diagnostics[0]


def test_nested_spans_are_licensed_at_every_depth(tmp_path):
    # a nested claim with an empty raw window: the parent is fine, the child is convicted
    nested = [_sem("coin", "begin", 1),
              {"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {}, "res": 1},
              _sem("push", "begin", 2), _sem("push", "end", 2, outcome="ok"),
              _sem("coin", "end", 1, outcome="ok")]
    verdict = licensed(_tree(tmp_path, nested), "session", "model")
    assert verdict.violations == 1
    assert "s0/s0" in verdict.diagnostics[0]


# --- evidence beyond the claiming span's own window --------------------------------------


_SENSOR = {"k": "fx", "fn": "sensor.read", "args": [], "kwargs": {}, "res": 1}
_TALLY = _sem("passage-counted", "point", 3, data={})


def test_a_derived_point_is_licensed_by_its_ancestors_read(tmp_path):
    # the instantaneous act encloses nothing; its license names the sensor read one level
    # up — and the point stays decomposition: refinement never sees it
    ride = _COIN + [_sem("push", "begin", 2), _SENSOR, _TALLY,
                    _sem("push", "end", 2, outcome="ok")]
    tree = _tree(tmp_path, ride)
    assert licensed(tree, "session", "model").violations == 0
    assert refines(tree, "session", "model").violations == 0


def test_sibling_acts_derived_from_one_read_are_all_licensed(tmp_path):
    # v0's mutual exclusion dissolves: one read, two claims above it, both acquitted
    ride = _COIN + [_sem("push", "begin", 2), _SENSOR,
                    _sem("passage-counted", "point", 3, data={}),
                    _sem("passage-counted", "point", 4, data={}),
                    _sem("push", "end", 2, outcome="ok")]
    assert licensed(_tree(tmp_path, ride), "session", "model").violations == 0


def test_a_claim_with_no_evidence_anywhere_still_goes_red(tmp_path):
    # the widening did not dissolve the check: no sensor.read along the lineage, convicted
    verdict = licensed(_tree(tmp_path, _COIN + _PUSH + [_TALLY]), "session", "model")
    assert verdict.violations == 1
    assert "passage-counted-license" in verdict.diagnostics[0]


def test_unrelated_ancestor_io_does_not_license_a_named_claim(tmp_path):
    # nested under coin, whose window holds an acceptor.read: I/O above the claim, and the
    # wrong I/O — a bare enclosing count would acquit here, which is why it is not offered
    ride = [_sem("coin", "begin", 1),
            {"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {}, "res": 1},
            _TALLY,
            _sem("coin", "end", 1, outcome="ok")] + _PUSH
    verdict = licensed(_tree(tmp_path, ride), "session", "model")
    assert verdict.violations == 1
    assert "passage-counted-license" in verdict.diagnostics[0]


def test_a_span_wrapping_the_wrong_io_is_convicted(tmp_path):
    # naming sharpens the own window too: a coin span enclosing a sensor read counted
    # under v0's bare len(ctx('events')) — now the acceptor is named, so it convicts
    wrong = [_sem("coin", "begin", 1), _SENSOR, _sem("coin", "end", 1, outcome="ok")]
    verdict = licensed(_tree(tmp_path, wrong + _PUSH), "session", "model")
    assert verdict.violations == 1
    assert "coin-license" in verdict.diagnostics[0]


def test_orphan_raw_events_never_license(tmp_path):
    # the sensor read is enclosed by NO span: totality's violation must not double as
    # licensing's evidence — behavior the model does not know exists licenses nothing
    tree = _tree(tmp_path, _COIN + _PUSH + [_SENSOR, _TALLY])
    assert licensed(tree, "session", "model").violations == 1
    assert total(tree, "session", "model").violations == 1


def test_a_wider_gaze_through_ctx_is_refused_with_the_road_named(tmp_path):
    tree = _tree(tmp_path, _COIN + _PUSH)
    model = tree.root.children[0]
    model.child("coin").child("coin-license").payload["expr"] = \
        "len(ctx('events', 'enclosing')) >= 1"
    verdict = licensed(tree, "session", "model")
    assert verdict.violations == 1
    assert "names its evidence" in verdict.diagnostics[0]


# --- model/total -------------------------------------------------------------------------


def test_an_orphan_raw_event_is_a_violation(tmp_path):
    tree = _tree(tmp_path, [{"k": "now", "v": "t"}] + _COIN + _PUSH)
    verdict = total(tree, "session", "model")
    assert verdict.violations == 1
    assert "raw 'now' event enclosed by no span" in verdict.diagnostics[0]
    # licensing and refinement stay green: the orphan is exactly and only totality's catch
    assert licensed(tree, "session", "model").violations == 0
    assert refines(tree, "session", "model").violations == 0


# --- model/refines -----------------------------------------------------------------------


def test_an_illegal_transition_names_the_first_divergent_span(tmp_path):
    tree = _tree(tmp_path, _PUSH + _COIN)  # push against a locked turnstile
    verdict = refines(tree, "session", "model")
    assert verdict.violations == 1
    (diag,) = verdict.diagnostics
    assert "session/call1/s0" in diag and "push" in diag
    assert "guard is false" in diag and "'state': 'locked'" in diag


def test_an_unknown_kind_is_a_refinement_violation_too(tmp_path):
    tree = _tree(tmp_path, [_sem("jump", "point", 9, data={})])
    verdict = refines(tree, "session", "model")
    assert verdict.violations == 1
    assert "not testimony to any action" in verdict.diagnostics[0]


def test_refinement_consumes_top_level_spans_only(tmp_path):
    # a second 'coin' nested INSIDE the first: decomposition, not a transition — a
    # flattening would read coin, coin and refuse the second against an unlocked turnstile
    nested_coin = [_sem("coin", "begin", 1),
                   {"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {}, "res": 1},
                   _sem("coin", "begin", 2),
                   {"k": "fx", "fn": "acceptor.read", "args": [], "kwargs": {}, "res": 1},
                   _sem("coin", "end", 2, outcome="ok"),
                   _sem("coin", "end", 1, outcome="ok")]
    tree = _tree(tmp_path, nested_coin + _PUSH)
    assert refines(tree, "session", "model").violations == 0
    assert licensed(tree, "session", "model").violations == 0


def test_a_session_refines_as_one_continuous_behavior(tmp_path):
    tree = _tree(tmp_path, _COIN, _PUSH)  # two calls, one accumulating state
    assert refines(tree, "session", "model").violations == 0

    # the same second call judged alone diverges: its push fires against init
    alone = _tree(tmp_path, _COIN, _PUSH, link=False)
    session = alone.root.children[1]
    session.child("call2").links = {"model": ["turnstile"]}
    assert refines(alone, "session/call2", "model").violations == 1


# --- args: bound from span data, held to their domains ----------------------------------


def _forceful(tree: Quern) -> Quern:
    """The turnstile, its push parameterized: the event carries a force, the license and
    the guard both read it — the arg-binding path end to end."""
    model = tree.root.children[0]
    push = model.child("push")
    push.payload["args"] = {"force": {"type": "int", "domain": {"min": 0, "max": 3}}}
    push.child("push-license").payload["expr"] = "force >= 1 and len(ctx('events')) >= 1"
    through = model.child("push-through")
    through.payload["args"] = {"force": {"type": "int", "domain": {"min": 0, "max": 3}}}
    through.payload["guard"] = "state == 'unlocked' and force >= 1"
    return tree


def test_args_bind_from_span_data(tmp_path):
    push = [_sem("push", "begin", 2, data={"force": 2}),
            {"k": "fx", "fn": "sensor.read", "args": [], "kwargs": {}, "res": 1},
            _sem("push", "end", 2, outcome="ok")]
    tree = _forceful(_tree(tmp_path, _COIN + push))
    assert licensed(tree, "session", "model").violations == 0
    assert refines(tree, "session", "model").violations == 0


def test_a_claim_without_its_declared_args_is_malformed(tmp_path):
    tree = _forceful(_tree(tmp_path, _COIN + _PUSH))  # push carries no force
    assert "declared arg(s) ['force']" in licensed(tree, "session", "model").diagnostics[0]
    diag = refines(tree, "session", "model").diagnostics[0]
    assert "needs arg 'force'" in diag


def test_an_out_of_domain_arg_is_a_divergence(tmp_path):
    push = [_sem("push", "begin", 2, data={"force": 9}),
            {"k": "fx", "fn": "sensor.read", "args": [], "kwargs": {}, "res": 1},
            _sem("push", "end", 2, outcome="ok")]
    tree = _forceful(_tree(tmp_path, _COIN + push))
    diag = refines(tree, "session", "model").diagnostics[0]
    assert "outside its declared domain" in diag


# --- the convention is load-bearing ------------------------------------------------------


def test_a_slice_naming_no_model_is_unjudged_not_green(tmp_path):
    tree = _tree(tmp_path, _COIN + _PUSH, link=False)
    for check in (licensed, total, refines):
        with pytest.raises(ValueError, match="exactly one model"):
            check(tree, "session", "model")


def test_a_link_to_a_non_model_is_refused(tmp_path):
    tree = _tree(tmp_path, _COIN + _PUSH)
    session = tree.root.children[1]
    session.links = {"model": ["turnstile/coins"]}
    with pytest.raises(ValueError, match="not a model"):
        refines(tree, "session", "model")


# --- determinism -------------------------------------------------------------------------


def test_same_tape_same_model_same_verdicts(tmp_path):
    story = [{"k": "now", "v": "t"}] + _PUSH + [_sem("jump", "point", 9, data={})]
    a, b = (_tree(tmp_path, story) for _ in range(2))
    for check in (licensed, total, refines):
        assert check(a, "session", "model") == check(b, "session", "model")
