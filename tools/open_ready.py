"""Public-readiness gate: is this repo, and everything it remembers, safe to open?

`python tools/open_ready.py` scans the working tree; `--history` scans every commit's diff as
well. Exit 1 on any finding, so this blocks a merge. Stdlib only, no dependencies — it must be
runnable on a bare checkout, before anything is installed, and it must never be the reason CI
is red for an unrelated reason.

This repo was born licensed and should stay open-ready as it grows, so that flipping it public
is a switch rather than a project. Two properties, both cheap now and expensive later:

**Nothing personal is ever committed.** Not a home path, not an address, not a token, not a
fixture derived from anyone's real data. History is forever and a scrub is a rewrite.

**This substrate names its dependencies and nothing else.** It knows `quern` and
`flight-recorder`, it publishes through `quern-registry`, and it does not know who uses it. A
library that names its consumers has inverted the dependency it depends on.

Which is why the repo check is an **allowlist and not a denylist**, and that is not a
stylistic preference: a denylist of the projects this repo may not mention would be a list of
this repo's consumers, sitting in this repo, which is exactly the reference it exists to
forbid. So it enumerates what may be named — the dependencies — and every other estate repo is
a finding by construction, including the ones that do not exist yet.

The patterns below are written so they do not match their own source. That is deliberate too:
a scanner that has to exempt itself has a hole in it exactly where someone would hide
something.
"""

from __future__ import annotations

import re
import subprocess
import sys

# What this substrate is allowed to know: what it stands on, and where it publishes. Adding a
# name here is a claim that this repo DEPENDS on it. If you are adding one to silence a
# finding about something that uses epure, the finding is right and you are wrong.
ALLOWED_REPOS = frozenset({"quern", "flight-recorder", "quern-registry", "epure"})

# Third-party owners whose repos this repo legitimately references (CI actions, toolchains).
# Estate references go through ALLOWED_REPOS above, whatever the URL shape.
ALLOWED_OWNERS = frozenset({"actions", "astral-sh"})

ESTATE = "xag"

FINDINGS: list[tuple[str, re.Pattern, str]] = [
    (
        "a home directory — someone's machine, in the history forever",
        # Doubled backslashes here, single ones in what it matches: this line is not a hit.
        re.compile(r"[Cc]:\\Users\\|/home/[a-z][a-z0-9_-]+/|/Users/[a-z][a-z0-9_-]+/"),
        "Use a tmp_path fixture or a relative path.",
    ),
    (
        "an email address",
        re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
        "Security contact goes through GitHub's private vulnerability reporting "
        "(see SECURITY.md), which needs no address in the tree.",
    ),
    (
        "something shaped like a credential",
        re.compile(r"gh[pousr]_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{20,}"
                   r"|sk-[A-Za-z0-9-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"),
        "Rotate it — assume it is burnt the moment it is committed — and keep it out of git.",
    ),
]

# A reference to an estate repo, in every shape one actually appears in: bare owner-slash-name,
# an https URL, a git URL. (Written without an example, because an example would be a reference,
# and the first thing this scanner ever caught was a comment here that spelled one out.)
ESTATE_REF = re.compile(rf"\b{ESTATE}/([A-Za-z0-9._-]+)")
GITHUB_URL = re.compile(r"github\.com[/:]([A-Za-z0-9._-]+)/([A-Za-z0-9._-]+)")


def _repo(name: str) -> str:
    """A captured repo name, as it would be written down: trailing punctuation from the prose
    around it, and the `.git` a clone URL carries, are not part of the name."""
    return name.rstrip(".,;:)\"'").removesuffix(".git").lower()


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if f]


def _scan(text: str, where: str, out: list[str]) -> None:
    for i, line in enumerate(text.splitlines(), 1):
        for what, pattern, fix in FINDINGS:
            m = pattern.search(line)
            if m:
                # The finding names the RULE and never the match: this output lands in CI logs,
                # and a tripwire that quotes the credential it caught has become the leak.
                out.append(f"{where}:{i}: {what}. {fix}")

        for name in ESTATE_REF.findall(line):
            if _repo(name) not in ALLOWED_REPOS:
                out.append(f"{where}:{i}: names an estate repo this one does not depend on. "
                           f"A substrate knows its dependencies, never its clients.")
        for owner, repo in GITHUB_URL.findall(line):
            if owner == ESTATE and _repo(repo) not in ALLOWED_REPOS:
                out.append(f"{where}:{i}: links to an estate repo this one does not depend on. "
                           f"A substrate knows its dependencies, never its clients.")
            elif owner != ESTATE and owner not in ALLOWED_OWNERS:
                out.append(f"{where}:{i}: links to '{owner}', which is not a declared "
                           f"dependency or a known toolchain. Deliberate?")


def scan_tree() -> list[str]:
    out: list[str] = []
    for path in _tracked_files():
        try:
            with open(path, encoding="utf-8") as f:
                _scan(f.read(), path, out)
        except (UnicodeDecodeError, OSError):
            continue  # binary or unreadable: nothing to read, nothing to leak in text
    return out


def scan_history() -> list[str]:
    """Every commit's diff. The working tree being clean says nothing about what git remembers,
    and `git log -p` is what an auditor runs the day after this goes public."""
    log = subprocess.run(["git", "log", "-p", "--no-color"],
                         capture_output=True, text=True, errors="replace", check=True)
    out: list[str] = []
    commit = "?"
    for line in log.stdout.splitlines():
        if line.startswith("commit "):
            commit = line.split()[1][:9]
        elif line.startswith("+") and not line.startswith("+++"):
            _scan(line[1:], f"history {commit}", out)
    return out


def main(argv: list[str]) -> int:
    findings = scan_tree()
    if "--history" in argv:
        findings += scan_history()

    if not findings:
        scope = "tree and history" if "--history" in argv else "working tree"
        print(f"open-ready: nothing to scrub in the {scope}.")
        return 0

    print(f"open-ready: {len(findings)} finding(s) — this repo is not safe to open.\n")
    for f in dict.fromkeys(findings):  # the same line can trip two rules; say it once
        print(f"  {f}")
    print("\nHistory is forever. Fix it before it is committed, not after it is published.")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
