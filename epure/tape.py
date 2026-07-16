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
        return _scenario(source.record, source.spans())
    if isinstance(source, Recording):
        calls, trees = source.calls, source.spans()
    else:
        calls = [ln for ln in read_tape(source) if ln.get("ev") == "call"]
        trees = Recording({}, calls).spans()
    return Node(id="session", kind="session",
                children=[_scenario(rec, tree) for rec, tree in zip(calls, trees)])


def _scenario(record: dict[str, Any], tree: dict[str, Any]) -> Node:
    """One call: a `scenario` node named for its `fn`, over the span tree of its `sem` events.
    Raw events enclosed by no span land in `payload["events"]`, the totality check's tally."""
    return Node(
        id=f"call{record.get('seq')}",
        kind="scenario",
        name=record.get("fn") or "",
        payload={"seq": record.get("seq"), "ts": record.get("ts"),
                 "ms": record.get("ms"), "events": tree["events"]},
        children=[_span(child, i) for i, child in enumerate(tree["children"])],
    )


def _span(node: dict[str, Any], i: int) -> Node:
    """A span or point of the flight-recorder span tree as a node: its `name` is the kind
    (the semantic alphabet is the node vocabulary), its data/outcome/events the payload, its
    nested spans and points the children — all in document order."""
    return Node(
        id=f"s{i}",
        kind=node["name"],
        payload={"data": node["data"], "outcome": node["outcome"],
                 "events": node["events"]},
        children=[_span(child, j) for j, child in enumerate(node["children"])],
    )
