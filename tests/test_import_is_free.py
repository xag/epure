"""`import epure` pulls in no domain.

bom's own rule — a plain import installs no meaning — applies to every package built on it,
and it is worth a test rather than a comment because the failure is silent: someone adds a
convenience re-export to `epure/__init__.py`, every consumer starts paying for a vocabulary
and a set of natives it never asked for, and nothing goes red. The cost lands on whoever
imports the library for one small thing, which is exactly who cannot see it.

The natives (`model/licensed`, `model/total`, `model/refines`, `model/prove`) will register
through an explicit door, the way `geometry` does — importing the module that owns them. This
test is what keeps that door from drifting up into the top-level import.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap


def _in_a_fresh_interpreter(source: str) -> str:
    """This cannot be asserted in-process: pytest has already imported half the world."""
    proc = subprocess.run([sys.executable, "-c", textwrap.dedent(source)],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc.stdout.strip()


def test_importing_epure_does_not_even_pull_in_the_substrate():
    out = _in_a_fresh_interpreter("""
        import sys
        import epure
        leaked = sorted(m for m in sys.modules if m == "bom" or m.startswith("bom."))
        print(",".join(leaked))
    """)
    assert out == "", f"`import epure` dragged in {out} — the domain must arrive by a door"


def test_importing_epure_registers_no_natives():
    out = _in_a_fresh_interpreter("""
        import epure
        from bom.tree import NATIVE
        print(",".join(sorted(n for n in NATIVE if n.startswith("model/"))))
    """)
    assert out == "", f"`import epure` registered {out} before anyone asked for it"
