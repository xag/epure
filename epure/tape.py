"""The tape: the one IO seam that reads it, and the importer that turns it into a tree.

Every byte epure reads from a recording enters through `read_tape`, and that is deliberate.
A boundary is a *declaration* — the recorder cannot know about an input it was never told
crosses the line — so an app whose file reads are scattered across ten call sites has ten
things to declare and nine chances to forget one. Funnelling them through a single module
function makes the declaration in `epure.boundary` true by construction rather than by
diligence, and it is the reason this module exists at all for a function this small.

The tape's shape is the frozen contract in flight-recorder's `spec/tape-v1.md`; `read_tape`
reads lines, and interprets nothing. A truncated final line is the only corruption the format
permits (the process died mid-write) and the spec requires a reader to discard it, so that
is what this does — silently, because it is a normal end for a tape, not a defect in one.

`import_scenario` is the bridge from a tape to the substrate's own idiom: a semantic tape
becomes a `scenario` subtree of ordinary nodes, so that every downstream question —
licensing, totality, refinement, and whatever a domain writes with the trace verbs — is
asked with `run_rules` over the tree, never by bespoke tape-walking code in a consumer. It
is a pure function of the tape bytes: no clock, no writes, no interpretation. It carries
names and payloads across and judges nothing — the judging is a rule's, later.

POSITIONS TRAVEL. The span tree separates a node's own raw events from its children's, which
is what makes it readable — and it is what lost the interleaving: a point's place among its
parent's raw events did not survive import, so no check could say "after". The conduct
natives (`epure.behavior`) need exactly that — an effect is shown by a read that comes AFTER
the act — so every span now carries `at`/`to` (the stream index of its begin and end marks)
and every event list a parallel `pos` (each event's index in the call's stream). The lists
are unchanged; the indexes ride beside them, so nothing that read a tape before reads it
differently now. This is the first half of the `license-direction-is-blind` discharge in
the ledger; the other half (a direction on `evidence()`) waits for the license that needs it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flight_recorder.mutate import CallHandle, Recording
from quern import Node


def read_tape(path: str | Path) -> list[dict[str, Any]]:
    """A recording's lines: the `session` header first, then one object per `call`."""
    text = Path(path).read_text(encoding="utf-8")
    lines = [ln for ln in text.split("\n") if ln.strip()]
    out: list[dict[str, Any]] = []
    for i, line in enumerate(lines):
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            if i == len(lines) - 1:
                break  # the last line was torn: the process died mid-write
            raise
    return out


def import_scenario(source: str | Path | Recording | CallHandle) -> Node:
    """A semantic tape as a scenario subtree of ordinary nodes.

    `source` is a `flight_recorder.mutate.Recording`, a single `CallHandle`, or a tape path.
    A single call becomes one `scenario` node; a whole recording becomes a `session` node
    whose children are the per-call scenarios in tape order. Document order is preserved
    everywhere, so the trace verbs' notion of "before" coincides with emission order.
    """
    if isinstance(source, CallHandle):
        return _scenario(source.record)
    if isinstance(source, Recording):
        calls = source.calls
    else:
        calls = [ln for ln in read_tape(source) if ln.get("ev") == "call"]
    return Node(id="session", kind="session",
                children=[_scenario(rec) for rec in calls])


def _skeleton(record: dict[str, Any]) -> dict[str, Any]:
    """The call's span tree, derived from order exactly as flight-recorder's own
    `_span_tree` derives it (the round-trip is tested), plus what that tree drops: each
    node's `at`/`to` and each event's `pos` in the call's stream. Forgiving about a
    malformed tape for the same reason it is — an `end` with nothing open is ignored, an
    unclosed span stays open with `outcome: None`."""
    root: dict[str, Any] = {"name": record.get("fn"), "data": record.get("kwargs") or {},
                            "outcome": "error" if record.get("error") else "ok",
                            "children": [], "events": [], "pos": [], "at": -1, "to": None}
    stack = [root]
    for i, ev in enumerate(record.get("events") or []):
        if ev.get("k") != "sem":
            stack[-1]["events"].append(ev)
            stack[-1]["pos"].append(i)
            continue
        phase = ev.get("phase")
        node = {"name": ev.get("name"), "data": ev.get("data") or {}, "outcome": None,
                "children": [], "events": [], "pos": [], "at": i, "to": i}
        if phase == "point":
            stack[-1]["children"].append(node)
        elif phase == "begin":
            node["to"] = None
            stack[-1]["children"].append(node)
            stack.append(node)
        elif phase == "end" and len(stack) > 1:
            done = stack.pop()
            done["outcome"] = ev.get("outcome")
            done["to"] = i
    root["to"] = len(record.get("events") or [])
    return root


def _scenario(record: dict[str, Any]) -> Node:
    """One call: a `scenario` node named for its `fn`, over the span tree of its `sem` events.
    Raw events enclosed by no span land in `payload["events"]`, the totality check's tally."""
    tree = _skeleton(record)
    return Node(
        id=f"call{record.get('seq')}",
        kind="scenario",
        name=record.get("fn") or "",
        payload={"seq": record.get("seq"), "ts": record.get("ts"),
                 "ms": record.get("ms"), "events": tree["events"], "pos": tree["pos"],
                 # the call as an act: its inputs, its outcome, its whole window — so the
                 # conduct natives can bind the tool itself to a declaration
                 "data": record.get("kwargs") or {}, "outcome": tree["outcome"],
                 "at": -1, "to": tree["to"]},
        children=[_span(child, i) for i, child in enumerate(tree["children"])],
    )


def _span(node: dict[str, Any], i: int) -> Node:
    """A span or point of the flight-recorder span tree as a node: its `name` is the kind
    (the semantic alphabet is the node vocabulary), its data/outcome/events the payload, its
    nested spans and points the children — all in document order. `at`/`to` are the stream
    indexes of its begin and end marks (a point: both its own; an unclosed span: `to` None);
    `pos` is the index of each of its own events."""
    return Node(
        id=f"s{i}",
        kind=node["name"],
        payload={"data": node["data"], "outcome": node["outcome"],
                 "events": node["events"], "pos": node["pos"],
                 "at": node["at"], "to": node["to"]},
        children=[_span(child, j) for j, child in enumerate(node["children"])],
    )
