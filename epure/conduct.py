"""The conduct catalogue: the behavior laws, as content the effect kinds bind to.

The founder's example was «a value must be the same if it wasn't changed», and the point was
never that one rule — it was the family, and the census of families. The census here is not a
judgment call: Hughes's *How to Specify It!* enumerates the ways a property over an operation
can be written — "five different approaches to writing properties (invariants, postconditions,
metamorphic properties and the preservation of equivalence, inductive properties, and
model-based properties)" — and the nine families below are that enumeration folded onto what a
tape can witness: what a postcondition can say about an effect (it happened; it matches its
inputs; nothing else moved), what a metamorphic relation can say about repeats, inverses and
refusals, and what the model-based frame already owns (invariants live in semantic-model's own
`invariant` kind and are proved, not sampled — they are deliberately NOT a family here).

Binding is by inheritance, not template-stamping — the founder's fork, resolved: each law
names the generic effect kind it applies to (`creates`, `mutates`, `deletes`, `touches`,
declared by semantic-model@0.4.0 as action children), and an action inherits every law of the
effects it declares by declaring them, the way ledger@'s gate law binds every domain's gates.
Nothing is stamped per operation; templates survive only in the refuting examples the natives
will demand. And the catalogue is OPT-IN: semantic-model does not require effects to be
declared — adopting this catalogue is what makes the declaration a demand.

Five of the nine are now held against tapes by natives (`epure.behavior`): conduct/effect,
conduct/faithful, conduct/frame, conduct/refusal on a recorded run, conduct/checkable on the
model. Each law's payload names its `native`, or the `owed` reason the tape cannot witness it
yet — four families need two stretches of one tape compared (a repeat, a do/undo pair, two
identical pre-states, a read long after), and that is a named debt, not a check stretched until
it answers. The sightings below are real and from this estate's own record — a law that has
never caught anything is a law nobody should trust, and three of these families caught
something the same week they were named.
"""

from __future__ import annotations

from quern import KindDef, Node, Rule, SolverDef
from quern.library import CounterExample, Package
from quern.provenance import Quantity
from quern.tree import PackageRef


def _cited(source: str) -> Quantity:
    """A law somebody reputable has actually stated. Grounded: it may be acted on."""
    return Quantity(value=1, unit="law", provenance="cited", grounded=True, source=source)


def _uncited() -> Quantity:
    """A law nobody has been found to have stated. NOT deleted — carried, and visibly
    ungrounded, so a gate will not let it pass as settled: known-unsound, on purpose, with
    its cost stated rather than forgotten. Source it or drop it."""
    return Quantity(value=1, unit="law", provenance="asserted, uncited", grounded=False,
                    source="observed in practice; no authority found. Source it or drop it.")


def _law(law_id, name, authority, *, falsifier, triggers, citations=(), sightings=(), note="",
         meta=None, native="", owed=""):
    """`native` names the conduct contract that holds this law against a tape; `owed` says
    why none does yet. Exactly one of the two, always: a law is either checked or a debt."""
    assert bool(native) != bool(owed), law_id
    kids = []
    kids.append(Node(id=f"{law_id}--falsifier", kind="falsifier", payload={"claim": falsifier}))
    for i, t in enumerate(triggers):
        kids.append(Node(id=f"{law_id}--trigger-{i}", kind="trigger", payload={"when": t}))
    for i, (title, url, quote) in enumerate(citations):
        kids.append(Node(id=f"{law_id}--citation-{i}", kind="citation",
                         name=title, payload={"url": url, "quote": quote}))
    for i, (where, what) in enumerate(sightings):
        kids.append(Node(id=f"{law_id}--sighting-{i}", kind="sighting",
                         name=where, payload={"what": what}))
    payload = {"note": note} if note else {}
    payload.update({"native": native} if native else {"owed": owed})
    return Node(id=law_id, kind="law", name=name, payload=payload,
                params={"authority": authority}, children=kids,
                meta=meta or {})


# --- the citable package: the law shape, and the gates that keep it honest ------------
#
# The five kinds mirror craft@'s law shape deliberately — same names, same children — but
# they are NOT craft's kinds consumed: craft's `law` is defined as a claim about interface
# or copy, and stretching a KindDef's stated meaning to cover a second domain is the drift
# the registry exists to refuse. Two vocabularies, one shape, each saying what its laws are
# about; the day a third law domain arrives, the shape earns extraction into a package of
# its own and both supersede onto it.

CONDUCT_VOCABULARY = [
    KindDef(
        kind="law",
        description="A claim about how an OPERATION behaves — what its effect promises "
        "under reading back, repetition, inversion, refusal, replay and time — that holds "
        "across domains because it binds to the generic effect kinds "
        "(semantic-model@0.4.0's creates/mutates/deletes/touches, with doors since 0.5.0), never to any one "
        "operation. It carries an `authority` param, grounded when a reputable source has "
        "actually stated it and ungrounded when it is observation carried honestly as a "
        "debt.",
        links={"supersedes": "the law this one replaces, if any"},
    ),
    KindDef(
        kind="citation",
        description="Where the law actually comes from: a publisher, a title, a URL, and — "
        "the part that matters — the QUOTE. A citation without the words is a citation "
        "nobody can check, and an unfalsifiable appeal to authority is worse than an honest "
        "opinion.",
    ),
    KindDef(
        kind="falsifier",
        description="The tape that constitutes a violation: which effect declaration, which "
        "stretch of execution, what read disagrees. A behavior law whose breach no tape "
        "could exhibit is a taste, and tastes do not belong in a package.",
    ),
    KindDef(
        kind="trigger",
        description="The effect declaration that switches this law on. This is the "
        "inheritance seam: an action declares `creates`, and every law whose trigger names "
        "`creates` binds to it — the author writes what the operation does, and the laws "
        "arrive.",
    ),
    KindDef(
        kind="sighting",
        description="A real defect this law actually caught, in a real system, on a real "
        "tape. Evidence, not decoration: a law that has never caught anything is a law "
        "nobody should trust.",
    ),
]

CONDUCT_RULES = [
    Rule(
        name="a-law-can-be-violated-observably",
        kind="law",
        description="A law whose breach cannot be shown by a tape can never produce a "
        "verdict, and a verdict is the only thing a law is for.",
        expr="len(nodes('falsifier', self)) >= 1",
    ),
    Rule(
        name="a-law-is-switched-on-by-something",
        kind="law",
        description="Laws arrive because an effect declaration called for them. A law that "
        "applies to everything applies to nothing: it becomes a checklist item, and a "
        "checklist item is read once and never again.",
        expr="len(nodes('trigger', self)) >= 1",
    ),
    Rule(
        name="a-law-cites-a-source",
        kind="law",
        description="A law that cannot name who said it is a hypothesis. It may be carried, "
        "and it will be red, and that is the honest state of it — five of the nine families "
        "in the authoring repo are carried exactly so.",
        expr="len(nodes('citation', self)) >= 1",
    ),
]


HUGHES = ("John Hughes — How to Specify It! A Guide to Writing Properties of Pure Functions "
          "(Chalmers, 2020)")
HUGHES_URL = "https://research.chalmers.se/publication/517894/file/517894_Fulltext.pdf"
HUGHES_POSTCONDITION = ("after calling insert, then we should be able to find the key just "
                        "inserted, and any previously inserted keys with unchanged values")
RFC9110 = "IETF RFC 9110, HTTP Semantics — §9.2.2 Idempotent Methods"
RFC9110_URL = "https://www.rfc-editor.org/rfc/rfc9110.txt"


CONDUCT_LAWS = [

    # --- what the effect itself promises -----------------------------------------
    _law(
        "the-effect-is-shown",
        "What an action declares it does, the world shows afterward",
        _cited("Hughes 2020, postconditions: find the key just inserted"),
        falsifier="A tape where an action declaring `creates` or `mutates` completes and the "
                  "entity it names cannot be read back — or one declaring `deletes` completes "
                  "and the entity still shows.",
        triggers=["an action declares `creates` — the entity must be shown after",
                  "an action declares `mutates` — the entity must show as changed",
                  "an action declares `deletes` — inverted: the entity must NOT be shown"],
        citations=[(HUGHES, HUGHES_URL, HUGHES_POSTCONDITION)],
        note="The floor of every postcondition: the operation is not a no-op wearing a verb. "
             "Deletion inverts the check, which is why `deletes` is its own kind.",
        native="conduct/effect",
    ),
    _law(
        "the-effect-matches-its-inputs",
        "What was made from the inputs agrees with the inputs",
        _cited("Hughes 2020, postconditions: the key JUST inserted"),
        falsifier="A tape where the entity read back after the action disagrees with the "
                  "arguments the effect's `from` names — created with one value, shown with "
                  "another.",
        triggers=["an action declares `creates` or `mutates` with a non-empty `from`"],
        citations=[(HUGHES, HUGHES_URL, HUGHES_POSTCONDITION)],
        sightings=[
            ("surface-tape walker, 2026-08-18",
             "The walk deposited folded <details> content as visible text: the record "
             "disagreed with what the click had actually produced on screen, and two "
             "convictions and a fix-ruling were built on the lie before clean() learned "
             "to honor the fold."),
        ],
        note="Presence without fidelity is half a check: an object created is actually "
             "created, consistent with its inputs — the founder's own phrasing.",
        native="conduct/faithful",
    ),
    _law(
        "the-frame-holds",
        "A value is the same if it wasn't changed",
        _cited("Hughes 2020, postconditions: previously inserted keys with unchanged values"),
        falsifier="A tape where state outside the action's declared `touches` boundary differs "
                  "after the action from before it.",
        triggers=["an action declares `touches` — everything outside `only` is the frame"],
        citations=[(HUGHES, HUGHES_URL, HUGHES_POSTCONDITION)],
        sightings=[
            ("surface-tape walks, 2026-08-19",
             "An 'empty' walk read a seeded store: a server a previous run failed to kill "
             "was still holding port 8199, so state the walk never touched had been moved "
             "by something else — the frame assumption violated by an unowned writer, and "
             "the deposited walk was a lie until the PID was hunted down."),
            ("chores flights and scenes, first run of conduct/frame, 2026-08-20",
             "Two turn-done acts on the-rhythms-run and a chore-added on every scene wrote "
             "through app.storage.create to sent/second_settler and sent/second_chore — the "
             "#149 onboarding milestones, claimed and counted from inside the completion "
             "writer and the add (deliberately, to spare a round trip; #150 is the cost) and "
             "never in the drawing. The model's boundary was wrong, not the code: the doors "
             "are admitted on those acts now, with the finding on them (chores-model@0.12.0). "
             "Caught by the native, not by reading: the effect, faithfulness and refusal "
             "laws were green on the same tapes."),
        ],
        note="Inside a proved model the frame holds by construction — updates name every "
             "moving var. The law exists for tapes, where the real system writes.",
        native="conduct/frame",
    ),

    # --- what shape the effect has under algebra ----------------------------------
    _law(
        "twice-is-once",
        "Repeating an action whose repeat the model allows leaves the world as one did",
        _cited("RFC 9110 §9.2.2, Idempotent Methods"),
        falsifier="A tape where the same action, run twice with the same arguments, leaves a "
                  "different world than running it once — for an action the model re-admits "
                  "(its guard holds again after it fires).",
        triggers=["an action declares an effect and its guard can hold in its own post-state"],
        citations=[(RFC9110, RFC9110_URL,
                    "A request method is considered \"idempotent\" if the intended effect on "
                    "the server of multiple identical requests with that method is the same "
                    "as the effect for a single such request.")],
        note="Not every action is idempotent and the model already says which: a guard that "
             "refuses its own post-state (the turnstile's insert-coin when unlocked) exits "
             "the family; a guard that re-admits enters it.",
        owed="needs two consecutive acts with the same kind and data, the automaton's "
             "verdict that the guard re-admits, and the world read back after each — a "
             "comparison of two stretches, which no tape in the estate yet stages",
    ),
    _law(
        "refusal-changes-nothing",
        "An action the guard refuses leaves every value untouched",
        _uncited(),
        falsifier="A tape where an action fires outside its guard — or is refused — and any "
                  "state-var reads differently after than before.",
        triggers=["any action with a guard — refusal is the other half of every transition"],
        note="The error path is the least-tested path and the most likely to half-write. No "
             "authority found stating it this generally; atomicity literature states it for "
             "transactions only.",
        meta={"expected:a-law-cites-a-source":
              "carried uncited on purpose: atomicity literature states it for transactions "
              "only, and no source has been found for the general form. Source it or keep "
              "carrying it red."},
        native="conduct/refusal",
    ),
    _law(
        "undo-restores",
        "What a delete unmakes is what the create made",
        _uncited(),
        falsifier="A tape where an action declaring `deletes` of an entity a prior `creates` "
                  "made completes, and the world differs from before the create — residue "
                  "left, or bystanders taken with it.",
        triggers=["a model declares both `creates` and `deletes` over the same entity"],
        note="Hughes files do-undo under metamorphic properties without stating this form; "
             "carried uncited until a stated source is found.",
        meta={"expected:a-law-cites-a-source":
              "Hughes gestures at do-undo under metamorphic properties but never states "
              "this form; carried red until somebody finds it stated."},
        owed="needs the world read back before the create and after the delete, compared "
             "whole — conduct/effect holds the delete's own half (the entity is gone); "
             "the residue and the bystanders want a snapshot comparison no door declares",
    ),
    _law(
        "same-state-same-story",
        "The same action from the same state with the same inputs shows the same effect",
        _uncited(),
        falsifier="Two tapes (or two stretches of one) where identical state and identical "
                  "arguments precede the same action, and the shown effects differ — with no "
                  "declared source of nondeterminism in between.",
        triggers=["an action declares an effect with `from` naming every input"],
        note="The flight-recorder's whole premise, unstated as a law: replay answers 'same?'. "
             "A difference names an undeclared input — a clock, a random draw, a global.",
        meta={"expected:a-law-cites-a-source":
              "the replay premise the estate already lives by; no authority found stating "
              "it as a law over operations. Source it or keep carrying it red."},
        owed="needs two stretches with identical abstract state and data, and a notion of "
             "which differences in what was written are declared nondeterminism (a `now`, "
             "a `rand`, an id drawn) — the flight-recorder's replay answers this per tape; "
             "the cross-stretch form is not yet a native",
    ),
    _law(
        "shown-once-shown-until-touched",
        "An effect once shown stays shown until something declares it changes",
        _uncited(),
        falsifier="A tape where an entity shown after its action is later missing or "
                  "different, with no intervening action whose `touches` or `deletes` "
                  "claims it.",
        triggers=["an action declares `creates` or `mutates` and later reads exist"],
        sightings=[
            ("health CI, first run, 2026-08-19",
             "The answers were written and then lost: process.exit fired before stdout "
             "drained past the 64KB pipe buffer on Linux, so the effect the process had "
             "shown never survived it — fixed by exiting in the write callback."),
        ],
        note="Durability without a database word: writes survive the writer. The ACID "
             "literature states it for transactions; no source found stating it for "
             "observable effects generally.",
        meta={"expected:a-law-cites-a-source":
              "ACID durability is stated for transactions only; the general "
              "observable-effect form is unsourced. Source it or keep carrying it red."},
        owed="conduct/effect stops at the first read that shows the effect; this law wants "
             "every later read through the same door, until an act declaring the entity "
             "intervenes — the horizon is computable now that positions travel, and the "
             "check is the next native to write, not a stretch of this one",
    ),
    _law(
        "the-effect-is-checkable",
        "Every declared effect names something the tape can show",
        _uncited(),
        falsifier="An effect declaration whose `entity` no state-var, event, or read on the "
                  "tape can exhibit — a claim no execution could ever refute.",
        triggers=["any effect declaration at all — this law gates the other eight"],
        note="The in-house half is already enforced: semantic-model's "
             "an-action-is-observable refuses actions no event witnesses. This states the "
             "remainder — the effect's ENTITY must be witnessable too, or the other laws "
             "bind to fiction. Popper says the general thing; nobody found says this one.",
        meta={"expected:a-law-cites-a-source":
              "Popper states falsifiability in general; nobody found states it for effect "
              "declarations. Source it or keep carrying it red."},
        native="conduct/checkable",
    ),
]


# --- the contracts: the laws as natives a rule can reach ------------------------------
#
# Descriptors only (native=True, no blob), the geometry pattern: the implementations are
# host code in `epure.behavior`, their demonstrations registered beside them, and the
# publish gate refuses this package in any process that cannot see them satisfied. The
# names are conduct's — a law family's check belongs to the catalogue that states the
# family, so that adopting conduct@ is what makes the check a demand; semantic-model@0.5.0
# carries only the declaration vocabulary (the doors) the checks read.

CONDUCT_SOLVERS = [
    SolverDef(
        name="conduct/effect", native=True,
        description="(path, rel): count the declared effects under `path` the world failed "
        "to show — a creates/mutates whose `via` write is absent from the act or whose "
        "`shown_by` read after it (before the entity's next act) does not return what the "
        "write carried; a deletes whose `shown_by` read after it still does. A read that "
        "never comes is a note, not a count.",
        params_doc={"rel": "the link from the scenario/session to the model"}),
    SolverDef(
        name="conduct/faithful", native=True,
        description="(path, rel): count the effects under `path` whose `via` write does not "
        "carry every input the effect's `from` names, as the span testified them.",
        params_doc={"rel": "the link from the scenario/session to the model"}),
    SolverDef(
        name="conduct/frame", native=True,
        description="(path, rel): count the writes under `path` through a door the model "
        "knows (any `via` it declares) that the act's own `touches.via` and effects' `via` "
        "do not admit. Acts whose actions declare no `touches` are outside the law.",
        params_doc={"rel": "the link from the scenario/session to the model"}),
    SolverDef(
        name="conduct/refusal", native=True,
        description="(path, rel): count the outermost spans under `path` that ended in error "
        "having written through a door the model knows.",
        params_doc={"rel": "the link from the scenario/session to the model"}),
    SolverDef(
        name="conduct/checkable", native=True,
        description="(path): on the model at `path`, count the declarations no tape could "
        "witness — an effect naming no state-var, no `via`, or no `shown_by`; a `touches` "
        "naming an unknown state-var."),
]


# --- the package's own examples and refuters -----------------------------------------
#
# The example is a REAL law, the frame family itself, not a synthetic one: it instantiates
# all five kinds (falsifier, trigger, citation, sighting) and passes all three rules, so
# the published shape and the authored content cannot drift apart. The five uncited
# families above are deliberately NOT examples: the gate demands examples pass, and an
# uncited law is red under a-law-cites-a-source — which is the honest state of it, carried
# in this repo's tree as declared red, never laundered through the gate.

CONDUCT_EXAMPLES = [next(l for l in CONDUCT_LAWS if l.id == "the-frame-holds")]

CONDUCT_COUNTER_EXAMPLES = [
    CounterExample(
        rule="a-law-cites-a-source",
        because="a behavior claim that names no authority — a hypothesis wearing a law's "
                "name, which is how every one of these families started",
        node=Node(
            id="reads-never-lie", kind="law",
            name="A read always returns what was last written",
            params={"authority": Quantity(value=1, unit="law", provenance="asserted",
                                          grounded=False, source="feels obviously true")},
            children=[
                Node(id="cx1-f", kind="falsifier",
                     payload={"claim": "a tape where a read disagrees with the last write"}),
                Node(id="cx1-t", kind="trigger", payload={"when": "any effect declaration"}),
            ],
        ),
    ),
    CounterExample(
        rule="a-law-can-be-violated-observably",
        because="a law whose breach no tape could ever exhibit can never produce a verdict, "
                "so it is a taste and not a law",
        node=Node(
            id="behaves-well", kind="law",
            name="The system should behave predictably",
            params={"authority": Quantity(value=1, unit="law", provenance="cited",
                                          grounded=True, source="a methodology book")},
            children=[
                Node(id="cx2-t", kind="trigger", payload={"when": "any effect declaration"}),
                Node(id="cx2-c", kind="citation", name="A methodology book",
                     payload={"url": "https://example.invalid",
                              "quote": "Systems should behave predictably."}),
            ],
        ),
    ),
    CounterExample(
        rule="a-law-is-switched-on-by-something",
        because="a law nothing switches on is a checklist item, and a checklist item is "
                "read once and never again",
        node=Node(
            id="always-applies", kind="law",
            name="Every operation is idempotent",
            params={"authority": Quantity(value=1, unit="law", provenance="cited",
                                          grounded=True, source="RFC 9110 §9.2.2")},
            children=[
                Node(id="cx3-f", kind="falsifier",
                     payload={"claim": "a tape where twice differs from once"}),
                Node(id="cx3-c", kind="citation", name=RFC9110,
                     payload={"url": RFC9110_URL,
                              "quote": "A request method is considered \"idempotent\" if "
                                       "the intended effect on the server of multiple "
                                       "identical requests with that method is the same as "
                                       "the effect for a single such request."}),
            ],
        ),
    ),
]


CONDUCT_PACKAGE = Package(
    name="conduct",
    version="0.2.1",
    description="The behavior laws of operations, as checkable data: what a declared effect "
                "promises under reading back (it happened, it matches its inputs, nothing "
                "else moved), under algebra (repetition, inversion, refusal), and under time "
                "(replay, persistence, witnessability). Nine families, a census folded from "
                "Hughes's five approaches to writing properties onto what a tape can "
                "witness. Laws bind by INHERITANCE to semantic-model's generic effect "
                "kinds — an action declares `creates` and every creates-law arrives; nothing "
                "is stamped per operation. Each law carries the tape that would convict it, "
                "the declaration that switches it on, and the source that authorises it; an "
                "uncited law is an ungrounded param the ledger's own gate refuses to let "
                "travel as settled. 0.2.0 delivers the natives 0.1.0 named: conduct/effect, "
                "conduct/faithful, conduct/frame and conduct/refusal hold a recorded run to "
                "the effect, faithfulness, frame and refusal families through the doors an "
                "action declares (semantic-model@0.5.0's `via`/`shown_by`), and "
                "conduct/checkable holds the model to the checkability family. The other "
                "four families are carried as named debts on their laws, not stretched. "
                "0.2.1 changes no kind, rule or contract: the frame law — this package's "
                "own example — gained its second sighting, the first the native itself "
                "caught (chores, 2026-08-20), and a sighting on the example is content.",
    publisher="poietic.studio",
    requires=[
        # Pinned exactly, by doctrine: grounding@ for the authority provenance the laws
        # carry; semantic-model@0.5.0 for the effect kinds the triggers bind to and the doors the natives read — the
        # version where creates/mutates/deletes/touches first exist.
        PackageRef(name="grounding", version="1.2.0"),
        PackageRef(name="semantic-model", version="0.5.0"),
    ],
    vocabulary=CONDUCT_VOCABULARY,
    rules=CONDUCT_RULES,
    solvers=CONDUCT_SOLVERS,
    examples=CONDUCT_EXAMPLES,
    counter_examples=CONDUCT_COUNTER_EXAMPLES,
)
