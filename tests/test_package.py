"""semantic-model is what the lock says it is, and it still demonstrates itself.

Two different failures are guarded here. The digest test catches DRIFT: someone edits
`epure/package.py` after publication, and the authored content quietly stops being the
content every consumer pins — the registry would refuse the republish, but nothing in this
repo would notice until then. The gate test catches ROT: the proof that held at publish time
is re-run on every CI pass, so a rule that decays into vacuity under a later refactor of the
substrate is caught here, not by the first consumer whose defect it waves through.
"""

from __future__ import annotations

from pathlib import Path

from quern.library import package_digest, read_lock, validate_package

from epure.package import SEMANTIC_MODEL_PACKAGE

_ROOT = Path(__file__).resolve().parents[1]


def test_the_pin_is_this_content():
    refs = {r.name: r for r in read_lock(_ROOT / "quern.lock")}
    assert "semantic-model" in refs, "semantic-model is not pinned in quern.lock"
    assert refs["semantic-model"].sha256 == package_digest(SEMANTIC_MODEL_PACKAGE), (
        "the authored package and the pinned digest disagree — epure/package.py has "
        "drifted from what was published. Versions are immutable: bump the version and "
        "republish; never edit a published meaning in place")


def test_the_package_still_demonstrates_itself(tmp_path):
    # requires=[] and no solvers, so no library and no blobs are needed: the whole gate
    # is the rules against their own examples and counter-examples.
    log = validate_package(SEMANTIC_MODEL_PACKAGE, tmp_path)
    assert any("3 rule(s) exercised" in line for line in log), log
    assert any("refuted by their counter-example" in line for line in log), log


def test_every_rule_carries_a_counter_example():
    """The gate tolerates a rule with no counter-example (it logs, it does not refuse).
    This package does not: a guard shipping without the evidence that it guards is the
    exact defect its own docstring warns about."""
    named = {r.name for r in SEMANTIC_MODEL_PACKAGE.rules}
    refuting = {ce.rule for ce in SEMANTIC_MODEL_PACKAGE.counter_examples}
    assert named == refuting, f"rules without a refutation: {sorted(named - refuting)}"
