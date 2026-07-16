"""epure — what does it mean, and will it always hold.

An *épure* is the stonecutter's full-scale working drawing: the piece is proven against the
drawing before anything is cut. Here the drawing is a **semantic model** — a small, finite
mathematical object (state variables, actions with guards and updates, invariants) — and the
piece is a running program that testifies, on its own tape, which semantic acts it performed.

Verification then splits into two obligations of different character:

1. **model |= predicates** — proven once, at design time, exhaustively over every behavior of
   the model. Real proof, not sampling.
2. **code <= model** — never provable, so checked mechanically on *every* execution:
   refinement (the semantic trace is a legal path of the model), licensing (each semantic
   claim is justified by the raw boundary events beneath it), totality (no raw event escapes
   semantics).

A plain `import epure` pulls in no domain: no vocabulary is registered, no natives are
installed, nothing is read from disk. The subpackages are the doors — `epure.tree` for this
repo's own design ledger, `epure.tape` for the one IO seam, `epure.prove` for the design-time
checker, `epure.conformance` for the per-tape checks (importing either registers its
natives) — and each costs only what the caller asked for. The substrate learned this the hard way and it is not a style preference:
a library that installs meaning at import time makes every consumer pay for a domain it may
never touch.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = ["__version__"]
