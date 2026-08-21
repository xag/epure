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
    # and when no row shows the before at all, the constant every row shows is partial -
    # the frame is neither refuted nor confirmed, and a candidate judged on no row is
    # skipped, never proposed
    rows = [({}, {}, {"n": 0}), ({}, {}, {"n": 0})]
    assert draft_update_where("n", list(range(8)), rows, [], ["n"]) == ("0", "partial",
                                                                          [(0, "n"), (1, "n")])
    rows = [({"n": 0}, {}, {"n": 1}), ({"n": 1}, {}, {"n": 2}), ({"n": 6}, {}, {"n": 7})]
    assert draft_update("n", list(range(8)), rows, [], ["n", "today"]) == ("n + 1", "increment")


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


def test_the_richer_grammar_drafts_a_predicate_and_a_conditional():
    from epure.draft import draft_update_where
    names = {"n": list(range(8)), "p": [False, True], "d": list(range(-1, 7))}
    # a flag that is exactly "the counter is still zero": predicate, found after the simple
    # forms fail (the posts vary, no argument or variable carries them)
    rows = [({"n": 0, "p": True, "d": 0}, {}, {"p": True}), ({"n": 1, "p": True, "d": 1}, {}, {"p": False}),
            ({"n": 0, "p": False, "d": 2}, {}, {"p": True})]
    assert draft_update_where("p", [False, True], rows, [], ["n", "p", "d"], names)[:2] == \
        ("n == 0", "predicate")
    # a day that jumps to tomorrow on two weekdays and stays otherwise: the conditional, in
    # the hand's own form
    rows = [({"d": -1, "n": 0}, {}, {"d": 1}), ({"d": 1, "n": 1}, {}, {"d": 1}),
            ({"d": 1, "n": 2}, {}, {"d": 1}), ({"d": 1, "n": 3}, {}, {"d": 4}),
            ({"d": 4, "n": 4}, {}, {"d": 4})]
    expr, status, _ = draft_update_where("d", list(range(-1, 7)), rows, [], ["n", "d"], names)
    assert status == "conditional" and expr.startswith("d + (") and expr.endswith(") * (n + 1 - d)")
    # the simplest predicate the rows admit, which need not be the one a person meant: what
    # the draft owes is every sample, and --propose names where it parts from the hand
    from epure.prove import _compile, _LITERALS
    f = _compile(expr, "draft")
    assert all(f({**_LITERALS, **pre}) == post["d"] for pre, _, post in rows)
    # without the domains, the richer grammar is not tried
    assert draft_update_where("d", list(range(-1, 7)), rows, [], ["n", "d"])[1] == "unresolved"


def test_equivalence_is_judged_where_the_world_can_be():
    # the cloakroom's `lit` is derived from `held`: the sign is on exactly while a coat
    # hangs. The two are separate variables, so the domain holds four combinations and the
    # model reaches two - and an expression that reads one is the same as one that reads
    # the other everywhere the model can actually be
    from epure.draft import Reach
    names = {"held": [0, 1], "lit": [False, True]}
    R = Reach.of(spec.cloakroom())
    assert not equivalent("lit", "held == 1", names, boolean=True)
    assert equivalent("lit", "held == 1", names, boolean=True, reach=R)
    assert R.holds({"held": 1, "lit": True}) and not R.holds({"held": 1, "lit": False})
    # and an UPDATE is judged where its act is enabled: check-coat's guard is `held == 0`,
    # so `held + 1` and `1` are one expression there and two anywhere else - a world the
    # guard refuses is no more a place to tell them apart than one the model cannot reach
    enabled = R.where("held == 0", names)
    assert not equivalent("held + 1", "1", names)
    assert equivalent("held + 1", "1", names, reach=enabled)
    assert not enabled.holds({"held": 1})


def test_the_separating_point_is_one_a_flight_could_fly():
    # the measurement carries both counts apart: what agrees everywhere, and what agrees
    # only where the model reaches the act enabled - the second is an equivalence, and
    # saying which one it is is the whole difference between honest and flattering
    S = _samples(spec.AGREES, spec.RETAGGED, spec.COMMUTES)
    report = measure(spec.cloakroom(), S)
    assert report["unreachable_pre"] == 0        # the tapes stay inside the model
    assert report["reachable"] > 0
    t = report["tally"]
    assert t["updates_equivalent"] >= t["updates_equivalent_enabled"]
    # every point --propose names sits in the reachable set: an experiment in a world the
    # model cannot be in is an errand nobody can run
    from epure.draft import Reach
    R = Reach.of(spec.cloakroom())
    for p in report["proposals"]:
        if sp := p.get("separating"):
            assert R.holds(sp["pre"]), (p["action"], sp["pre"])
