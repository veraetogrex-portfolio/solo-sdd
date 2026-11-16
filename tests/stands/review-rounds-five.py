#!/usr/bin/env python3
"""Stand of change review-rounds-five: step 3 of the Live Scenario of its verification.md.

It runs `sync.py push` of this tree into a new empty temporary home and checks that the laid-out spec-next skill and
algorithm are this tree's texts, which name default 5 and the extra round; the wording itself is checked by
tests/test_skill_commands.py. The stand removes its temporary folder; the last line is the summary.
Run from the repository root: python3 tests/stands/review-rounds-five.py
"""
import os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
checks = []


def check(name, good, detail=""):
    checks.append(bool(good))
    print(("ok   " if good else "FAIL ") + name + ("" if good else ": " + str(detail).strip()[-400:]))


def read(path):
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read()


with tempfile.TemporaryDirectory(prefix="review-rounds-") as home:
    os.makedirs(os.path.join(home, ".claude"))
    p = subprocess.run([sys.executable, os.path.join(ROOT, "sync.py"), "push"], cwd=ROOT,
                       env=dict(os.environ, HOME=home), capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=300)
    check("3 sync.py push into a temporary home: exit 0", p.returncode == 0, p.stdout + p.stderr)
    for name, laid, source, word in (
            ("spec-next", (".claude", "skills", "spec-next", "SKILL.md"), ("skills", "spec-next", "SKILL.md"),
             "- Extra round. "),
            ("ALGORITHM.md", (".local", "share", "solo-sdd", "ALGORITHM.md"), ("ALGORITHM.md",),
             "one extra round runs without asking the owner")):
        got, want = read(os.path.join(home, *laid)), read(os.path.join(ROOT, *source))
        check("3 laid-out %s is this tree's text with default 5 and the extra round" % name,
              got is not None and got == want and "default 5" in got and word in got,
              "no copy" if got is None else "differs from the tree or lacks default 5 / %r" % word)

print("%d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
