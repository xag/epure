"""The conformance driver: confront an app's tapes with its model, and say red or green.

`epure.conformance` answers three questions about ONE slice — licensed, total, refines — and
`epure.behavior` five more: effect, faithful, frame, refusal and agrees — the conduct laws held
against what the act actually wrote and read back, by presence and, where a state-var projects,
by value. This is the harness around all eight: walk an app's tape
directories, judge each tape, print one screen, and leave a digest-bearing receipt a ledger gate
can ground on. It is the part every adopter needs and none of them should write twice.

THE CONDUCT CHECKS ride the same gate as refinement: a class held to refinement is held to the
laws, because both are claims about a tape built to be answerable. A model that declares no
doors answers 0 to all four, vacuously — `conduct/checkable` on the model is what says so, and
it is the adopter's model test to run it, not this harness's per-tape business. A conduct note
(a read that never came) is printed, never counted: a green resting on silence is visible as
such.

It was written twice already — once, in chores, as `tools/conformance.py`. That file was 351
lines of which the app-shaped part was five constants: the model, its package name, the tape
classes, the totality budget, and where the receipt goes. Everything else was machinery. This
module is that machinery with the constants lifted into `Suite`, and chores' copy is now a
config block over it. Extracting it was xag/epure#15's actual content, whose stated goal — that
a second app adopt the pipeline — turned out to be blocked on something else entirely (see the
note at the end of this docstring).

WHAT A CLASS IS, and it is the one idea an adopter has to hold. Tapes come in kinds that are
held to different bars. chores has two: a FLIGHT is a scripted journey whose whole job is to be
a legal path of the model, so it is gated on refinement and on a totality ratchet; a SCENE is a
recording of real use, which cannot refine until the model can bind a real household's ids, so
it is held to licensing alone and its other two reds are carried as ledger debts. An adopter
with one kind of tape passes one class. The gate lives in `Verdict.red()` and reads the class,
so what a tape is held to is data rather than a branch.

THE TOTALITY RATCHET is a high-water mark, not a target: `budget[stem]` is what that tape's
unmodeled traffic measures TODAY. Adding unmodeled behaviour to a path costs a red; closing an
instrumentation gap shows up as a number going down rather than as a feeling. A gated tape with
no budget entry is red on purpose — a missing number must not read as zero.

VACUITY IS A FAILURE, not a pass, and this is the subtlest thing here. A tape that claims
nothing refines perfectly, because refinement has nothing to refuse. `bound` counts only the
acts that bind an argument — the only claims refinement can actually convict — so a gated tape
whose `bound` is zero is red however green its three numbers look.

THE RECEIPT names the SHA-256 of every tape it judged. A receipt saying "green" is worth
nothing on its own; anyone can write one. It is worth something because a ledger gate can ask
whether the tapes on disk today are the tapes this verdict is about — edit a tape and its digest
moves and the receipt stops grounding anything. The model version is read off `quern.lock`
rather than typed: chores typed it until 0.4.0 and it named the wrong version for a whole minor
series, which is the one thing a receipt must never do.

ON THE SECOND ADOPTION. #15 asked for this so that an app which did not grow the tooling could
walk the path. That app does not exist yet, and the blocker is not here: of the estate's
candidates, chores emits 16 `span()`/`note()` call sites and its tapes carry semantic events,
while home and korean-gpt-coach emit ZERO and their tapes contain none. Without testimony there
is no semantic trace — refinement has no span sequence, licensing has no claims, and totality
reports every raw event as unenclosed. Generalizing the harness was worth doing and does not
unblock anything on its own: what a second app needs first is instrumentation, which is its
own work in its own repo.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Sequence

from quern import Node, Quern

from epure.behavior import agrees, effect, faithful, frame, refusal
from epure.conformance import licensed, refines, total
from epure.tape import import_scenario

_CHECKS: tuple[tuple[str, Callable], ...] = (
    ("licensed", licensed), ("total", total), ("refines", refines),
    ("effect", effect), ("faithful", faithful), ("frame", frame), ("refusal", refusal),
    ("agrees", agrees))
_CONDUCT = ("effect", "faithful", "frame", "refusal", "agrees")


@dataclass(frozen=True)
class TapeClass:
    """One kind of tape and what it is held to."""

    directory: Path
    refines_gated: bool
    #: Prose for the report header — what this class answers for, in the adopter's words.
    held: str = ""


@dataclass(frozen=True)
class Suite:
    """One app's conformance configuration: the five things that are not machinery."""

    model: Node                          # the semantic model's root node
    model_name: str                      # its package name — the `model` link and the lock pin
    classes: dict[str, TapeClass]
    root: Path                           # the repo root: quern.lock, and relative printing
    budget: dict[str, int] = field(default_factory=dict)
    receipt: Path | None = None          # None = this app leaves no receipt
    prog: str = "conformance"

    @property
    def bound_kinds(self) -> set[str]:
        """The event-kinds that carry an argument, READ OFF THE MODEL rather than restated.

        A copy of this list would be a second source of truth, and the second source is always
        the one that is wrong. These are the only claims that can bind a value outside a
        declared domain, which makes them the only claims refinement can actually convict."""
        return {c.id for c in self.model.children
                if c.kind == "event-kind" and (c.payload.get("args") or {})}


def _ascii(s: str) -> str:
    """épure speaks in em-dashes; this prints to a cp1252 console, which raises on the first
    one. Losing the report to an encoding error is worse than losing the punctuation."""
    return s.encode("ascii", "replace").decode("ascii")


class Verdict:
    """One tape's three answers, plus the act counts that stop a silence reading as a pass."""

    def __init__(self, tape: Path, kind: str, suite: Suite):
        self.tape = tape
        self.name = tape.stem
        self.kind = kind
        self.suite = suite
        self.acts = 0
        self.bound = 0
        self.checks: dict[str, tuple[int, str]] = {}
        self.notes: dict[str, int] = {}
        self.error = ""

    @property
    def vacuous(self) -> bool:
        """Refinement stopped at no act because there was no act to stop at.

        `acts` is not the test: a tape can carry six claims that all bind nothing and sail
        through refinement having been asked nothing. Only an arg-carrying claim can be
        refuted, so only those count."""
        return self.bound == 0

    def red(self) -> list[str]:
        """What this tape is failing, given what its class is held to. The gate, in one place."""
        if self.error:
            return ["the checks could not run"]
        bad = []
        if self.checks["licensed"][0]:
            bad.append("licensing")
        if self.suite.classes[self.kind].refines_gated:
            if self.checks["refines"][0]:
                bad.append("refinement")
            # A tape that claims nothing refines perfectly and proves nothing. For a class
            # whose entire job is to refine, that is a failure, not a pass.
            if self.vacuous:
                bad.append("vacuity (a tape that emits no act)")
            budget = self.suite.budget.get(self.name)
            if budget is None:
                bad.append("no totality budget (add one, with a reason)")
            elif self.checks["total"][0] > budget:
                bad.append(f"totality ratchet ({self.checks['total'][0]} > {budget})")
            # The laws: what the act declared it does, the world shows; nothing else moved.
            for law in _CONDUCT:
                if self.checks[law][0]:
                    bad.append(f"conduct/{law}")
        return bad


def judge(suite: Suite, tape: Path, kind: str) -> Verdict:
    """Import one tape, confront it with the model, and read the three verdicts off it."""
    v = Verdict(tape, kind, suite)
    session = import_scenario(tape)
    # The importer hardcodes the session's id to "session" regardless of filename, so importing
    # two tapes into one tree would collide on the path. Naming it for the tape is what lets the
    # report say which tape a diagnostic came from.
    session.id = tape.stem
    session.links = {"model": [suite.model_name]}

    tree = Quern()
    tree.root.children = [suite.model.model_copy(deep=True), session]

    bound_kinds = suite.bound_kinds

    def tally(node) -> tuple[int, int]:
        acts = bound = 0
        for c in node.children:
            a, b = tally(c)
            acts += 1 + a
            bound += (1 if c.kind in bound_kinds else 0) + b
        return acts, bound

    for call in session.children:
        a, b = tally(call)
        v.acts += a
        v.bound += b

    for name, check in _CHECKS:
        try:
            got = check(tree, tape.stem, "model")
            first = got.diagnostics[0] if got.diagnostics else ""
            # The diagnostic is prefixed with the offending node's full tree path, which starts
            # with the tape name the report already prints in the margin.
            first = first[len(tape.stem) + 1:] if first.startswith(tape.stem + "/") else first
            v.checks[name] = (got.violations, first)
            if got.notes:
                v.notes[name] = len(got.notes)
        except Exception as e:                       # a broken link, a model that is not a model
            v.error = f"{type(e).__name__}: {e}"
            v.checks[name] = (-1, v.error)
    return v


def report(suite: Suite, verdicts: list[Verdict]) -> None:
    """Tape, three verdicts, first diagnostic. One screen, and ASCII — this prints to a Windows
    console under cp1252, which turns anything prettier into mojibake exactly when it matters."""
    for kind, cls in suite.classes.items():
        rows = [v for v in verdicts if v.kind == kind]
        if not rows:
            continue
        held = cls.held or ("licensed + refines + a totality ratchet + the conduct laws"
                            if cls.refines_gated else "licensed only")
        print(f"\n{kind}s ({len(rows)}) - held to: {held}")
        print("-" * 78)
        for v in sorted(rows, key=lambda r: r.name):
            lic, tot, ref = (v.checks[k][0] for k in ("licensed", "total", "refines"))
            budget = suite.budget.get(v.name)
            room = f"/{budget}" if budget is not None and cls.refines_gated else ""
            mark = "RED " if v.red() else "ok  "
            # `bound` next to `refines`, always and deliberately: refines=0 means nothing
            # without it, and a reader who has to go looking for the act count will not.
            print(f"  {mark}{v.name:<28} licensed={lic:<4} total={tot}{room:<8} "
                  f"refines={ref}  ({v.bound} of {v.acts} acts bind an arg"
                  f"{' - VACUOUS, it refines by saying nothing' if v.vacuous else ''})")
            # The laws on their own line: four counts, and the silences beside them.
            laws = " ".join(f"{law}={v.checks[law][0]}" for law in _CONDUCT)
            quiet = ", ".join(f"{n} {law} read(s) never came" for law, n in v.notes.items())
            print(f"      laws: {laws}{f'   [{quiet}]' if quiet else ''}")
            for check, _ in _CHECKS:
                n, first = v.checks[check]
                if n and first:
                    print(f"         {check}: {_ascii(first)[:150]}")


def write_receipt(suite: Suite, verdicts: list[Verdict], path: Path | None = None) -> None:
    """What was checked, against which tapes, and what they said — for a ledger to read.

    A ledger's gate does not take conformance on trust and usually cannot re-run it. So this run
    leaves evidence and the gate grounds a param on it — the same shape as every other grounded
    claim, and the reason a `nothing-unsound-passes-a-gate` rule can brake on conformance
    without knowing what conformance is.

    The digests are the load-bearing part, and they are why this file can be committed without
    becoming a lie. A receipt saying "green" is worth exactly nothing on its own: anyone can
    write one. It is worth something because it names the SHA-256 of every tape it judged, so
    the ledger can ask whether the tapes on disk today are the tapes this verdict is about.

    No timestamp. A time is not evidence of anything here — the digests already say precisely
    what this verdict covers — and a field that changes on every run is a field that puts a diff
    in every commit and teaches people to stop reading it.

    The model version is READ OFF `quern.lock`, not typed. chores typed it until 0.4.0 and it
    named `chores-model@0.2.0` through the whole of 0.3.0 — a receipt naming the wrong drawing,
    which is the one thing a receipt must never do. Now the string cannot drift from the pin
    because it IS the pin.
    """
    target = path or suite.receipt
    if target is None:
        return
    lock = json.loads((suite.root / "quern.lock").read_text(encoding="utf-8"))
    pin = next(r for r in lock["packages"] if r["name"] == suite.model_name)
    payload: dict[str, Any] = {
        "green": not any(v.red() for v in verdicts),
        "model": f"{pin['name']}@{pin['version']}",
        "checker": "epure/conformance",
        "tapes": [
            {
                "name": v.name,
                "kind": v.kind,
                "sha256": hashlib.sha256(v.tape.read_bytes()).hexdigest(),
                "acts": v.acts,
                "bound": v.bound,
                "licensed": v.checks["licensed"][0],
                "total": v.checks["total"][0],
                "refines": v.checks["refines"][0],
                "conduct": {law: v.checks[law][0] for law in _CONDUCT},
                "red": v.red(),
            }
            for v in sorted(verdicts, key=lambda r: (r.kind, r.name))
        ],
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(suite: Suite, argv: Sequence[str]) -> int:
    """The whole run: judge, report, receipt, exit code. An adopter's entry point is one line."""
    p = argparse.ArgumentParser(
        prog=suite.prog,
        description=f"Confront this app's tapes with {suite.model_name}.")
    p.add_argument("directory", nargs="*", type=Path,
                   help="tape directories. Default: every class below. A directory of "
                        "production tapes is a scene directory.")
    p.add_argument("--as", dest="kind", choices=sorted(suite.classes), default=None,
                   help="what class the given directories are. Required when naming a directory "
                        "explicitly: it decides what the tape is held to, and guessing that from "
                        "a path is how a production tape gets held to a flight's bar.")
    args = p.parse_args(list(argv))

    if args.directory:
        if not args.kind:
            p.error("--as is required when a directory is named")
        work = [(d, args.kind) for d in args.directory]
    else:
        work = [(Path(c.directory), k) for k, c in suite.classes.items()]

    # Only the full default run leaves a receipt. A run over somebody's production tapes is a
    # question being asked, not the app's own tapes being certified, and grounding the gate on
    # it would let an arbitrary directory decide whether the repo may ship.
    leave_receipt = not args.directory

    verdicts: list[Verdict] = []
    for directory, kind in work:
        if not directory.is_dir():
            print(f"no such directory: {directory}")
            return 2
        tapes = sorted(directory.glob("*.jsonl"))
        if not tapes:
            print(f"no tapes in {directory}")
            return 2
        for tape in tapes:
            verdicts.append(judge(suite, tape, kind))

    report(suite, verdicts)

    if leave_receipt and suite.receipt is not None:
        write_receipt(suite, verdicts)
        print(f"\nreceipt: {suite.receipt.relative_to(suite.root)} "
              f"(the ledger's gate grounds on this)")

    red = [v for v in verdicts if v.red()]
    print()
    if not red:
        print(f"{len(verdicts)} tape(s), conformance green.")
        return 0
    print(f"{len(red)} of {len(verdicts)} tape(s) RED.")
    print()
    for v in red:
        print(f"  {v.name}: {', '.join(v.red())}")
    print()
    print("A refinement red is never ambiguous: either the model is wrong (fix it, re-prove it)")
    print("or the code diverged (the diagnostic names the first illegal step). Decide which.")
    print("A conduct red names the act and the law: the world did not show what the act declared,")
    print("or something moved the act never claimed. Either the door is wrong or the code is.")
    return 1
