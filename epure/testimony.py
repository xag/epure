"""One table per app: what each act testifies to, beside the code that emits it.

The effect declarations the conduct natives read (`epure.behavior`) are data on the model's
actions — and the model is a package, authored in one file, while the acts are emitted from
wherever the code does the work. Two places for one fact, and the second place is always the
one that drifts: an act grows a write and the model still says it writes nothing, until a tape
convicts it. The frame law caught exactly that on its first run. This module is the seam that
makes the drift structural rather than disciplinary:

- The APP holds one table, next to its `span()` call sites, with no dependency on épure: the
  acts it emits, the arguments each carries, and what each does to the store — effects and the
  write boundary, in the doors the natives read. Plain data; see `Acts.from_table`.
- The MODEL generates its actions' effect children from that table (`Acts.children`), so the
  package and the code cannot say two things about one act: the package's content IS the
  table's, instantiated per action.
- The app's tests hold every emission literal to the table (`Acts.undeclared`), so an act the
  code emits and the table does not know is refused where it is written, not on a tape.

An act is ONE event kind, and a model may bind it to several actions — chores' `turn-done`
instantiates done-wash, done-hoover or done-bins by its `chore` argument. So a declaration is
written once, per act, with its entities TEMPLATED over the act's arguments (`"{chore}_pending"`),
and instantiated per action with that action's fixed binding. The template lives here, in the
app's declaration, never in a law: the laws stay generic, the binding is the app's to state.

The emission-side guard lives in flight-recorder, not here: `flight_recorder.declare(ACTS)`
takes this same table and refuses, while a tape is being made, a span or note the table does
not know — so the app carries no dependency on épure (which carries quern, which carries a
wasm runtime a running app has no use for). `Acts.undeclared` stays as the second reader,
for a source scan in the app's tests; `Acts.children` is the model side.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from quern import Node

EFFECT_KINDS = ("creates", "mutates", "deletes")

# `fr.span("name", ...)`, `fr.note("name")`, `span("name"`, `note("name"` — the literal an
# emission site names its act with. A name computed at runtime is not found here, and that
# is a finding in itself: an act whose name the source does not state is an act no table
# can declare.
_EMISSION = re.compile(r"\b(?:span|note)\(\s*([\"'])([a-z][a-z0-9-]*)\1")


class Act:
    """One declared act: its arguments, its effects (templated), its write boundary."""

    def __init__(self, name: str, spec: dict[str, Any]):
        self.name = name
        self.args = list(spec.get("args") or [])
        self.effects: list[dict[str, Any]] = []
        for kind in EFFECT_KINDS:
            for eff in _listed(spec.get(kind)):
                if not isinstance(eff, dict) or "entity" not in eff:
                    raise ValueError(f"act '{name}': a {kind} declaration names its entity "
                                     f"(and via/shown_by), not {eff!r}")
                self.effects.append({"kind": kind, **eff})
        touches = spec.get("touches")
        if touches is not None and not isinstance(touches, dict):
            raise ValueError(f"act '{name}': touches is {{only: [...], via: [...]}}, "
                             f"not {touches!r}")
        self.touches: dict[str, Any] | None = touches
        unknown = set(spec) - {"args", "touches", *EFFECT_KINDS, "note"}
        if unknown:
            raise ValueError(f"act '{name}': unknown key(s) {sorted(unknown)}")

    def children(self, action: str, binding: dict[str, Any] | None = None,
                 also: Iterable[str] = (), unmodeled: Iterable[str] = ()) -> list[Node]:
        """The effect nodes of one action that this act witnesses: every `{arg}` in an
        entity or a touched name substituted from `binding`; `also` adds state-vars this
        particular action moves beyond the templated ones (done-hoover moves hoover_last);
        `unmodeled` names entities the act really moves that THIS model abstracts away
        (chores' wash has no assignee variable) — dropped from the effects and the
        boundary, so the model's abstraction is stated where it is made, not faked in
        the app's table."""
        binding = dict(binding or {})
        unmodeled = set(unmodeled)
        missing = [a for a in self.args if a not in binding]
        if any("{" in str(e["entity"]) for e in self.effects) and missing:
            raise ValueError(f"act '{self.name}' templates over {self.args}; action "
                             f"'{action}' binds no {missing}")
        out: list[Node] = []
        for eff in self.effects:
            entity = _fill(eff["entity"], binding)
            if entity in unmodeled:
                continue
            payload: dict[str, Any] = {"entity": entity}
            if eff["kind"] != "deletes":
                payload["from"] = list(eff.get("from") or [])
            for key in ("via", "shown_by"):
                if key in eff:
                    payload[key] = eff[key]
            out.append(Node(id=f"{action}-{eff['kind']}-{entity}", kind=eff["kind"],
                            payload=payload))
        if self.touches is not None:
            only = [v for v in (_fill(v, binding) for v in self.touches.get("only") or [])
                    if v not in unmodeled] + list(also)
            out.append(Node(id=f"{action}-touches", kind="touches",
                            payload={"only": only, "via": list(self.touches.get("via") or [])}))
        return out


class Acts:
    """An app's declared acts, by name."""

    def __init__(self, acts: dict[str, Act]):
        self._acts = acts

    @classmethod
    def from_table(cls, table: dict[str, dict[str, Any]]) -> "Acts":
        """The app-side shape — plain data, so an app declares without importing épure:

            ACTS = {
                "turn-done": {
                    "args": ["chore"],
                    "mutates": [{"entity": "{chore}_pending", "from": ["chore"],
                                 "via": COMPLETION, "shown_by": READ_LOG}],
                    "touches": {"only": ["{chore}_pending"], "via": [COMPLETION, REV]},
                },
                "board-read": {"touches": {"only": [], "via": []}},
            }
        """
        return cls({name: Act(name, spec) for name, spec in table.items()})

    def __contains__(self, name: str) -> bool:
        return name in self._acts

    def __getitem__(self, name: str) -> Act:
        if name not in self._acts:
            raise KeyError(f"'{name}' is not a declared act; declared: {self.alphabet()}")
        return self._acts[name]

    def alphabet(self) -> list[str]:
        return list(self._acts)

    def children(self, act: str, action: str, also: Iterable[str] = (),
                 unmodeled: Iterable[str] = (), **binding: Any) -> list[Node]:
        """Effect children for `action`, witnessed by `act`, bound by keyword."""
        return self[act].children(action, binding, also, unmodeled)

    # --- holding the source to the table ---------------------------------------------

    def undeclared(self, sources: Iterable[Path | str]) -> list[str]:
        """Every emission literal in `sources` that names an act this table does not
        declare — as 'path:line: name'. The app's test asserts this is empty."""
        out: list[str] = []
        for src in sources:
            path = Path(src)
            for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                for m in _EMISSION.finditer(line):
                    name = m.group(2)
                    if name not in self._acts:
                        out.append(f"{path}:{i}: {name}")
        return out

    def emitted(self, sources: Iterable[Path | str]) -> set[str]:
        """Every act name the sources emit — to hold the table to the code the other way:
        a declared act nothing emits is a word no tape will ever carry."""
        names: set[str] = set()
        for src in sources:
            text = Path(src).read_text(encoding="utf-8")
            names.update(m.group(2) for m in _EMISSION.finditer(text))
        return names


def _listed(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, list) else [value]


def _fill(template: Any, binding: dict[str, Any]) -> str:
    try:
        return str(template).format(**binding)
    except KeyError as e:
        raise ValueError(f"'{template}' names {e}, which the action does not bind") from None
