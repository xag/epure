"""The one IO seam: reading a tape off the disk.

Every byte epure reads from a recording enters through `read_tape`, and that is deliberate.
A boundary is a *declaration* — the recorder cannot know about an input it was never told
crosses the line — so an app whose file reads are scattered across ten call sites has ten
things to declare and nine chances to forget one. Funnelling them through a single module
function makes the declaration in `epure.boundary` true by construction rather than by
diligence, and it is the reason this module exists at all for a function this small.

The tape's shape is the frozen contract in flight-recorder's `spec/tape-v1.md`; this reads
lines, and interprets nothing. A truncated final line is the only corruption the format
permits (the process died mid-write) and the spec requires a reader to discard it, so that
is what this does — silently, because it is a normal end for a tape, not a defect in one.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


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
