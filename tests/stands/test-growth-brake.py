#!/usr/bin/env python3
"""Live scenario of change test-growth-brake, without model calls.

1. `sync.py push --global-rules` into a temporary HOME; every rule of the five requirements is read from the deployed
   spec-plan, spec-analyze, spec-next and global rules: one `ok` line per rule.
2. The same rules on the texts of the commit before this change (git show): every rule fails there.
Run from the repository root: python3 tests/stands/test-growth-brake.py. The temporary folder is removed; the last line
is "SUMMARY: all steps passed" (code 0) or "SUMMARY: N of M steps failed" (code 1)."""
import os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "157cf51"  # main before this change: pinned, so the stand runs the same after the merge
ENV = {k: v for k, v in os.environ.items() if k != "HOME"}
DEPLOYED = {"spec-plan": ".claude/skills/spec-plan/SKILL.md", "spec-analyze": ".claude/skills/spec-analyze/SKILL.md",
            "spec-next": ".claude/skills/spec-next/SKILL.md", "rules": ".claude/CLAUDE.md"}
SOURCE = {"spec-plan": "skills/spec-plan/SKILL.md", "spec-analyze": "skills/spec-analyze/SKILL.md",
          "spec-next": "skills/spec-next/SKILL.md", "rules": "global/AGENTS.md"}
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def run(*args, env=None):
    return subprocess.run(list(args), cwd=ROOT, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          timeout=600)


def part(text, start, end):
    return text.split(start, 1)[1].split(end, 1)[0] if start in text else ""


def missing(text, words):
    return [w for w in words if w not in text]


def rules(t):
    """(name, the words a text lacks) for every rule of the five requirements."""
    plan = part(t["spec-plan"], "## Writing rules", "\n## Bug fix")
    pass1 = part(t["spec-analyze"], "**1. Coverage.**", "\n**2. ")
    nxt = t["spec-next"]
    step5, step9 = part(nxt, "\n5. **Implementation", "\n6. "), part(nxt, "\n9. **Closing", "\n10. ")
    important = part(part(nxt, "\n7a. ", "\n8. "), "`Important`:", "`Nit`")
    report = part(nxt, "## Report", "```\n\n")
    glob = part(t["rules"], "## 3. What", "\n## ")
    return [
        ("no repeated tests: spec-plan", missing(plan, (
            "needs no second test of the same behaviour", "a new row of that test's table, not a new test function",
            "A property test pass 3a of `spec-analyze` requires and a bug fix's test of the bug scenario are not repeats"))),
        ("untested code: spec-plan", missing(plan, (
            "a getter", "a DTO", "configuration", "a thin library wrapper", "a private function a scenario test reaches",
            "a one-off script (a stand checks it)", "what a separate CI step checks"))),
        ("no repeated tests: spec-analyze pass 1", missing(pass1, (
            "A scenario a Live Scenario step checks needs no unit test", "no finding"))),
        ("no repeated tests: spec-next step 7a", missing(important, (
            "a test that repeats a scenario a higher-level test already covers",
            "except a property test `spec-analyze` pass 3a requires and a bug fix's test of the bug scenario"))
         + missing(part(nxt, "\n7a. ", "\n8. "), ("tests that repeat a scenario a higher-level test covers, except the required tests",))),
        ("no repeated tests: global rules", missing(glob, (
            "gets no second test (a required property test and a bug's regression test excepted)",
            "a row of the existing test", "private functions a scenario test reaches", "what a CI step checks"))),
        ("doubles: spec-plan", missing(plan, (
            "Test doubles only for external I/O (the network, paid APIs) and the clock", "a temporary real one",
            "an in-memory fake", "the module under test is never mocked"))),
        ("doubles: global rules", missing(glob, (
            "Doubles only for external I/O (the network, paid APIs) and the clock", "the module under test is never mocked"))),
        ("tests change: spec-plan", missing(plan, (
            "only by a task that names a MODIFIED or REMOVED requirement", "names the test and keeps every assertion"))),
        ("tests change: spec-next step 5", missing(step5, (
            "is fixed, not the test", "names a MODIFIED or REMOVED requirement", "keeps every assertion"))),
        ("tests change: global rules", missing(glob, (
            "An existing assertion changes or goes only", "MODIFIED or REMOVED requirement", "setup, cost or layout keeps every assertion"))),
        ("property budget: spec-plan", missing(plan, (
            "starts a process or creates a repository per example", "`max_examples`",
            "in its task and in the test, the same number in both"))),
        ("suite time: spec-next step 9", missing(step9, (
            "`Result` and the report hold the bare line `Suite: <before> (<change>) -> <after>`",
            "`Suite: n/a -> <after>`", "sorts last",
            "no extra suite run on the base branch"))),
        ("suite time: spec-next report", missing(report, ("\nSuite: <before> (<change>) -> <after>",))),
    ]


with tempfile.TemporaryDirectory() as t:
    home = pathlib.Path(t) / "home"
    p = run(sys.executable, "sync.py", "push", "--global-rules", env={**ENV, "HOME": str(home)})
    read = lambda f: f.read_text(encoding="utf-8") if f.is_file() else ""
    deployed = {k: read(home / rel) for k, rel in DEPLOYED.items()}
    step("1 push", p.returncode == 0 and all(deployed.values()),
         "code %d, texts not deployed: %s" % (p.returncode, ", ".join(k for k, v in deployed.items() if not v) or "none"))
    for name, lack in rules(deployed):
        step(name, not lack, "lacks: %s" % ("; ".join(lack) or "nothing"))

prev = {k: run("git", "show", "%s:%s" % (BASE, rel)).stdout for k, rel in SOURCE.items()}
if not all(prev.values()):
    step("2 previous text", False, "the commit %s is not in this clone" % BASE)
else:
    passed = [name for name, lack in rules(prev) if not lack]
    step("2 previous text", not passed, "rules of %s that pass on it: %s" % (BASE, ", ".join(passed) or "none"))

failed = results.count(False)
print("SUMMARY: all steps passed" if not failed else "SUMMARY: %d of %d steps failed" % (failed, len(results)))
sys.exit(1 if failed else 0)
