"""model/prove: real proof over the turnstile, and every refusal by name.

The fixtures are the published package's own turnstile — the checker is tested against the
exact model every consumer of semantic-model@0.1.0 reads first. What is asserted exactly
(state counts, action sequences, digests) is asserted exactly on purpose: the checker's
determinism is a contract, and a drifting counterexample would be a breach even if it were
still a correct one.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import quern.grounding  # noqa: F401 — the gate rule's natives, for the composition test
from quern import Node, Quantity, Quern, Rule, load_blob, run_rules
from quern.library import consume

import epure.prove  # noqa: F401 — the door: registers the model/prove native
from epure.package import EXAMPLES
from epure.prove import attest, prove

_ROOT = Path(__file__).resolve().parents[1]


def _turnstile() -> Quern:
    tree = Quern()
    tree.root.children = [EXAMPLES[0].model_copy(deep=True)]
    return tree


# --- the true invariant proves ---------------------------------------------------


def test_the_turnstile_proves():
    proof = prove(_turnstile(), "turnstile")
    assert proof.verdict == "proved"
    assert proof.invariants == ["no-free-entry"]
    assert proof.violations == []
    # The reachable space is the strict coin/push alternation up to the bound — seven
    # states, not the 32 the domains span. Exact on purpose: determinism is a contract.
    assert proof.states_explored == 7


def test_the_artifact_is_emitted_and_its_digest_is_stable(tmp_path):
    q1 = attest(_turnstile(), "turnstile", tmp_path, ref="turnstile@fixture")
    q2 = attest(_turnstile(), "turnstile", tmp_path, ref="turnstile@fixture")
    assert q1.source == q2.source, "same model, same artifact — or the artifact is noise"
    assert q1.grounded and q1.provenance == "proved" and q1.value == 1
    sha = q1.source.removeprefix("artifact://")
    artifact = json.loads(load_blob(tmp_path, sha))
    assert artifact["verdict"] == "proved"
    assert artifact["model"] == "turnstile@fixture"
    assert artifact["checker"].startswith("epure/prove@")
    assert artifact["invariants"] == ["no-free-entry"]


# --- a broken invariant yields the minimal counterexample -------------------------


def test_a_broken_invariant_names_its_minimal_path():
    tree = _turnstile()
    tree.get("turnstile/no-free-entry").payload["expr"] = "entries <= 1"
    proof = prove(tree, "turnstile")
    assert proof.verdict == "refuted"
    v = proof.violations[0]
    assert v.invariant == "no-free-entry"
    # BFS makes this the shortest road to entries == 2 — coin, push, coin, push.
    assert [s["action"] for s in v.path] == [
        "insert-coin", "push-through", "insert-coin", "push-through"]
    assert v.state == {"state": "locked", "coins": 2, "entries": 2}
    assert "no-free-entry" in v.replay()


def test_attest_refuses_a_refuted_model(tmp_path):
    tree = _turnstile()
    tree.get("turnstile/no-free-entry").payload["expr"] = "entries <= 1"
    with pytest.raises(ValueError, match="refusing to attest"):
        attest(tree, "turnstile", tmp_path)
    assert not any(tmp_path.iterdir()), "a refuted model must leave no artifact behind"


# --- bounds, never silent ----------------------------------------------------------


def test_the_cap_refuses_loudly():
    with pytest.raises(ValueError, match="state space exceeds 3"):
        prove(_turnstile(), "turnstile", cap=3)


def test_an_out_of_domain_update_is_a_refusal_not_an_implicit_guard():
    tree = _turnstile()
    # Drop the author's own bound from the guard: the fourth coin now drives coins to 4.
    tree.get("turnstile/insert-coin").payload["guard"] = "state == 'locked'"
    with pytest.raises(ValueError, match="drives 'coins' to 4"):
        prove(tree, "turnstile")


def test_malformed_models_are_refused_by_name():
    bad_init = _turnstile()
    bad_init.get("turnstile/coins").payload["init"] = 9
    with pytest.raises(ValueError, match="init 9 is outside"):
        prove(bad_init, "turnstile")

    bad_arg = _turnstile()
    bad_arg.get("turnstile/insert-coin").payload["args"] = {"who": "int"}
    with pytest.raises(ValueError, match="cannot enumerate"):
        prove(bad_arg, "turnstile")

    not_a_model = _turnstile()
    with pytest.raises(ValueError, match="not a model"):
        prove(not_a_model, "turnstile/coins")


# --- the native, behind solve() -----------------------------------------------------


def test_the_native_answers_in_the_rule_language():
    tree = _turnstile()
    tree.rules.append(Rule(name="the-model-is-proven", kind="model",
                           expr="solve('model/prove', self) == 0"))
    results = {r.rule: r for r in run_rules(tree)}
    assert results["the-model-is-proven"].ok

    tree.get("turnstile/no-free-entry").payload["expr"] = "entries <= 1"
    results = {r.rule: r for r in run_rules(tree)}
    assert not results["the-model-is-proven"].ok


# --- the composition that is the acceptance test -------------------------------------
#
# A proof artifact grounds evidence, and a gate refuses anything ungrounded — with NO new
# rule. The whole reason the artifact is a Quantity is that ledger@'s existing
# nothing-unsound-passes-a-gate already knows how to judge it.


def _gated(proof: Quantity) -> Quern:
    lib, refs = consume(_ROOT, os.environ.get("QUERN_REGISTRY", _ROOT.parent / "quern-registry"))
    tree = Quern(packages=[next(r for r in refs if r.name == "ledger")])
    tree = lib.effective(tree)
    tree.root.children = [
        Node(id="charter-wall-holds", kind="claim",
             name="The charter wall invariant is proven over the model",
             params={"proof": proof}),
        Node(id="release", kind="gate", links={"admits": ["charter-wall-holds"]}),
    ]
    return tree


def test_a_proof_artifact_passes_the_gate(tmp_path):
    proof = attest(_turnstile(), "turnstile", tmp_path)
    results = {(r.rule, r.node): r for r in run_rules(_gated(proof))}
    assert results[("nothing-unsound-passes-a-gate", "release")].ok


def test_a_proof_owed_is_refused_by_the_gate():
    owed = Quantity(value=1, unit="proof", provenance="proved", grounded=False,
                    source="proof owed — claimed, never run")
    results = {(r.rule, r.node): r for r in run_rules(_gated(owed))}
    assert not results[("nothing-unsound-passes-a-gate", "release")].ok
