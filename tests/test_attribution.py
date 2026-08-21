"""The attribution counter reads `red` records off diagnosis claims and nothing else."""

from epure.attribution import count


def _red(culprit, tool, check="conduct/agrees"):
    return {"kind": "diagnosis", "text": "x",
            "red": {"check": check, "culprit": culprit, "tool_named": tool}}


def test_counts_met_named_and_right():
    got = count([_red("harness", "harness"), _red("model", "harness"), _red("model", None),
                 _red("app", "unnamed"), {"kind": "done", "text": "not a red"},
                 {"kind": "diagnosis", "text": "a diagnosis with no red record"}])
    assert (got.met, got.named, got.right) == (4, 2, 1)
    assert got.by_check == {"conduct/agrees": (4, 2, 1)}
    assert got.line().startswith("reds met 4, tool named 2, named right 1")


def test_a_session_filter_narrows_to_its_own_reds():
    a = {**_red("model", "model"), "session": "a"}
    b = {**_red("model", "app"), "session": "b"}
    assert (count([a, b], "a").met, count([a, b], "a").right) == (1, 1)
    assert count([a, b]).met == 2


def test_no_reds_is_zero_not_a_verdict():
    assert count([]).line() == "reds met 0, tool named 0, named right 0"
