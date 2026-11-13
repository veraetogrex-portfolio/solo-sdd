#!/usr/bin/python3
"""Readiness of the lesson-routing stand, without models.

Copies tests/stands/lesson-stand to a temporary folder (removed at the end) and checks: both stand tests fail as
committed; check.sh prints "## Lessons: missing" and three checksum lines for AGENTS.md, "## Lessons: 20 lines" with
no line about async calls for AGENTS.full.md, "AGENTS.md: missing" without AGENTS.md; the stand openspec is valid.
The last line is the summary.
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


tmp = tempfile.mkdtemp(prefix="lesson-stand-")
try:
    s = os.path.join(tmp, "stand")
    shutil.copytree(STAND, s, ignore=shutil.ignore_patterns("__pycache__"))
    code, out = run([sys.executable, "-m", "unittest", "-v"], s)
    check("stand tests fail as committed (2 of 2)",
          code != 0 and "FAILED (failures=2)" in out and out.count("... FAIL") == 2, out)
    code, out = run(["sh", "check.sh"], s)
    sums = re.findall(r"^[0-9a-f]{64}  .*(?:AGENTS\.md|CLAUDE\.md)$|^missing .*$", out, re.M)
    check("check.sh: no Lessons section, three global copies", "## Lessons: missing" in out and len(sums) == 3, out)
    os.replace(os.path.join(s, "AGENTS.full.md"), os.path.join(s, "AGENTS.md"))
    code, out = run(["sh", "check.sh"], s)
    check("check.sh on AGENTS.full.md: 20 lines, none about async",
          "## Lessons: 20 lines" in out and not re.search(r"async|await", out, re.I), out)
    os.remove(os.path.join(s, "AGENTS.md"))
    code, out = run(["sh", "check.sh"], s)
    check("check.sh without AGENTS.md", "AGENTS.md: missing" in out, out)
    if shutil.which("openspec"):
        code, out = run(["openspec", "validate", "--all", "--strict", "--no-interactive"], s)
        check("stand openspec valid", code == 0, out)
    else:
        print("skip stand openspec: no openspec in PATH")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("%d of %d checks passed" % (sum(checks), len(checks)))
sys.exit(0 if all(checks) else 1)
