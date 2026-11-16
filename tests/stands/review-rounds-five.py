#!/usr/bin/env python3
"""Stand of change review-rounds-five: the Live Scenario of its verification.md, steps 1-3.

Step 1 runs `python3 -m solo_sdd config get process.review-rounds` of this tree in a new temporary git project with
`solo-sdd/` and no config file. Step 2 runs `scripts/sync_blocks.py --check` and reads every settings block copy.
Step 3 runs `sync.py push` into a new empty temporary home and reads the laid-out spec-next skill and algorithm, and
the review row of docs/stop-conditions.md. The stand removes its temporary folders; the last line is the summary.
Run from the repository root: python3 tests/stands/review-rounds-five.py
"""
import os, re, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
checks = []


def check(name, good, detail=""):
    checks.append(bool(good))
    print(("ok   " if good else "FAIL ") + name + ("" if good else ": " + str(detail).strip()[-400:]))


def run(cwd, *args, home=None):
    env = dict(os.environ, PYTHONPATH=ROOT, **({"HOME": home} if home else {}))
    p = subprocess.run([sys.executable, *args], cwd=cwd, env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=300)
    return p.returncode, p.stdout, p.stderr


def flat(path):
    with open(path, encoding="utf-8") as f:
        return re.sub(r"\s+", " ", f.read())


with tempfile.TemporaryDirectory(prefix="review-rounds-") as tmp:
    project = os.path.join(tmp, "project")
    os.makedirs(os.path.join(project, "solo-sdd", "changes"))
    subprocess.run(["git", "init", "-q", "-b", "main", project], check=True)
    got = run(project, "-m", "solo_sdd", "config", "get", "process.review-rounds")
    check("1 config get without a file value: 5, source: default", got == (0, "5\n", "source: default\n"), got)

    got = run(ROOT, "scripts/sync_blocks.py", "--check")
    check("2 sync_blocks --check: no output, exit 0", got == (0, "", ""), got)
    lines = [(path, line) for d in ("solo_sdd", "global") for path in sorted(os.listdir(os.path.join(ROOT, d)))
             if path.endswith(".py")
             for line in open(os.path.join(ROOT, d, path), encoding="utf-8").read().splitlines()
             if '"process.review-rounds": ("int"' in line]
    check("2 every settings block copy has default \"5\" (%d copies)" % len(lines),
          len(lines) == 5 and all('"5"' in line for _, line in lines), lines)

    home = os.path.join(tmp, "home")
    os.makedirs(os.path.join(home, ".claude"))
    code, out, err = run(ROOT, "sync.py", "push", home=home)
    check("3 sync.py push into a temporary home: exit 0", code == 0, out + err)
    skill = os.path.join(home, ".claude", "skills", "spec-next", "SKILL.md")
    algo = os.path.join(home, ".local", "share", "solo-sdd", "ALGORITHM.md")
    for name, path, words in (
            ("laid-out spec-next", skill, ("(default 5; no `solo-sdd` command: 5)",
                                           "every `Important` open after it has all its places in lines the rework "
                                           "before that round changed", "There is no second extra round",
                                           "extra round: ran | did not run")),
            ("laid-out ALGORITHM.md", algo, ("default 5", "one extra round runs without asking the owner",
                                             "there is no second extra round")),
            ("docs/stop-conditions.md", os.path.join(ROOT, "docs", "stop-conditions.md"),
             ("`process.review-rounds`, default 5", "one extra round runs without asking",
              "every open `Important` lies in the lines of the last rework, never a second one"))):
        text = flat(path) if os.path.isfile(path) else ""
        missing = [w for w in words if w not in text]
        check("3 %s names default 5 and the extra round" % name, text and not missing, missing or "no file")

print("%d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
