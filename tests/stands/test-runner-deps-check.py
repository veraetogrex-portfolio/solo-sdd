#!/usr/bin/env python3
"""Stand of change test-runner-deps-check (Requirement: Test imports found before the run).
The real tests/run.py of this working folder runs on this interpreter isolated (-I, an empty temporary
PYTHONUSERBASE its test-file processes inherit), where hypothesis is not found: on tests/test_readme.py and
tests/test_runner.py (which imports hypothesis at top level) it must end with code 2 and a missing-module line
before any file runs; on tests/test_readme.py alone (standard library only) it must run the file. Nothing outside
the temporary folder changes except the git-ignored tests/.last-failed."""
import os
import pathlib
import re
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]

with tempfile.TemporaryDirectory(prefix="deps-check-") as base:
    env = dict(os.environ, PYTHONUSERBASE=base)

    def iso(*args, flags=("-I",)):
        p = subprocess.run([sys.executable, *flags, *args], cwd=REPO, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=300)
        return p.returncode, p.stdout, p.stderr

    # the runner looks imports up in a process started as its test files are: without -I, with the empty user base
    probe = iso("-c", "import importlib.util, sys; print(importlib.util.find_spec('hypothesis') is None); "
                      "print(sys.executable)", flags=())[1].splitlines()
    if probe[:1] != ["True"]:
        print("FAIL hypothesis is visible to the isolated interpreter" if probe[:1] == ["False"]
              else "FAIL the probe of the isolated interpreter printed nothing")
        sys.exit(1)
    exe = probe[1]
    row = next((ln for ln in (REPO / "AGENTS.md").read_text(encoding="utf-8").splitlines()
                if ln.startswith("| Install |")), "")
    install = (re.search(r"`([^`]+)`", row) or [None, None])[1]
    if not install:
        print("FAIL AGENTS.md has no Install row with a command")
        sys.exit(1)
    code1, out1, err1 = iso("tests/run.py", "--jobs", "2", "tests/test_readme.py", "tests/test_runner.py")
    code2, out2, err2 = iso("tests/run.py", "--jobs", "2", "tests/test_readme.py")

line = next((ln for ln in err1.splitlines() if ln.startswith("missing module hypothesis ")), "")
checks = [("isolated run of test_readme and test_runner: code 2, missing module hypothesis naming tests/test_runner.py,"
           " the interpreter and the install command, no ok or FAIL line",
           code1 == 2 and "tests/test_runner.py" in line and exe in line and line.endswith(install)
           and not re.search(r"(?m)^(ok|FAIL) ", out1 + err1)),
          ("isolated run of test_readme alone: code 0, ok tests/test_readme.py",
           code2 == 0 and re.search(r"(?m)^ok tests/test_readme\.py ", out2) is not None)]
for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
if not checks[0][1]:
    print("run 1: code %d\n%s%s" % (code1, out1, err1))
if not checks[1][1]:
    print("run 2: code %d\n%s%s" % (code2, out2, err2))
fails = sum(not g for _, g in checks)
print("test-runner-deps-check: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
