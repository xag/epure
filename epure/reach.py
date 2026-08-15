"""model/escapes: from every reachable state, a way back.

`prove` answers safety — no reachable state is bad. This answers the other half of
what a walk of the state graph can decide: LIVENESS of return. "From every state the
model can reach, some action sequence reaches a state satisfying `home`." An interface
model owes this to the person inside it (a sheet with no close, a fold that traps —
craft@'s a-way-back names the law); a protocol model owes it to the operator (a state
you can enter and never drain). A prover that only checks invariants cannot see this
defect, because every stranded state can be individually fine.

The check is two walks over the same graph `prove` explores: BFS forward from init to
enumerate states and edges (minimal witness paths, same as prove), then BFS backward
from every home state over the reversed edges. Whatever the backward walk never
reaches is stranded, and each stranded state is reported with the shortest action
sequence that gets a person INTO it — which is the repro, since the complaint "and
then you are stuck" needs no path to demonstrate.

Two refusals worth their names: a `home` no reachable state satisfies is reported as
its own verdict rather than as "everything is stranded" (the claim was miswritten,
and 44 identical violations would bury that fact); and the cap raises exactly as in
`prove`, because a partial walk is not a proof of return.

No native is registered here yet: the consumers so far call `escapes()` as a
function. The day a ledger rule wants `solve('model/escapes', ...)`, the contract
enters the spec beside model/prove and a package declares it — a native nothing
declares is a capability nobody can audit.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quern import Quern, TreeStore

from .prove import DEFAULT_CAP, _LITERALS, _compile, _load, _model_sha256


@dataclass
class Stranded:
    """One state with no way home, and the shortest way into it."""

    path: list[dict[str, Any]]          # [{'action': id, 'args': {...}}, ...] from init
    state: dict[str, Any]
    exits: list[str]                    # actions enabled there — stuck with doors, or none

    def replay(self) -> str:
        steps = " -> ".join(
            s["action"] + (f"({', '.join(f'{k}={v}' for k, v in s['args'].items())})"
                           if s["args"] else "")
            for s in self.path) or "(the initial state itself)"
        doors = (f"exits: {', '.join(self.exits)} — every one leads further from home"
                 if self.exits else "no action is enabled at all")
        return f"no way home after {steps} in state {self.state} ({doors})"


@dataclass
class Escape:
    model: str
    model_sha256: str
    home: str
    states_explored: int
    home_states: int
    verdict: str                        # 'proved' | 'refuted' | 'home-unreachable'
    stranded: list[Stranded] = field(default_factory=list)


def escapes(tree: Quern | TreeStore, path: str, home: str,
            cap: int = DEFAULT_CAP) -> Escape:
    """Check that every reachable state of the model at `path` can reach a state
    satisfying `home` (an expr over the state vars, e.g. "surface == 'board'")."""
    node, variables, actions, _ = _load(tree, path)
    order = [name for name, _, _ in variables]
    domains = {name: dom for name, dom, _ in variables}
    home_expr = _compile(home, f"home '{home}'")

    init = {name: i for name, _, i in variables}
    init_key = tuple(init[n] for n in order)
    parents: dict[tuple, tuple | None] = {init_key: None}
    incoming: dict[tuple, list[tuple]] = {init_key: []}
    exits: dict[tuple, list[str]] = {}
    homes: list[tuple] = []

    frontier = [init_key]
    explored = 0
    while frontier:
        nxt: list[tuple] = []
        for key in frontier:
            explored += 1
            state = dict(zip(order, key))
            if home_expr({**state, **_LITERALS}):
                homes.append(key)
            enabled: list[str] = []
            for action in actions:
                for binding in action.bindings:
                    env = {**state, **binding, **_LITERALS}
                    if not action.guard(env):
                        continue
                    enabled.append(action.id)
                    succ = dict(state)
                    for var, expr in action.updates:
                        value = expr(env)
                        if isinstance(value, float) and value.is_integer():
                            value = int(value)
                        if value not in domains[var]:
                            raise ValueError(
                                f"action '{action.id}'"
                                f"{f' with {binding}' if binding else ''} drives "
                                f"'{var}' to {value!r}, outside its domain — guard "
                                "the action or widen the domain")
                        succ[var] = value
                    succ_key = tuple(succ[n] for n in order)
                    if succ_key not in parents:
                        if len(parents) >= cap:
                            raise ValueError(
                                f"state space exceeds {cap} states; refine the model "
                                "or raise the cap — a partial walk is not a proof")
                        parents[succ_key] = (key, {"action": action.id,
                                                   "args": binding})
                        incoming[succ_key] = []
                        nxt.append(succ_key)
                    incoming[succ_key].append(key)
            exits[key] = sorted(set(enabled))
        frontier = nxt

    sha = _model_sha256(node)
    if not homes:
        return Escape(model=node.id, model_sha256=sha, home=home,
                      states_explored=explored, home_states=0,
                      verdict="home-unreachable")

    # The backward walk: everything that can reach home, over reversed edges.
    can_return: set[tuple] = set(homes)
    back = list(homes)
    while back:
        nxt_back: list[tuple] = []
        for key in back:
            for pred in incoming[key]:
                if pred not in can_return:
                    can_return.add(pred)
                    nxt_back.append(pred)
        back = nxt_back

    def _replay(key: tuple) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        while parents[key] is not None:
            key, step = parents[key]
            steps.append(step)
        return list(reversed(steps))

    # Stranded, shortest witness first — parents holds BFS-minimal paths already.
    stranded = [Stranded(path=_replay(k), state=dict(zip(order, k)), exits=exits[k])
                for k in parents if k not in can_return]
    stranded.sort(key=lambda s: len(s.path))

    return Escape(model=node.id, model_sha256=sha, home=home,
                  states_explored=explored, home_states=len(homes),
                  verdict="refuted" if stranded else "proved", stranded=stranded)
