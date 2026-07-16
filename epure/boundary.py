"""This repo's own nondeterminism boundary.

A program's execution is fully determined by its code plus its nondeterministic inputs. epure
has very few: it publishes packages to a registry, it reads packages back out of one, and it
reads tapes off the disk. Everything else here is a pure function of those answers — which is
the point, and the reason the boundary is worth declaring while it is still this thin. A
boundary declared on the day the repo is empty stays true; a boundary retrofitted after the
IO has spread is an archaeology exercise, and the practice exists because that archaeology is
how projects end up debugging by re-deriving what must have happened.

Nothing here is recorded by default: this declaration is the artifact, and an app (or a test)
that wants a tape of epure's own execution calls `flight_recorder.install(BOUNDARY, ...)` with
it. The library records and judges nothing on its own.
"""

from __future__ import annotations

from flight_recorder import Boundary

import quern.library
import quern.solver

from epure import tape


def boundary() -> Boundary:
    """The declaration. A function, not a module constant, because building it imports the
    modules it names — and `import epure` must stay free of everything (see `epure/__init__`)."""
    return Boundary(
        effects=[
            # Reading the registry, and writing to it. `publish` is where a claim leaves this
            # process and becomes something another project can pin, so it is the effect that
            # matters most: the proof gate runs inside it.
            (quern.library, ["consume", "sync", "read_lock", "write_lock"]),
            (quern.library.Library, ["publish", "get", "list"], {"method": True}),
            # The tapes. One function, by construction (see `epure.tape`).
            (tape, ["read_tape"]),
            # The blob store. Every content-addressed write — a proof artifact leaving
            # `epure.prove.attest`, a solver blob entering a library — lands through this
            # one function, declared at the module that owns it so patching the seam
            # catches every caller.
            (quern.solver, ["save_blob"]),
        ],
    )
