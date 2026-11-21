#!/usr/bin/python3
"""Readiness of the lesson-routing stand, without models.

Copies tests/stands/lesson-stand to a temporary folder (removed at the end) and checks: both stand tests fail as
committed; check.sh prints "## Lessons: missing" and three checksum lines for AGENTS.md, "## Lessons: 20 lines" with
no line about async calls for AGENTS.full.md, "AGENTS.md: missing" without AGENTS.md; for AGENTS.long.md in a
committed copy "## Lessons: 20 lines", "over 300: 1", "missing ids: none", "lost: 0", and "lost: 1" once the glued line
is deleted; with the glued line shortened and linked, "missing ids: retries" and "lost: 1" while its old text
stands under another id, "missing ids: none" and "lost: 0" under its own; a check.sh without its length count
fails the AGENTS.long.md check; the stand openspec is valid. The last line is the
summary.
"""
import os, re, shutil, subprocess, sys, tempfile

STAND = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lesson-stand")
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else "\n" + detail))


def run(cmd, cwd):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout + p.stderr


GIT = ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.invalid", "-c", "commit.gpgsign=false",
       "-c", "core.hooksPath=/dev/null", "-c", "init.defaultBranch=main"]
LENGTH = 'print("over 300: %d" % sum(len(t) > 300 for t, _ in now))'


def long_copy(name, check_sh=None):
    """A committed copy of the stand with AGENTS.long.md as AGENTS.md, optionally with another check.sh text."""
    d = os.path.join(tmp, name)
    shutil.copytree(STAND, d, ignore=shutil.ignore_patterns("__pycache__"))
    os.replace(os.path.join(d, "AGENTS.long.md"), os.path.join(d, "AGENTS.md"))
    if check_sh is not None:
        with open(os.path.join(d, "check.sh"), "w", encoding="utf-8") as f:
            f.write(check_sh)
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-qm", "stand"]):
        code, out = run(GIT + cmd, d)
        if code:
            raise SystemExit("git %s: %s" % (cmd[0], out))
    return d


def long_counts(out):
    lines = out.splitlines()
    return all(line in lines for line in ("## Lessons: 20 lines", "over 300: 1", "missing ids: none", "lost: 0"))


tmp = tempfile.mkdtemp(prefix="lesson-stand-")
try:
    s = os.path.join(tmp, "stand")
    shutil.copytree(STAND, s, ignore=shutil.ignore_patterns("__pycache__"))
    code, out = run([sys.executable, "-m", "unittest", "-v"], s)
    check("stand tests fail as committed (2 of 2)",
          code != 0 and "FAILED (failures=2)" in out and out.count("... FAIL") == 2, out)
    code, out = run(["sh", "check.sh"], s)
    sums = re.findall(r"^[0-9a-f]{64}  .*(?:AGENTS\.md|CLAUDE\.md)$|^missing /.*$", out, re.M)
    check("check.sh: no Lessons section, three global copies", "## Lessons: missing" in out and len(sums) == 3, out)
    os.replace(os.path.join(s, "AGENTS.full.md"), os.path.join(s, "AGENTS.md"))
    code, out = run(["sh", "check.sh"], s)
    check("check.sh on AGENTS.full.md: 20 lines, none about async",
          "## Lessons: 20 lines" in out and not re.search(r"async|await", out, re.I), out)
    os.remove(os.path.join(s, "AGENTS.md"))
    code, out = run(["sh", "check.sh"], s)
    check("check.sh without AGENTS.md", "AGENTS.md: missing" in out, out)
    d = long_copy("long")
    code, out = run(["sh", "check.sh"], d)
    check("check.sh on AGENTS.long.md: 20 lines, over 300: 1, missing ids: none, lost: 0",
          long_counts(out) and "retries a paid call" in out and not re.search(r"async|await", out, re.I), out)
    with open(os.path.join(d, "AGENTS.md"), encoding="utf-8") as f:
        kept = [line for line in f if "retries a paid call" not in line]
    with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8") as f:
        f.writelines(kept)
    code, out = run(["sh", "check.sh"], d)
    check("check.sh after the glued line is deleted: lost: 1", "lost: 1" in out.splitlines(), out)
    glued = [line for line in open(os.path.join(STAND, "AGENTS.long.md"), encoding="utf-8")
             if "retries a paid call" in line][0]
    short = "- Every retry has a maximum count and a backoff. ([full text](LESSONS.md#retries))\n"
    with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8") as f:
        f.writelines(short if line == glued else line
                     for line in open(os.path.join(STAND, "AGENTS.long.md"), encoding="utf-8"))
    for head, want in (("other", ("over 300: 0", "missing ids: retries", "lost: 1")),
                       ("retries", ("over 300: 0", "missing ids: none", "lost: 0"))):
        with open(os.path.join(d, "LESSONS.md"), "w", encoding="utf-8") as f:
            f.write("# Lessons\n\n### %s\n\n%s\n" % (head, glued[2:].strip()))
        code, out = run(["sh", "check.sh"], d)
        check("check.sh, glued line shortened, its old text under ### %s: %s" % (head, ", ".join(want)),
              all(w in out.splitlines() for w in want), out)
    with open(os.path.join(STAND, "check.sh"), encoding="utf-8") as f:
        source = f.read()
    mutated = source.replace(LENGTH, 'print("over 300: 0")')
    code, out = run(["sh", "check.sh"], long_copy("mutant", mutated))
    check("check.sh without its length count fails the AGENTS.long.md check",
          LENGTH in source and mutated != source and not long_counts(out), out)
    if shutil.which("openspec"):
        code, out = run(["openspec", "validate", "--all", "--strict", "--no-interactive"], s)
        check("stand openspec valid", code == 0, out)
    else:
        print("skip stand openspec: no openspec in PATH")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("%d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
