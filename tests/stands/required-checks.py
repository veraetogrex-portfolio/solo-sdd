#!/usr/bin/env python3
"""Live scenario of pr-wait-required without a repository (Fallback): the real global/sdd_pr.py wait
against a fake gh first in PATH. The fake returns branch rules with a required `PR title` and a list
of checks; the stuck-check deadline of 300 s is replaced by the parameter --stuck 1.

Usage: python3 tests/stands/required-checks.py
Code 0 means every scenario matched. The stand creates and removes its temporary folder itself."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "global/sdd_pr.py"
URL = "https://github.com/o/stand/pull/1"
RULES = [{"type": "required_status_checks", "parameters": {
    "required_status_checks": [{"context": "PR title"}]}}]
CHECKS = {"name": "Checks", "state": "SUCCESS", "bucket": "pass", "link": ""}
CODEQL = {"name": "CodeQL", "state": "SUCCESS", "bucket": "pass", "link": ""}
TITLE_QUEUED = {"name": "PR title", "state": "QUEUED", "bucket": "pending", "link": ""}
TITLE_PASS = {"name": "PR title", "state": "SUCCESS", "bucket": "pass", "link": ""}
WARN = "warning: branch rules not read, required checks not checked"

GH = f"""#!{sys.executable}
import json, os, sys
cfg = json.load(open(os.environ["STAND_CFG"]))
a = sys.argv[1:]
if a[:2] == ["pr", "view"]:
    print(json.dumps({{"baseRefName": "main"}}))
elif a[:2] == ["pr", "checks"]:
    print(json.dumps(cfg["checks"]))
elif a[:1] == ["api"] and "/code-scanning/" in a[1]:  # code scanning is not enabled in the stand
    sys.stderr.write("gh: no analysis found (HTTP 404)\\n")
    sys.exit(1)
elif a[:1] == ["api"]:
    key = "rules" if "/rules/" in a[1] else "branch"
    if cfg.get(key) == "fail":
        sys.stderr.write("gh: Forbidden (HTTP 403)\\n")
        sys.exit(1)
    print(json.dumps(cfg.get(key, [] if key == "rules" else {{}})))
else:
    sys.exit(1)
"""

# name, fake setup, expected (code, stdout, stderr)
CASES = [
    ("required check stuck in the queue", {"rules": RULES, "checks": [CHECKS, CODEQL, TITLE_QUEUED]},
     (4, f"PR #1 {URL} CI: infra\nrequired check did not start: PR title", "")),
    ("required check not in the list", {"rules": RULES, "checks": [CHECKS, CODEQL]},
     (4, f"PR #1 {URL} CI: infra\nrequired check did not start: PR title", "")),
    ("required check passed", {"rules": RULES, "checks": [CHECKS, TITLE_PASS]},
     (0, f"PR #1 {URL} CI: green", "")),
    ("no required checks", {"checks": [CHECKS, CODEQL]},
     (0, f"PR #1 {URL} CI: green", "")),
    ("rules not readable", {"rules": "fail", "checks": [CHECKS, CODEQL]},
     (0, f"PR #1 {URL} CI: green", WARN)),
]


def main():
    d = Path(tempfile.mkdtemp(prefix="stand-required-"))
    try:
        (d / "gh").write_text(GH)
        (d / "gh").chmod(0o755)
        env = dict(os.environ, PATH=f"{d}:{os.environ['PATH']}", STAND_CFG=str(d / "cfg.json"))
        ok = 0
        for name, cfg, want in CASES:
            (d / "cfg.json").write_text(json.dumps(cfg))
            t = time.monotonic()
            p = subprocess.run([sys.executable, str(SCRIPT), "wait", URL, "--timeout", "30",
                                "--interval", "0.2", "--stuck", "1"],
                               capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env, timeout=60)
            got = (p.returncode, p.stdout.strip(), p.stderr.strip())
            good = got == want
            ok += good
            print(f"{'ok  ' if good else 'FAIL'} {name}: code {p.returncode}, {time.monotonic() - t:.1f} s, "
                  f"{p.stdout.strip().replace(chr(10), ' | ')}" + (f" | stderr: {got[2]}" if got[2] else ""))
            if not good:
                print(f"     expected: {want}")
        print(f"total: {ok} of {len(CASES)}")
        return 0 if ok == len(CASES) else 1
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
