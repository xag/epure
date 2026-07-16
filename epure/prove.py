"""model/prove v0 — exhaustive explicit-state checking of finite models.

The design-time half of the substrate's split: **model |= invariants, established over every
reachable state**, once, and carried as a grounded proof artifact. This is proof in the
mathematical sense — the checker visits each state the model can reach and evaluates every
invariant there — not the witnessed-cases sense of the package publish gate. The 0.1.0
meta-vocabulary restricts state-vars to finite domains precisely so this checker can be this
simple and this honest: BFS from the initial state, successors are every action whose guard
holds over every binding of its args, invariants judged at discovery.

Importing this module is the door: it registers the `model/prove` native and nothing else.
The native returns a violation COUNT so the canonical rule shape is
`solve('model/prove', self) == 0` — the same composition every counting contract uses.
Everything else the checker knows (the counterexample path, the states explored) is on the
`Proof` that `prove()` returns, and the artifact `attest()` emits.

Three commitments, each a diagnostic and never a shrug:

- **Bounds, never silent.** A hard cap on explored states (default 1e6). Exceeding it is a
  refusal — "state space exceeds N; refine the model or raise the cap" — never a silently
  partial pass that reads like a proof.
- **Purity.** No clock, no randomness, no IO in the walk. Iteration order is fixed (actions
  in document order, bindings in domain order), so the same model yields the same verdict and
  the same counterexample, byte for byte. `attest` is the one function that writes, and only
  into the content-addressed store.
- **One grammar, one evaluator.** Guards, updates and invariants are exprs in the quern rule
  grammar, and they are evaluated by quern's own evaluator — imported from the pinned rev,
  tokens cached per expr. Re-implementing the grammar here would create a second meaning for
  the same text, and the two would drift; a checker whose reading of an expr can disagree with
  the rule language it serves proves nothing.

Transition semantics (journaled in `epure.tree`): an action's updates all read the PRE-state
and apply simultaneously, and an update that drives a variable out of its declared domain is
a refusal naming the action and binding — not an implicit guard, not a clamp. The domain is a
claim about the model; a transition that breaks it is a modeling error the author must hear
about, because an implicit guard would silently prune exactly the behaviors the author most
needs to know exist.
"""

from __future__ import annotations

import hashlib
import json
from itertools import product
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel, Field

from quern import Node, Quantity, Quern, TreeStore, get_node, register_native
# The store write is reached through the module, not a bound name, so the boundary's
# declaration of `quern.solver.save_blob` stays true when a recorder patches the seam.
from quern import solver as _store
# The rule grammar's reference evaluator, at the rev pyproject pins. Private on purpose —
# nothing else should evaluate exprs — and reached here because the alternative is a second
# implementation of the same grammar, which is how one text acquires two meanings.
from quern.tree import _parse_or, _tokenize

from epure import __version__

DEFAULT_CAP = 1_000_000
CHECKER = f"epure/prove@{__version__}"

# The evaluator resolves function names from an env and everything else from variables.
# The walk offers no bridge to content and no context — a guard that needs the world is
# not a guard over the model — so the env is arithmetic helpers and nothing more.
_ENV: dict[str, Any] = {"abs": abs, "min": min, "max": max,
                        "sum": lambda xs: sum(xs), "len": lambda xs: len(xs)}
# The grammar has no boolean literals (rules never needed them; a bool state-var's updates
# do), so `true` and `false` are bound as variables in every evaluation.
_LITERALS = {"true": True, "false": False}


class Violation(BaseModel):
    """One invariant, refuted: the minimal action path from init to a reachable state where
    its expr is false — a counterexample a person can replay against the model by hand."""

    invariant: str
    note: str = ""
    path: list[dict[str, Any]] = Field(default_factory=list)  # [{"action", "args"}]
    state: dict[str, Any] = Field(default_factory=dict)

    def replay(self) -> str:
        steps = " -> ".join(
            s["action"] + (f"({', '.join(f'{k}={v}' for k, v in s['args'].items())})"
                           if s["args"] else "")
            for s in self.path) or "(the initial state itself)"
        return (f"invariant '{self.invariant}' fails after {steps} "
                f"in state {self.state}")


class Proof(BaseModel):
    """What one exhaustive run established. `verdict` is 'proved' only when every invariant
    held in every reachable state; anything less carries its counterexamples."""

    model: str
    model_sha256: str
    checker: str = CHECKER
    states_explored: int
    invariants: list[str]
    verdict: str  # "proved" | "refuted"
    violations: list[Violation] = Field(default_factory=list)


def _compile(src: str, where: str) -> Callable[[dict[str, Any]], Any]:
    """One expr, tokenized once, evaluated many times — the walk's inner loop."""
    try:
        tokens = _tokenize(src)
    except ValueError as e:
        raise ValueError(f"{where}: {e}") from e

    def run(variables: dict[str, Any]) -> Any:
        value, pos = _parse_or(tokens, 0, _ENV, variables)
        if pos != len(tokens):
            raise ValueError(f"{where}: unexpected '{tokens[pos][1]}'")
        return value

    return run


def _domain(spec: dict[str, Any] | str, where: str) -> list[Any]:
    """The finite value list a type spec declares. A state-var's payload and an action arg's
    type share this shape; a spec this function cannot enumerate is a refusal, because an
    unenumerable domain is exactly what 0.1.0 exists to refuse."""
    if spec == "bool" or (isinstance(spec, dict) and spec.get("type") == "bool"):
        return [False, True]
    if isinstance(spec, dict) and spec.get("type") == "enum":
        dom = spec.get("domain")
        if not isinstance(dom, list) or not dom:
            raise ValueError(f"{where}: enum declares no domain")
        return list(dom)
    if isinstance(spec, dict) and spec.get("type") == "int":
        dom = spec.get("domain") or {}
        lo, hi = dom.get("min"), dom.get("max")
        if not (isinstance(lo, int) and isinstance(hi, int) and lo <= hi):
            raise ValueError(f"{where}: an int domain is {{'min': n, 'max': n}} with "
                             "min <= max — the bound is the price of the proof")
        return list(range(lo, hi + 1))
    raise ValueError(f"{where}: cannot enumerate type {spec!r} — 0.1.0 knows bool, "
                     "bounded int and enum, and nothing else is finite by declaration")


class _Action(BaseModel):
    model_config = {"arbitrary_types_allowed": True}
    id: str
    guard: Callable[[dict[str, Any]], Any]
    updates: list[tuple[str, Callable[[dict[str, Any]], Any]]]
    bindings: list[dict[str, Any]]  # every assignment of args to their domains


def _load(tree: Quern | TreeStore, path: str) -> tuple[Node, list[tuple[str, list[Any], Any]],
                                                        list[_Action],
                                                        list[tuple[str, str, Callable]]]:
    """The model node compiled for the walk: (node, vars, actions, invariants). Every
    malformation is refused here, by name, before a single state is explored."""
    node = get_node(tree, path)
    if node is None:
        raise ValueError(f"no node at '{path}'")
    if node.kind != "model":
        raise ValueError(f"'{path}' is a '{node.kind or '(bare)'}', not a model — "
                         "model/prove proves models")

    variables: list[tuple[str, list[Any], Any]] = []  # (name, domain, init)
    seen: set[str] = set()
    for c in node.children:
        if c.kind != "state-var":
            continue
        if c.id in seen:
            raise ValueError(f"state-var '{c.id}' is declared twice — one name, one variable")
        seen.add(c.id)
        dom = _domain(c.payload, f"state-var '{c.id}'")
        init = c.payload.get("init")
        if init not in dom:
            raise ValueError(f"state-var '{c.id}': init {init!r} is outside its own domain")
        variables.append((c.id, dom, init))

    actions: list[_Action] = []
    for c in node.children:
        if c.kind != "action":
            continue
        args = c.payload.get("args") or {}
        names = list(args)
        domains = [_domain(args[n], f"action '{c.id}' arg '{n}'") for n in names]
        bindings = [dict(zip(names, combo)) for combo in product(*domains)]
        guard_src = c.payload.get("guard", "")
        actions.append(_Action(
            id=c.id,
            # an absent guard means always enabled: a transition with no precondition is a
            # legitimate model, and demanding '1 == 1' boilerplate invites copy-paste noise
            guard=(_compile(guard_src, f"action '{c.id}' guard") if guard_src
                   else (lambda _env: True)),
            updates=[(u["var"], _compile(u["expr"], f"action '{c.id}' update of '{u['var']}'"))
                     for u in c.payload.get("updates") or []],
            bindings=bindings))
        for var, _ in actions[-1].updates:
            if var not in seen:
                raise ValueError(f"action '{c.id}' updates '{var}', which no state-var "
                                 "declares — a transition cannot write outside the state")

    invariants = [(c.id, c.payload.get("note", ""),
                   _compile(c.payload.get("expr", ""), f"invariant '{c.id}'"))
                  for c in node.children if c.kind == "invariant"]
    return node, variables, actions, invariants


def prove(tree: Quern | TreeStore, path: str, cap: int = DEFAULT_CAP) -> Proof:
    """Exhaustively check every invariant of the model at `path` over its reachable states.

    BFS from the initial state, so each violation's counterexample path is minimal. The walk
    continues past a violating state — a safety violation does not halt the model, and the
    author deserves every refuted invariant in one run, each with its own shortest path.
    Exceeding `cap` raises; a partial walk must never be mistaken for a proof.
    """
    node, variables, actions, invariants = _load(tree, path)
    order = [name for name, _, _ in variables]
    domains = {name: dom for name, dom, _ in variables}

    def check(state: dict[str, Any], key: tuple) -> None:
        env = {**state, **_LITERALS}
        for inv, note, expr in invariants:
            if inv in refuted:
                continue
            if not expr(env):
                refuted[inv] = Violation(invariant=inv, note=note,
                                         path=_replay(key), state=dict(state))

    def _replay(key: tuple) -> list[dict[str, Any]]:
        steps: list[dict[str, Any]] = []
        while parents[key] is not None:
            key, step = parents[key]
            steps.append(step)
        return list(reversed(steps))

    init = {name: i for name, _, i in variables}
    init_key = tuple(init[n] for n in order)
    parents: dict[tuple, tuple | None] = {init_key: None}
    refuted: dict[str, Violation] = {}
    frontier = [init_key]
    check(init, init_key)

    explored = 0
    while frontier:
        nxt: list[tuple] = []
        for key in frontier:
            explored += 1
            state = dict(zip(order, key))
            for action in actions:
                for binding in action.bindings:
                    env = {**state, **binding, **_LITERALS}
                    if not action.guard(env):
                        continue
                    succ = dict(state)
                    for var, expr in action.updates:  # all read the pre-state
                        value = expr(env)
                        if isinstance(value, float) and value.is_integer():
                            value = int(value)  # the grammar's numbers are floats
                        if value not in domains[var]:
                            raise ValueError(
                                f"action '{action.id}'"
                                f"{f' with {binding}' if binding else ''} drives "
                                f"'{var}' to {value!r}, outside its domain — guard the "
                                "action or widen the domain; the checker will not "
                                "invent an implicit guard for you")
                        succ[var] = value
                    succ_key = tuple(succ[n] for n in order)
                    if succ_key in parents:
                        continue
                    if len(parents) >= cap:
                        raise ValueError(
                            f"state space exceeds {cap} states; refine the model or "
                            "raise the cap — a partial walk is not a proof")
                    parents[succ_key] = (key, {"action": action.id, "args": binding})
                    check(succ, succ_key)
                    nxt.append(succ_key)
        frontier = nxt

    return Proof(
        model=node.id,
        model_sha256=_model_sha256(node),
        states_explored=explored,
        invariants=[inv for inv, _, _ in invariants],
        verdict="refuted" if refuted else "proved",
        violations=[refuted[inv] for inv, _, _ in invariants if inv in refuted])


def _model_sha256(node: Node) -> str:
    """The model's content identity — canonical serialization, not file bytes, for exactly
    the reason `package_digest` is: transport mangles bytes without changing meaning."""
    return hashlib.sha256(node.model_dump_json(indent=2, exclude_none=True)
                          .encode("utf-8")).hexdigest()


def attest(tree: Quern | TreeStore, path: str, blob_dir: Path | str,
           ref: str | None = None, cap: int = DEFAULT_CAP) -> Quantity:
    """Prove, and carry the proof: the canonical artifact into the content-addressed store,
    a grounded Quantity back — the shape a gate composes with.

    Refuses on anything short of 'proved': an artifact is a claim other trees will pin their
    releases on, and emitting one for a refuted model would be manufacturing evidence. The
    returned Quantity (`provenance='proved'`, `grounded=True`, `source='artifact://<sha>'`)
    is what lets a verdict resting on this proof pass `ledger@`'s
    nothing-unsound-passes-a-gate with no new rule — that composition is the whole point.
    `ref` names the model as consumers know it (name@version); it defaults to the node id.
    """
    proof = prove(tree, path, cap=cap)
    if proof.verdict != "proved":
        raise ValueError(
            "refusing to attest: " + "; ".join(v.replay() for v in proof.violations))
    artifact = {"model": ref or proof.model, "model_sha256": proof.model_sha256,
                "checker": proof.checker, "states_explored": proof.states_explored,
                "invariants": proof.invariants, "verdict": proof.verdict}
    data = json.dumps(artifact, sort_keys=True, separators=(",", ":")).encode("utf-8")
    sha = _store.save_blob(Path(blob_dir), data)
    return Quantity(value=1, unit="proof", provenance="proved", grounded=True,
                    source=f"artifact://{sha}",
                    note=f"{artifact['model']}: {len(proof.invariants)} invariant(s) over "
                         f"{proof.states_explored} reachable state(s), {proof.checker}")


def prove_count(tree: Quern | TreeStore, path: str, cap: int = DEFAULT_CAP) -> float:
    """The native: how many invariants of the model at `path` are refuted. Counts, not
    booleans — a rule wants `== 0`, a diagnostic wants to know how many."""
    return float(len(prove(tree, path, cap=int(cap)).violations))


register_native("model/prove", prove_count)
