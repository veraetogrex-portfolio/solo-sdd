#!/usr/bin/python3
"""Live scenario of change settings-change-limits, steps 1-3, on the real `solo-sdd validate` and `config set`.

In a temporary project with one change `demo`, run as `python3 -m solo_sdd` from this repository:
1. 12 tasks and no solo-sdd/config: `validate demo` fails with `too many tasks: 12 > 10 (default)`.
2. `config set process.max-tasks 14`: `validate demo` passes.
3. `config set process.requirement-max-chars 300` and a requirement of 400 characters: `validate demo` fails naming
   `400 > 300 (file)`.
Run from the repository root: python3 tests/stands/settings-change-limits.py. The temporary folder is removed; the
last line is the summary."""
import os, pathlib, subprocess, sys, tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PROPOSAL = ("# Proposal\n\n## Why\n\nA reason.\n\n## What Changes\n\n- A change.\n\n## Capabilities\n\n"
            "### New Capabilities\n- `foo`: a thing.\n\n### Modified Capabilities\n\n## Impact\n\n`foo.py`.\n\n"
            "## Out of Scope\n\n- `other`.\n\n## Depends On\n\nnone\n\n## Source\n\n\"Do it\" (the owner).\n")
VERIFICATION = "## Live Scenario\n\nRun it.\n\n## Needs\n\nnone\n\n## Fallback\n\nNot needed.\n"
SPEC = ("## Purpose\n\nDefines the foo capability of the toy project for the change limits stand.\n\n"
        "## ADDED Requirements\n\n### Requirement: Foo\nThe system SHALL %s.\n\n"
        "#### Scenario: S\n- **WHEN** a\n- **THEN** b\n")


def sdd(proj, *args):
    p = subprocess.run([sys.executable, "-m", "solo_sdd"] + list(args), cwd=proj, capture_output=True, text=True,
                       env=dict(os.environ, PYTHONPATH=str(REPO)), stdin=subprocess.DEVNULL, timeout=60)
    return p.returncode, p.stdout + p.stderr


with tempfile.TemporaryDirectory() as t:
    proj = pathlib.Path(t)
    change = proj / "solo-sdd" / "changes" / "demo"
    (change / "specs" / "foo").mkdir(parents=True)
    (proj / "solo-sdd" / "project.md").write_text("Intent: a toy.\n")
    (change / "proposal.md").write_text(PROPOSAL)
    (change / "verification.md").write_text(VERIFICATION)
    (change / "tasks.md").write_text("## 1. Code\n\n" + "".join("- [ ] 1.%d t\n" % i for i in range(1, 11))
                                     + "\n## 2. Acceptance\n\n- [ ] 2.1 Live\n- [ ] 2.2 Archive\n")
    (change / "specs" / "foo" / "spec.md").write_text(SPEC % "do foo")
    checks = []

    code, out = sdd(proj, "validate", "demo")
    checks.append(("1 twelve tasks, the default limit: fails", code == 1
                   and "too many tasks: 12 > 10 (default)" in out, out))

    set_code, set_out = sdd(proj, "config", "set", "process.max-tasks", "14")
    code, out = sdd(proj, "validate", "demo")
    checks.append(("2 process.max-tasks 14: passes", set_code == 0 and (code, out) == (0, "0 errors\n"), set_out + out))

    set_code, set_out = sdd(proj, "config", "set", "process.requirement-max-chars", "300")
    (change / "specs" / "foo" / "spec.md").write_text(SPEC % ("x" * 382))  # "The system SHALL " + 382 + "." = 400
    code, out = sdd(proj, "validate", "demo")
    checks.append(("3 a 400 character requirement over a file limit of 300: fails", set_code == 0 and code == 1
                   and "Foo: 400 > 300 (file)" in out, set_out + out))

    for step, good, why in checks:
        print("%s %s%s" % ("ok    " if good else "FAILED", step, "" if good else ": " + why.strip()))
    passed = sum(g for _, g, _ in checks)
    print("settings-change-limits: %d of %d checks passed" % (passed, len(checks)))
sys.exit(0 if passed == len(checks) else 1)
