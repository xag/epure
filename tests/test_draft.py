"""The draft: updates and guards proposed from tapes, and the equivalence that measures them."""

from quern import Quern

from epure import spec
from epure.behavior import _Worlds
from epure.draft import Samples, draft_guard, draft_update, equivalent, measure


def _samples(*tapes):
    S = Samples()
    for t in tapes:
        tree = Quern()
        tree.root.children = [spec.cloakroom(), t.model_copy(deep=True)]
        S.add(_Worlds(tree, "visit", "model"))
    return S


def test_the_cloakroom_drafts_its_own_arithmetic():
    # a deposit, a tagging and a shelving, each with the world read before and after
    S = _samples(spec.AGREES, spec.RETAGGED, spec.COMMUTES)
    report = measure(spec.cloakroom(), S)
    by = {a["id"]: a for a in report["actions"]}
    assert by["check-coat"]["updates"]["held"]["draft"] == "1"
    assert by["check-coat"]["updates"]["held"]["verdict"] == "equivalent"
    assert by["tag-coat"]["updates"]["tag"]["draft"] == "color"
    assert by["tag-coat"]["updates"]["tag"]["verdict"] == "equivalent"
    # every shelving on these tapes shelved high: the simplest expression the tapes admit
    # is the constant, and the domain tells it from the argument the person wrote
    assert by["shelve-coat"]["updates"]["shelf"]["draft"] == "'high'"
    assert by["shelve-coat"]["updates"]["shelf"]["verdict"] == "different"
    t = report["tally"]
    assert t["updates_equivalent"] >= 3 and t["frames_disputed"] == 0


def test_a_guard_is_drafted_from_positives_only_and_says_so():
    S = _samples(spec.AGREES, spec.RETAGGED)
    report = measure(spec.cloakroom(), S)
    assert report["refusals"] == 0
    by = {a["id"]: a for a in report["actions"]}
    # the tagging always found a coat on the hook: `held` is an int, not a bool, so the
    # positive-only draft has no term for it, and the hand guard `held == 1` is not reached
    assert by["tag-coat"]["guard"]["verdict"] == "different"


def test_simplest_first():
    rows = [({"x": 0}, {"a": 3}, {"x": 3}), ({"x": 1}, {"a": 3}, {"x": 3})]
    assert draft_update("x", list(range(8)), rows, ["a"], ["x"]) == ("3", "constant")
    rows = [({"x": 0}, {"a": 3}, {"x": 3}), ({"x": 1}, {"a": 5}, {"x": 5})]
    assert draft_update("x", list(range(8)), rows, ["a"], ["x"]) == ("a", "argument")
    rows = [({"x": 0}, {}, {"x": 1}), ({"x": 4}, {}, {"x": 5})]
    assert draft_update("x", list(range(8)), rows, [], ["x"]) == ("x + 1", "increment")
    rows = [({"x": 5}, {}, {"x": 6}), ({"x": 7}, {}, {"x": 7})]
    assert draft_update("x", list(range(8)), rows, [], ["x"]) == ("min(x + 1, 7)", "saturating")
    rows = [({"x": 2}, {}, {"x": 2})]
    assert draft_update("x", list(range(8)), rows, [], ["x"]) == (None, "frame")
    assert draft_update("x", list(range(8)), [], [], ["x"]) == (None, "unwitnessed")


def test_equivalence_is_over_the_whole_domain_not_the_samples():
    names = {"n": list(range(8))}
    assert equivalent("n + 1", "n + 1", names)
    assert not equivalent("n + 1", "min(n + 1, 7)", names)   # differs at n = 7 only
    assert equivalent("", "true", {"p": [False, True]}, boolean=True)
    assert not equivalent("p", "true", {"p": [False, True]}, boolean=True)


def test_guard_terms_are_booleans_that_never_varied():
    pres = [{"p": True, "q": False, "e": "a"}, {"p": True, "q": True, "e": "b"}]
    assert draft_guard(pres, {"p": [False, True], "q": [False, True], "e": ["a", "b", "c"]}) == "p"


def test_a_row_without_a_before_does_not_refute_what_it_cannot_judge():
    # three hoovers: two with the clock read before, one on a Monday before any tick wrote
    # it. `today` fits both rows that show it and cannot be judged on the third: partial,
    # naming the row and the operand - never 'unresolved', and never the constant that would
    # fit if the Monday row were thrown away
    rows = [({"last": -1, "today": 3}, {}, {"last": 3}),
            ({"last": -1}, {}, {"last": 0}),
            ({"last": 0, "today": 2}, {}, {"last": 2})]
    from epure.draft import draft_update_where
    expr, status, unsettled = draft_update_where("last", list(range(-1, 7)), rows, [],
                                                 ["last", "today"])
    assert (expr, status) == ("today", "partial")
    assert unsettled == [(1, "today")]
    # and when no row shows the before at all, the frame is partial - not the constant
    rows = [({}, {}, {"n": 0}), ({}, {}, {"n": 0})]
    assert draft_update_where("n", list(range(8)), rows, [], ["n"]) == (None, "partial",
                                                                          [(0, "n"), (1, "n")])


def test_a_guard_is_drafted_from_refusals():
    # taken while pending, refused while not: the simplest predicate that separates them
    taken = [{"pending": True, "who": "m1"}, {"pending": True, "who": "none"}]
    denied = [{"pending": False, "who": "m1"}]
    variables = {"pending": [False, True], "who": ["none", "m1", "m2"]}
    assert draft_guard(taken, variables, refused=denied) == "pending"
    # two atoms when one will not do: taken only when pending AND assigned
    taken = [{"pending": True, "who": "m1"}]
    denied = [{"pending": False, "who": "m1"}, {"pending": True, "who": "none"}]
    assert draft_guard(taken, variables, refused=denied) == "pending and who != 'none'"
    # no refusal: positives only, and the measurement says so
    assert draft_guard(taken, variables) == "pending"
