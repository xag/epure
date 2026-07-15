# Contributing

Short, because most of it is checked rather than asked for.

```bash
uv sync
uv run pytest                    # the tests
uv run python -m epure.check     # the design ledger. Exit 1 while any rule is red.
python tools/open_ready.py       # nothing personal, no consumers named
```

All three run in CI. The last two are gates, not reports.

## The ledger is not a changelog

A non-obvious decision goes into `epure/tree.py` as it is made — with the alternatives it
rejected, as nodes. A belief held provisionally goes in as a `hypothesis`, carrying the
observation that would kill it. Something known-unsound that we are shipping anyway goes in as
a `debt`, carrying the condition that discharges it.

This is not paperwork; it is the thing that makes the caveat *fire*. A decision naming no
rejected alternative is red. A belief nothing could disprove is red. And a red node is never
discharged by editing the ledger — only by doing the work it names.

Keep the beliefs that turned out wrong. A ledger that deletes its errors is a ledger that will
hold them again.

## This repo names its dependencies and nothing else

It knows `quern` and `flight-recorder`, it publishes through `quern-registry`, and it does not know
who uses it — not in the README, not in a docstring, not in a test fixture. `tools/open_ready.py`
enforces it, and it does so with an allowlist, because a list of the projects we may *not*
mention would be a list of our consumers sitting in our own source.

## Fixtures are invented

Every fixture, every example tape, every model in a test is a synthetic, neutral domain — a
turnstile, a lamp, a vending machine. Nothing derived from anyone's real system, ever, and that
is not about secrets: a fixture drawn from a real app teaches the substrate that app's
accidents, and the accidents are what we are trying to see past.

Nothing personal enters the history. History is forever; a scrub is a rewrite.
