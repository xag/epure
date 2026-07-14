"""The open-ready gate, exercised by what it must REFUSE.

A check that has only ever been seen green proves nothing — that is this estate's founding
scar, and it is not going to be reproduced inside the tool that exists to prevent it. bom's
publish gate makes the same demand of every package: a rule must ship the counter-example that
trips it, or it does not enter. Same discipline, same reason.

The offending strings are built from parts rather than written out. That is not cuteness: a
literal home path in this file would be a home path in this repo, the scanner would flag it —
correctly — and the obvious "fix" would be to exempt `tests/` from the scan, which is precisely
where anything real would then hide. Building them at runtime keeps the tree clean and the
scanner honest, and this comment is here so nobody later mistakes the indirection for a wart
and tidies it away.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from open_ready import ALLOWED_REPOS, ESTATE, _scan  # noqa: E402


def _findings(line: str) -> list[str]:
    out: list[str] = []
    _scan(line, "synthetic", out)
    return out


def test_it_is_green_on_what_belongs_here():
    for line in [
        f'bom = {{ git = "https://github.com/{ESTATE}/bom", rev = "4dd8328" }}',
        f"See https://github.com/{ESTATE}/flight-recorder for the tape's frozen shape.",
        f"{ESTATE}/bom-registry is the transport.",
        "      - uses: actions/checkout@v4",
        "Apache-2.0. (c) 2026 Xavier Grehant.",
    ]:
        assert not _findings(line), f"false positive on a legitimate line: {line}"


def test_it_refuses_a_consumer():
    """The load-bearing one. This substrate may name what it stands on; it may not name what
    stands on it, and the check must catch a consumer it has never heard of — which is every
    consumer, since it is an allowlist and the list is the dependencies."""
    invented = "a-project-that-uses-this"
    assert invented not in ALLOWED_REPOS
    assert _findings(f"Used in production by {ESTATE}/{invented}.")
    assert _findings(f"see https://github.com/{ESTATE}/{invented}/issues/4")


def test_it_refuses_a_home_directory():
    assert _findings("path = " + "C:" + chr(92) + "Users" + chr(92) + "someone" + chr(92) + "tapes")
    assert _findings("path = " + "/home/" + "someone" + "/tapes/flight.jsonl")


def test_it_refuses_an_email_address():
    assert _findings("contact " + "someone" + "@" + "example.com")


def test_it_refuses_something_shaped_like_a_credential():
    assert _findings("token = " + "ghp_" + "A" * 24)
    assert _findings("-----BEGIN " + "RSA PRIVATE KEY-----")


def test_a_clone_url_is_not_a_different_repo():
    """`.git` is not part of a repo's name, and neither is the comma after it in a sentence.
    A gate that goes red on a legitimate line is a gate people learn to ignore, and that is a
    slower, quieter failure than one that never fires at all."""
    assert not _findings(f"git clone https://github.com/{ESTATE}/epure.git")
    assert not _findings(f"It stands on {ESTATE}/bom, {ESTATE}/flight-recorder.")
