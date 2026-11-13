#!/usr/bin/env python3
"""Live scenario of change test-run-budget, without model calls.

1. `sync.py push --global-rules` into a temporary HOME; every rule of the three requirements is read from the deployed
   spec-next, spec-dispatch, project-init, global rules and algorithm (and this repository's AGENTS.md): one `ok` line per rule.
2. The deployed sdd-eval.py takes the `Tests` row of an AGENTS.md whose `Tests (one)` row stands above it (a pin).
3. The same rules on the texts of the commit before this change (git show): every rule fails there.
Run from the repository root: python3 tests/stands/test-run-budget.py. The temporary folder is removed; the last line
is "SUMMARY: all steps passed" (code 0) or "SUMMARY: N of M steps failed" (code 1)."""
import os, pathlib, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "5221334"  # main before this change: pinned, so the stand runs the same after the merge
ENV = {k: v for k, v in os.environ.items() if k != "HOME"}
DEPLOYED = {"spec-next": ".claude/skills/spec-next/SKILL.md", "spec-dispatch": ".claude/skills/spec-dispatch/SKILL.md",
            "project-init": ".claude/skills/project-init/SKILL.md",
            "rules": ".claude/CLAUDE.md", "algorithm": ".local/share/solo-sdd/ALGORITHM.md"}
SOURCE = {"spec-next": "skills/spec-next/SKILL.md", "spec-dispatch": "skills/spec-dispatch/SKILL.md",
          "project-init": "skills/project-init/SKILL.md",
          "rules": "global/AGENTS.md", "algorithm": "ALGORITHM.md", "agents": "AGENTS.md"}
BUDGET = ("`Tests (one)`", "once after the last code edit", "only when code changed after that run",
          "the failed tests first", "`--reporter=dot`", "only the failure lines")
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
    """(name, the words a text lacks) for every rule of the three requirements."""
    nxt, init, glob, algo, agents = (t[k] for k in ("spec-next", "project-init", "rules", "algorithm", "agents"))
    step6 = part(nxt, "\n6. **Checks**", "\n7. ")
    sec3 = part(glob, "## 3. What", "\n## ")
    row = next((l for l in init.splitlines() if l.startswith("| Commands |")), "")
    cmds = part(agents, "## Commands", "\n## ")
    checks = part(agents, "## Checks", "\n## ")
    return [
        ("two commands: project-init rows", missing(row, ("the `Tests` row", "the `Tests (one)` row"))),
        ("two commands: one test per runner", missing(part(init, "The `Tests (one)` row by runner:", "\n\n"),
                                                     ("unittest", "pytest", "vitest", "jest"))),
        ("two commands: readers take Tests", missing(init, ("takes the `Tests` row only",
                                                            "(the `Tests` row; `Tests (one)` gets no flag)"))),
        ("two commands: dispatcher readers", missing(t["spec-dispatch"], (
            "add the `Tests` row of \"Commands\" (never `Tests (one)`)", "TESTS: <the `Tests` row of AGENTS.md> -> exit"))),
        ("two commands: this repository", missing(cmds, ("\n| Tests | `", "\n| Tests (one) | `python3 tests/<file>.py`"))
         + missing(checks, ("the `Tests` row",)) + (["all tests from the table"] if "all tests from the table" in checks
                                                   else [])),
        ("suite once: spec-next step 6", missing(step6, BUDGET + ("`-q`", "`--silent`", "unittest prints only dots"))),
        ("suite once: Nit fixed in code, dispatcher run", missing(step6, ("A Nit fixed in code", "without a new review round",
                                                                          "the dispatcher's run after merge"))),
        ("suite once: rework after Important", missing(part(nxt, "Only `Important` gives rework by step 5", "\n"), (
            "the tests of the edited module first and the suite once more after the last edit",))),
        ("suite once: global rules section 3", missing(sec3, BUDGET + (
            "the tests of the edited module, the suite once after the edit",))),
        ("suite once: algorithm", missing(part(algo, "\n6. A task is checked", "\n7. "), BUDGET)),
        ("reviewer: step 7a", missing(part(nxt, "\n7a. ", "\n8. "), (
            "the `Tests` command with its result line", "does not rerun the suite",
            "only the single tests it doubts, by `Tests (one)`"))),
    ]


with tempfile.TemporaryDirectory() as t:
    home = pathlib.Path(t) / "home"
    p = run(sys.executable, "sync.py", "push", "--global-rules", env={**ENV, "HOME": str(home)})
    read = lambda f: f.read_text(encoding="utf-8") if f.is_file() else ""
    deployed = {k: read(home / rel) for k, rel in DEPLOYED.items()}
    deployed["agents"] = read(ROOT / "AGENTS.md")
    step("1 push", p.returncode == 0 and all(deployed.values()),
         "code %d, texts not deployed: %s" % (p.returncode, ", ".join(k for k, v in deployed.items() if not v) or "none"))
    for name, lack in rules(deployed):
        step(name, not lack, "lacks: %s" % ("; ".join(lack) or "nothing"))

    copy = pathlib.Path(t) / "copy"
    copy.mkdir()
    (copy / "AGENTS.md").write_text("# p\n\n## Commands\n\n| What | Command |\n|---|---|\n"
                                    "| Tests (one) | `pytest -q <file>` |\n| Tests | `pytest -q` |\n", encoding="utf-8")
    code = ("import importlib.util, sys; s = importlib.util.spec_from_file_location('e', sys.argv[1]); "
            "m = importlib.util.module_from_spec(s); s.loader.exec_module(m); print(m.test_command(sys.argv[2]))")
    p = run(sys.executable, "-c", code, str(home / ".local/bin/sdd-eval.py"), str(copy))
    got = p.stdout.strip()
    step("2 sdd-eval reads the Tests row", got == "pytest -q", "got %r%s" % (got, "" if p.returncode == 0 else
                                                                          "; " + p.stderr.strip()[-200:]))

prev = {k: run("git", "show", "%s:%s" % (BASE, rel)).stdout for k, rel in SOURCE.items()}
if not all(prev.values()):
    step("3 previous text", False, "the commit %s is not in this clone" % BASE)
else:
    passed = [name for name, lack in rules(prev) if not lack]
    step("3 previous text", not passed, "rules of %s that pass on it: %s" % (BASE, ", ".join(passed) or "none"))

failed = results.count(False)
print("SUMMARY: all steps passed" if not failed else "SUMMARY: %d of %d steps failed" % (failed, len(results)))
sys.exit(1 if failed else 0)
