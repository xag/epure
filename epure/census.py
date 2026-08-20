"""The census: every item the sources list, each mapped to a law, each with a status.

conduct@0.1.0 said "nine families, a census folded from Hughes's five approaches" and grounded
the nine on `len(CONDUCT_LAWS)` — the catalogue's own length. Read in full, the paper lists
forty-odd properties in six categories, ranks the model-based ones first ("together form a
complete specification"), and every family the catalogue kept had been weakened from a value
comparison to a presence check. That is a census filtered by what was feasible, and the
practice law `a-census-is-read-from-its-source` (craft@) was earned by it.

This module is the correction and the harness: one `item` per property the source states,
with its formula; each item names the generic law that covers it and carries exactly one
status child —

- **covered**: a native holds the law in the form the source states it;
- **weakened**: a native holds a weaker form (presence for a value, a door for a variable)
  and the child says what is missing;
- **owed**: no native; the child names the debt that carries it;
- **aside**: the item is not a claim about an operation's behaviour (a test generator, a
  measurement, the paper's warm-up example, an HTTP caching policy) and the child says why.

The counts on the census node are COMPUTED over the items (`census()` builds the node and
its params from the list; nothing here is typed twice), so the brief shows the source's
number and the number left out, and a rule refuses an item with no status or two.

The mapping from a property over a binary search tree to a law over an app's operations
is the one judgment call here, stated per item: `insert k v` is an act declaring
`creates`/`mutates` of an entity from inputs, `delete k` an act declaring `deletes`,
`find k` a read through a `shown_by` door, `toList` the abstraction function — the
projection from the store to the model's state-vars — and `union` a merge, which no kind
in semantic-model@ yet names.
"""

from __future__ import annotations

from quern import Node
from quern.provenance import Quantity

HUGHES = "hughes-2020"
RFC = "rfc-9110"
LAMPORT = "lamport-1977"

# Debts the owed items point at (ids in this repo's ledger).
TWO_STRETCHES = "four-families-compare-two-stretches"
ABSTRACTION = "the-world-is-not-yet-projected"
MERGE = "no-kind-names-a-merge"
CONDITIONAL = "no-kind-names-a-validator"
GENERATED = "no-generated-world-is-checked"
DOORS = "no-door-census"
TEMPORAL = "temporal-predicates-are-inexpressible"
FAIRNESS = "fairness-is-inexpressible"


def _item(id: str, source: str, category: str, formula: str, law: str, status: str,
          because: str = "", section: str = "") -> dict:
    return {"id": id, "source": source, "category": category, "formula": formula,
            "law": law, "status": status, "because": because, "section": section}


def covered(id, source, category, formula, law, native, section=""):
    return _item(id, source, category, formula, law, "covered", native, section)


def weakened(id, source, category, formula, law, missing, section=""):
    return _item(id, source, category, formula, law, "weakened", missing, section)


def owed(id, source, category, formula, law, debt, section=""):
    return _item(id, source, category, formula, law, "owed", debt, section)


def aside(id, source, category, formula, why, section=""):
    return _item(id, source, category, formula, "", "aside", why, section)


# --- Hughes 2020, "How to Specify It!" — every `prop` the paper states ----------------
#
# Formulas as the paper writes them (Figures 3–6 and the text), with `≏` for the paper's
# equivalence (toList equality) and `===` for equality.

_V = "validity"
_P = "postcondition"
_M = "metamorphic"
_E = "preservation of equivalence"
_I = "inductive (completeness of insertion)"
_B = "model-based"
_A = "aside"

ITEMS: list[dict] = [
    # the warm-up, §2: reverse
    aside("Reverse", HUGHES, _A, "reverse xs === predictRev xs; reverse (reverse xs) === xs",
          "the paper's warm-up on list reversal, not a property of a store", "§2"),
    aside("Wrong", HUGHES, _A, "reverse xs === xs",
          "the paper's deliberately false property, shown to fail", "§2"),

    # §4.1 validity
    covered("NilValid", HUGHES, _V, "valid nil", "the-invariant-holds",
            "model/prove checks every invariant in the initial state", "§4.1"),
    covered("InsertValid", HUGHES, _V, "valid (insert k v t)", "the-invariant-holds",
            "model/prove over every reachable state; model/refines re-checks after every "
            "act on a tape", "§4.1"),
    covered("DeleteValid", HUGHES, _V, "valid t ==> valid (delete k t)", "the-invariant-holds",
            "as InsertValid", "§4.1"),
    covered("UnionValid", HUGHES, _V, "valid (union t t')",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "§4.1"),
    covered("ArbitraryValid", HUGHES, _V, "valid t (for generated t)",
             "a-generated-world-is-valid",
             'conduct/constructible on a probe tape: every world read off a mutated tape is one the model reaches, held before any other law is reported',
             "§4.1"),
    covered("ShrinkValid", HUGHES, _V, "valid t ==> all valid (shrink t)",
             "a-generated-world-is-valid",
             'conduct/constructible on a probe tape: every world read off a mutated tape is one the model reaches, held before any other law is reported',
             "§4.1"),
    aside("ValidEquivalent", HUGHES, _V, "valid t === fastValid t",
          "two implementations of the validity predicate agree — about the test's own "
          "oracle, not the store", "§4.1"),

    # §4.2 postconditions
    covered("InsertPost", HUGHES, _P,
             "find k' (insert k v t) === if k == k' then Just v else find k' t",
             "the-effect-is-shown",
             "conduct/agrees: the variable's value projected from the reads after the act equals the model's own update applied to the projected world before it; conduct/effect holds the presence form where no projection exists",
             "§4.2"),
    covered("InsertPost-others", HUGHES, _P,
             "k /= k' ==> find k' (insert k v t) === find k' t",
             "the-frame-holds",
             'conduct/agrees: a variable the action does not update projects the same value after as before; conduct/frame holds the door form where no projection exists',
             "§4.2"),
    weakened("InsertPost-value", HUGHES, _P,
             "find k (insert k v t) === Just v, for the v that was the argument",
             "the-effect-matches-its-inputs",
             "where the entity's update READS the input (assignee := member), conduct/agrees "
             "holds the read equal to the argument — the source's form; where it ignores it "
             "(held := 1, whatever the coat), conduct/faithful only checks that the WRITE "
             "carried the input, not that a read returns it — a weaker form, since nothing "
             "on the model projects the coat", "§4.2"),
    covered("InsertPostSameKey", HUGHES, _P,
             "find k (insert k v t) === Just v",
             "the-effect-is-shown",
             "conduct/agrees: the variable's value projected from the reads after the act equals the model's own update applied to the projected world before it; conduct/effect holds the presence form where no projection exists",
             "§4.2"),
    covered("DeletePost", HUGHES, _P,
             "find k' (delete k t) === if k == k' then Nothing else find k' t",
             "the-effect-is-shown",
             "conduct/agrees: the variable's value projected from the reads after the act equals the model's own update applied to the projected world before it; conduct/effect holds the presence form where no projection exists",
             "§4.2"),
    covered("DeletePost-others", HUGHES, _P,
             "k /= k' ==> find k' (delete k t) === find k' t",
             "the-frame-holds",
             'conduct/agrees: a variable the action does not update projects the same value after as before; conduct/frame holds the door form where no projection exists',
             "§4.2"),
    covered("FindPostPresent", HUGHES, _P,
             "find k (insert k v t) === Just v",
             "the-effect-is-shown",
             "conduct/agrees: the variable's value projected from the reads after the act equals the model's own update applied to the projected world before it; conduct/effect holds the presence form where no projection exists",
             "§4.2"),
    covered("FindPostAbsent", HUGHES, _P, "find k (delete k t) === Nothing",
            "the-effect-is-shown", "conduct/effect, deletes: no shown_by read after the act "
            "still shows what an earlier effect carried or names what the removal named",
            "§4.2"),
    covered("InsertDeleteComplete", HUGHES, _P,
         "case find k t of Nothing -> t === delete k t; Just v -> t === insert k v t",
             "twice-is-once",
             'conduct/twice: the world after an admitted repeat equals the world after once',
             "§4.2"),
    covered("UnionPost", HUGHES, _P, "find k (union t t') === (find k t <|> find k t')",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "§4.2"),

    # §4.3 metamorphic
    covered("InsertInsertWeak", HUGHES, _M,
         "k /= k' ==> insert k v (insert k' v' t) ≏ insert k' v' (insert k v t)",
             "independent-writes-commute",
             'conduct/commute: A;B and B;A from an equal world leave equal worlds',
             "§4.3"),
    covered("InsertInsert", HUGHES, _M,
         "insert k v (insert k' v' t) ≏ if k == k' then insert k v t "
         "else insert k' v' (insert k v t)",
             "last-write-wins",
             "conduct/last-write: the value after the second overwrite is the second's update on the world before the first",
             "§4.3"),
    covered("InsertDeleteWeak", HUGHES, _M,
         "k /= k' ==> insert k v (delete k' t) ≏ delete k' (insert k v t)",
             "independent-writes-commute",
             'conduct/commute: A;B and B;A from an equal world leave equal worlds',
             "§4.3"),
    covered("InsertDelete", HUGHES, _M,
         "insert k v (delete k' t) ≏ if k == k' then insert k v t "
         "else delete k' (insert k v t)",
             "last-write-wins",
             "conduct/last-write: the value after the second overwrite is the second's update on the world before the first",
             "§4.3"),
    covered("InsertUnion", HUGHES, _M, "insert k v (union t t') ≏ union (insert k v t) t'",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "§4.3"),
    covered("DeleteNil", HUGHES, _M, "delete k nil ≏ nil", "refusal-changes-nothing",
            "conduct/refusal: an act that does not apply (its guard refuses it, here an "
            "empty world) writes through no door", "§4.3, Appendix A"),
    covered("DeleteInsertWeak", HUGHES, _M,
         "k /= k' ==> delete k (insert k' v' t) ≏ insert k' v' (delete k t)",
             "independent-writes-commute",
             'conduct/commute: A;B and B;A from an equal world leave equal worlds',
             "Appendix A"),
    covered("DeleteInsert", HUGHES, _M,
         "delete k (insert k' v' t) ≏ if k == k' then delete k t "
         "else insert k' v' (delete k t)",
             "undo-restores",
             'conduct/undo: the world after the delete equals the world before the create',
             "Appendix A"),
    covered("DeleteDelete", HUGHES, _M, "delete k (delete k' t) ≏ delete k' (delete k t)",
             "independent-writes-commute",
             'conduct/commute: A;B and B;A from an equal world leave equal worlds',
             "Appendix A"),
    covered("DeleteUnion", HUGHES, _M, "delete k (union t t') ≏ union (delete k t) (delete k t')",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Appendix A"),
    covered("UnionNil1", HUGHES, _M, "union nil t ≏ t",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Appendix A"),
    covered("UnionNil2", HUGHES, _M, "union t nil ≏ t",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Appendix A"),
    covered("UnionDeleteInsert", HUGHES, _M,
         "union (delete k t) (insert k v t') ≏ insert k v (union t t')",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Appendix A"),
    covered("UnionUnionIdem", HUGHES, _M, "union t t ≏ t",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Appendix A"),
    covered("UnionUnionAssoc", HUGHES, _M, "union (union t1 t2) t3 ≏ union t1 (union t2 t3)",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Appendix A"),
    covered("FindNil", HUGHES, _M, "find k nil === Nothing", "a-read-changes-nothing",
            "a read of an empty world answers nothing and, by conduct/frame on an act "
            "declaring touches.via = [], writes nothing", "Appendix A"),
    covered("FindInsert", HUGHES, _M,
             "find k (insert k' v' t) === if k == k' then Just v' else find k t",
             "the-effect-is-shown",
             "conduct/agrees: the variable's value projected from the reads after the act equals the model's own update applied to the projected world before it; conduct/effect holds the presence form where no projection exists",
             "Appendix A"),
    covered("FindInsert-later", HUGHES, _M,
         "find k t, read again after later acts that do not name k, === find k t",
             "shown-once-shown-until-touched",
             'conduct/durable: every later read projects what the first showed, until an act updates it',
             "the else-branch of FindInsert read over time, Appendix A"),
    covered("FindDelete", HUGHES, _M,
             "find k (delete k' t) === if k == k' then Nothing else find k t",
             "the-effect-is-shown",
             "conduct/agrees: the variable's value projected from the reads after the act equals the model's own update applied to the projected world before it; conduct/effect holds the presence form where no projection exists",
             "Appendix A"),
    covered("FindUnion", HUGHES, _M, "find k (union t t') === (find k t <|> find k t')",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Appendix A"),

    # §4.3 preservation of equivalence
    covered("InsertPreservesEquivWeak", HUGHES, _E,
         "t ≏ t' ==> insert k v t ≏ insert k v t'",
             "equivalent-worlds-stay-equivalent",
             'conduct/same-story: equivalence is projected equality, compared after the same act',
             "§4.3"),
    covered("InsertPreservesEquiv", HUGHES, _E, "insert k v t ≏ insert k v t' (t ≏ t' generated)",
             "equivalent-worlds-stay-equivalent",
             'conduct/same-story: equivalence is projected equality, compared after the same act',
             "§4.3, Fig. 5"),
    covered("DeletePreservesEquiv", HUGHES, _E, "delete k t ≏ delete k t'",
             "equivalent-worlds-stay-equivalent",
             'conduct/same-story: equivalence is projected equality, compared after the same act',
             "Fig. 5"),
    covered("UnionPreservesEquiv", HUGHES, _E, "union t1 t2 ≏ union t1' t2'",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "Fig. 5"),
    covered("FindPreservesEquiv", HUGHES, _E, "find k t === find k t'",
             "same-state-same-story",
             'conduct/same-story: same act, same data, equal projected worlds before — equal after',
             "Fig. 5"),
    aside("Equivs", HUGHES, _E, "t ≏ t' (for generated pairs)",
          "tests the generator of equivalent pairs, not the store", "Fig. 5"),
    aside("ShrinkEquivs", HUGHES, _E, "t ≏ t' ==> all equivalent (shrink (t, t'))",
          "tests the shrinker, not the store", "Fig. 5"),

    # §4.4 inductive
    covered("UnionInsert", HUGHES, _I, "union (insert k v t) t' ≏ insert k v (union t t')",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "§4.4"),
    covered("InsertComplete", HUGHES, _I, "t === foldl (flip (uncurry insert)) nil (insertions t)",
             "every-world-is-constructible",
             'conduct/constructible: every projected world read off the tape is a state the prover reaches',
             "§4.4"),
    covered("InsertCompleteForDelete", HUGHES, _I, "InsertComplete (delete k t)",
             "every-world-is-constructible",
             'conduct/constructible: every projected world read off the tape is a state the prover reaches',
             "§4.4"),
    covered("InsertCompleteForUnion", HUGHES, _I, "InsertComplete (union t t')",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "§4.4"),

    # §4.5 model-based — the abstraction function, which the paper ranks first
    covered("NilModel", HUGHES, _B,
             "toList nil === []",
             "the-world-agrees-with-the-model",
             "conduct/agrees: the projected world after the act equals the model's update "
             "applied to the projected world before — the diagram, on a tape",
             "§4.5, Fig. 6"),
    covered("InsertModel", HUGHES, _B,
             "toList (insert k v t) === L.insert (k, v) (deleteKey k (toList t))",
             "the-world-agrees-with-the-model",
             "conduct/agrees: the projected world after the act equals the model's update "
             "applied to the projected world before — the diagram, on a tape",
             "§4.5, Fig. 6"),
    covered("DeleteModel", HUGHES, _B,
             "toList (delete k t) === deleteKey k (toList t)",
             "the-world-agrees-with-the-model",
             "conduct/agrees: the projected world after the act equals the model's update "
             "applied to the projected world before — the diagram, on a tape",
             "§4.5, Fig. 6"),
    covered("UnionModel", HUGHES, _B,
         "toList (union t t') === L.sort (L.unionBy ((==) `on` fst) (toList t) (toList t'))",
             "a-merge-keeps-both-and-prefers-the-left",
             "conduct/merge: after the act each merged variable projects to its own value where present, else the other's; a self-merge leaves the world; (b then c) equals (b merged with c)",
             "§4.5, Fig. 6"),
    covered("FindModel", HUGHES, _B,
             "find k t === L.lookup k (toList t)",
             "the-world-agrees-with-the-model",
             "conduct/agrees: the projected world after the act equals the model's update "
             "applied to the projected world before — the diagram, on a tape",
             "§4.5, Fig. 6"),

    # §6 measurement
    aside("Measure", HUGHES, _A, "label (measure k t) ... (coverage of the insert cases)",
          "a measurement of test-case distribution, not a property of the store", "§6"),
    aside("Unique", HUGHES, _A, "x /= y (for generated pairs)",
          "a property of the key generator, not the store", "§6"),

    # --- RFC 9110, HTTP Semantics: every normative property of methods and resources -----
    covered("safe", RFC, "method property",
            "A request method is considered \"safe\" if it is intended only for retrieving "
            "information and MUST NOT change the state of the origin server",
            "a-read-changes-nothing",
            "conduct/frame convicts a write through any door the model knows inside an act "
            "declaring touches.via = []; conduct/agrees convicts a projected variable that "
            "moved across it", "§9.2.1"),
    covered("safe-undeclared-doors", RFC, "method property",
            "...MUST NOT change the state of the origin server — the WHOLE state, including what "
            "no declaration names",
            "a-read-changes-nothing",
            "conduct/doors: every write function the model's boundary declares is a door of "
            "some action, so a read-act's empty boundary excludes the whole state the recorder "
            "can see", "§9.2.1"),
    covered("idempotent", RFC, "method property",
         "the intended effect on the server of multiple identical requests with that method is "
         "the same as the effect for a single such request",
             "twice-is-once",
             'conduct/twice: the world after an admitted repeat equals the world after once',
             "§9.2.2"),
    aside("cacheable", RFC, "method property",
          "Responses to safe request methods are cacheable, provided the response has "
          "appropriate Cache-Control or Expires header fields",
          "a policy about HTTP responses, not a property of an operation on a store; an "
          "http@ vocabulary's to state", "§9.2.3"),
    covered("strong-validator", RFC, "validator",
         "A strong validator is representation metadata that changes value whenever the "
         "associated representation changes",
             "a-change-moves-the-validator",
             'conduct/stamped: an act that moved a projected variable moved the validator',
             "§8.8.1"),
    covered("weak-validator", RFC, "validator",
         "A weak validator is representation metadata that might not change for every "
         "alteration to the associated representation",
             "a-change-moves-the-validator",
             'conduct/stamped: an act that moved a projected variable moved the validator',
             "§8.8.1"),
    covered("last-modified", RFC, "validator",
         "the date and time at which the origin server believes the representation was last "
         "modified",
             "a-change-moves-the-validator",
             'conduct/stamped: an act that moved a projected variable moved the validator',
             "§8.8.2"),
    covered("etag", RFC, "validator",
         "An entity tag is an opaque validator for differentiating between multiple "
         "representations of the same resource",
             "a-change-moves-the-validator",
             'conduct/stamped: an act that moved a projected variable moved the validator',
             "§8.8.3"),
    covered("if-match", RFC, "conditional request",
         "makes the request method conditional on the recipient origin server having a "
         "current representation of the target resource that matches the provided entity-tag(s)",
             "a-conditional-write-compares-before-it-writes",
             'conduct/conditional: handed the current stamp the act proceeds; handed another it refuses and writes nothing',
             "§13.1.1"),
    covered("if-none-match", RFC, "conditional request",
         "makes the request method conditional on a recipient cache or origin server NOT "
         "having a current representation of the target resource that matches any of the "
         "provided entity-tag(s)",
             "a-conditional-write-compares-before-it-writes",
             'conduct/conditional: handed the current stamp the act proceeds; handed another it refuses and writes nothing',
             "§13.1.2"),
    covered("if-modified-since", RFC, "conditional request",
         "makes a GET or HEAD request method conditional on the origin server only sending a "
         "representation if the selected representation has been modified since the provided "
         "HTTP-date",
             "a-conditional-write-compares-before-it-writes",
             'conduct/conditional: handed the current stamp the act proceeds; handed another it refuses and writes nothing',
             "§13.1.3"),
    covered("if-unmodified-since", RFC, "conditional request",
         "makes the request method conditional on the origin server only applying the request "
         "to the target resource if the selected representation has not been modified since "
         "the provided HTTP-date",
             "a-conditional-write-compares-before-it-writes",
             'conduct/conditional: handed the current stamp the act proceeds; handed another it refuses and writes nothing',
             "§13.1.4"),
    covered("precondition-failed", RFC, "conditional request",
         "The 412 (Precondition Failed) status code indicates that one or more conditions given "
         "in the request header fields evaluated to false when tested on the server",
             "a-conditional-write-compares-before-it-writes",
             'conduct/conditional: handed the current stamp the act proceeds; handed another it refuses and writes nothing',
             "§15.5.13"),
    covered("not-modified", RFC, "conditional request",
         "The 304 (Not Modified) status code indicates that a conditional GET or HEAD request "
         "has been received and would have resulted in a 200 (OK) response if it were not for "
         "the fact that the condition evaluated to false",
             "a-conditional-write-compares-before-it-writes",
             'conduct/conditional: handed the current stamp the act proceeds; handed another it refuses and writes nothing',
             "§15.4.5"),
]

ITEMS += [
    # --- Lamport 1977, Proving the Correctness of Multiprocess Programs: the two kinds -------
    covered("safety", LAMPORT, "property kind",
            "safety ... the proper generalization of partial correctness to concurrent programs "
            "- something bad never happens",
            "the-invariant-holds",
            "model/prove over every reachable state, re-checked by model/refines at every step "
            "of a tape; conduct/constructible holds every world read off a tape to reachability",
            "the paper's own annotation, lamport.azurewebsites.net/pubs"),
    covered("liveness", LAMPORT, "property kind",
            "liveness ... the proper generalization of termination to concurrent programs - "
            "something good eventually happens",
            "what-is-promised-eventually-happens",
            "model/promised: from every state where the promise is made, a state that keeps "
            "it is reachable; conduct/eventually: on a tape, kept within the horizon the "
            "promise names, or reported open",
            "the paper's own annotation, lamport.azurewebsites.net/pubs"),
    owed("weak-fairness", LAMPORT, "property kind",
         "weak fairness: an action that stays enabled is eventually taken (Lamport, Fairness and "
         "Hyperfairness, 2000 - stated here from the literature's standard form; the paper's own "
         "sentence has not been verified and the law it maps to is carried uncited)",
         "an-enabled-act-is-eventually-taken", FAIRNESS, "Fairness and Hyperfairness, 2000"),
]

STATUSES = ("covered", "weakened", "owed", "aside")


def census() -> Node:
    """The census node: one `item` child per source property, one status child each, and
    the counts computed over them. Nothing typed twice."""
    items: list[Node] = []
    for it in ITEMS:
        status = Node(id=f"{it['id']}--{it['status']}", kind=it["status"],
                      payload={"because": it["because"]})
        items.append(Node(id=f"{it['source']}--{it['id']}", kind="item",
                          name=it["formula"],
                          payload={"source": it["source"], "category": it["category"],
                                   "section": it["section"], "law": it["law"]},
                          children=[status]))
    counts = {s: sum(1 for it in ITEMS if it["status"] == s) for s in STATUSES}
    by_source = {src: sum(1 for it in ITEMS if it["source"] == src)
                 for src in (HUGHES, RFC, LAMPORT)}
    params = {
        "items": Quantity(value=len(ITEMS), unit="item", provenance="computed", grounded=True,
                          source=f"len(ITEMS): {by_source[HUGHES]} from Hughes 2020 (every "
                                 f"`prop` in Figures 3–8 and the text), {by_source[RFC]} from "
                                 f"RFC 9110 §8.8, §9.2, §13, §15, {by_source[LAMPORT]} from "
                                 "Lamport 1977 (safety, liveness)"),
    }
    for s in STATUSES:
        params[s] = Quantity(value=counts[s], unit="item", provenance="computed", grounded=True,
                             source=f"items whose status child is `{s}`")
    return Node(id="the-census-of-the-sources", kind="census",
                name="Every property the cited sources state, each mapped to a law and "
                     "counted by what holds it: covered, weakened, owed, or set aside",
                payload={"note": "Read the numbers before the laws: `owed` and `weakened` are "
                                 "what this catalogue does not yet do, in the sources' own "
                                 "count."},
                params=params, children=items)


def laws_named() -> set[str]:
    return {it["law"] for it in ITEMS if it["law"]}


def coverage_of(law: str) -> dict[str, int]:
    """How many source items a law covers, by status — for the law's own payload."""
    out = {s: 0 for s in STATUSES}
    for it in ITEMS:
        if it["law"] == law:
            out[it["status"]] += 1
    return out
