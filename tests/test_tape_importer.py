"""A semantic tape becomes a scenario subtree, and rules ask questions of it.

The importer is the bridge that lets every downstream check be an ordinary `run_rules` over
nodes instead of bespoke tape-walking in each consumer. So the tests hold it to exactly that:
the span nesting round-trips, document order survives as the trace verbs' order, raw events
that no span enclosed land on the scenario node (the totality check's tally), and the same
bytes always import to the same tree — determinism is what makes a downstream verdict
replayable. The last test is the whole point stated end to end: a hand-written rule over span
kinds, run against an imported tape, returns a verdict.

The tape is flight-recorder's own sem-event conformance fixture, vendored under `fixtures/`
so the test is hermetic: a synthetic enrolment (load a corpus, register an account, and fail),
nothing drawn from anyone's real system. One deliberate divergence from the upstream bytes:
the example email address is scrubbed to `user-t`, because the open-ready gate refuses
anything shaped like an email — re-vendoring verbatim would reintroduce it.
"""

from __future__ import annotations

from pathlib import Path

from quern import Quern, Rule, following, is_before, preceding, run_rules

from epure.tape import import_scenario, read_tape
from flight_recorder.mutate import Recording

_FIXTURE = Path(__file__).parent / "fixtures" / "python-sem-toy.jsonl"


def _skeleton(node) -> tuple:
    """A node as (kind, [children...]) — the shape, stripped of payload."""
    return node.kind, [_skeleton(c) for c in node.children]


def _span_skeleton(tree: dict) -> tuple:
    """The same shape read straight off flight-recorder's span tree, for the round-trip."""
    return tree["name"], [_span_skeleton(c) for c in tree["children"]]


def test_a_recording_imports_as_a_session_of_scenarios():
    root = import_scenario(_FIXTURE)
    assert root.kind == "session"
    scenarios = root.children
    assert [s.kind for s in scenarios] == ["scenario"]
    (scenario,) = scenarios
    assert scenario.name == "enrol"  # the call's fn
    assert set(scenario.payload) >= {"seq", "ts", "ms", "events"}
    assert scenario.payload["seq"] == 1


def test_the_span_nesting_round_trips():
    """The imported children mirror flight-recorder's own span derivation, one for one —
    kinds are the semantic names, nested spans and points are children in document order."""
    scenario = import_scenario(_FIXTURE).children[0]
    span_tree = Recording.load(_FIXTURE).call(0).spans()
    assert [_skeleton(c) for c in scenario.children] == \
        [_span_skeleton(c) for c in span_tree["children"]]


def test_a_span_carries_data_outcome_and_its_own_events():
    enrol = import_scenario(_FIXTURE).children[0].children[0]
    load_corpus, corpus_read, register, failed = enrol.children

    assert load_corpus.kind == "load_corpus"
    assert load_corpus.payload["outcome"] == "ok"
    assert [e["k"] for e in load_corpus.payload["events"]] == ["db"]  # directly enclosed

    assert register.payload["outcome"] == "error"
    assert [e["k"] for e in register.payload["events"]] == ["fx", "fx"]

    # a point note is a leaf: same mapping, no outcome, encloses nothing
    assert corpus_read.kind == "corpus_read"
    assert corpus_read.payload["data"] == {"rows": 3}
    assert corpus_read.payload["outcome"] is None
    assert corpus_read.children == []

    # a span's own events are its alone — the db lives under load_corpus, not under enrol
    assert enrol.payload["events"] == []


def test_events_enclosed_by_no_span_land_on_the_scenario():
    scenario = import_scenario(_FIXTURE).children[0]
    assert [e["k"] for e in scenario.payload["events"]] == ["now"]


def test_document_order_is_the_trace_verbs_order():
    tree = Quern()
    tree.root.children = [import_scenario(_FIXTURE)]
    enrol = "session/call1/s0"
    load_corpus, register, failed = f"{enrol}/s0", f"{enrol}/s2", f"{enrol}/s3"

    assert is_before(tree, load_corpus, register)
    assert not is_before(tree, register, load_corpus)
    assert preceding(tree, register, "load_corpus") == [load_corpus]
    assert following(tree, register, "registration_failed") == [failed]


def test_import_is_byte_deterministic():
    """Same tape, equal trees — no clock, no ordering drawn from anything but the bytes."""
    assert import_scenario(_FIXTURE) == import_scenario(_FIXTURE)

    # and from an already-loaded Recording, identically
    rec = Recording(read_tape(_FIXTURE)[0], read_tape(_FIXTURE)[1:])
    assert import_scenario(rec) == import_scenario(_FIXTURE)


def test_a_single_call_imports_as_one_scenario():
    call = Recording.load(_FIXTURE).call(0)
    node = import_scenario(call)
    assert node.kind == "scenario" and node.name == "enrol"


def test_a_hand_written_rule_reads_a_verdict_off_the_imported_tape():
    """The idiom, end to end: import a tape, attach a rule that quantifies over span kinds
    with the trace verbs, run the checker, read the verdict — no tape-walking anywhere."""
    tree = Quern(rules=[
        Rule(name="corpus-loads-before-registering", kind="register",
             description="a registration is attempted only after the corpus is loaded",
             expr="len(preceding(self, 'load_corpus')) >= 1"),
        Rule(name="a-failure-is-reported-after-it-fails", kind="registration_failed",
             expr="len(preceding(self, 'register')) >= 1"),
        # a claim the trace refutes: registering does not precede loading the corpus
        Rule(name="registering-precedes-loading", kind="register",
             expr="len(following(self, 'load_corpus')) >= 1"),
    ])
    tree.root.children = [import_scenario(_FIXTURE)]

    verdict = {r.rule: r.ok for r in run_rules(tree)}
    assert verdict["corpus-loads-before-registering"]
    assert verdict["a-failure-is-reported-after-it-fails"]
    assert not verdict["registering-precedes-loading"]
