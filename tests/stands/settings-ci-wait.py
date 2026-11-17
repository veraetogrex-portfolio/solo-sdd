#!/usr/bin/env python3
"""Live scenario of settings-ci-wait, steps 1-4: the real global/sdd_pr.py in a temporary git project with its
settings written by the real `python3 -m solo_sdd config set`; only gh is faked (first in PATH) and writes every call
to a log, so the stand sees which requests were sent and in which order.

Usage: python3 tests/stands/settings-ci-wait.py (from the repository root)
Prints one line per check and `<n> of 4 checks passed`; code 0 when all passed. The stand creates and removes its
temporary folder itself."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "global/sdd_pr.py"
URL = "https://github.com/o/stand/pull/7"
RUN = "https://github.com/o/stand/actions/runs/555/job/9"
GH = f"""#!{sys.executable}
import json, os, sys
a, d = sys.argv[1:], os.environ["STAND_D"]
open(d + "/gh.log", "a").write(json.dumps(a) + "\\n")
def state(name, default):
    try:
        return json.load(open(d + "/" + name))
    except OSError:
        return default
if a[:2] == ["pr", "view"]:
    print(json.dumps(dict({{"headRefOid": "abc123", "headRefName": "change/x", "baseRefName": "main", "state": "OPEN",
                           "title": "x", "isCrossRepository": False, "body": "", "author": {{"login": "bot"}}}},
                          **state("view.json", {{}}))))
elif a[:2] == ["pr", "checks"]:
    rows = state("checks.json", None)
    if rows is None:
        sys.stderr.write("no checks reported on the 'change/x' branch\\n")
        sys.exit(1)
    print(json.dumps(rows))
elif a[:2] == ["pr", "list"]:
    print("[]")
elif a[:2] == ["pr", "create"]:
    print("{URL}")
elif a[:2] == ["run", "view"]:
    print("job\\tstep\\tFAIL: test_x (x.T)")
elif a[:2] == ["api", "--paginate"] or a[:3] in (["api", "-X", "PUT"], ["api", "-X", "DELETE"]) or a[:2] == ["pr", "ready"]:
    pass
elif a[:1] == ["api"] and "/code-scanning/" in a[1]:
    print(json.dumps(state("alerts.json", [])))
elif a[:1] == ["api"] and "/rules/branches/" in a[1]:
    print("[]")
elif a[:1] == ["api"] and "/branches/" in a[1]:
    print("{{}}")
elif a[:1] == ["api"]:
    print(0)
"""
GREEN = [{"name": "Checks", "state": "SUCCESS", "bucket": "pass", "link": ""}]
ALERT = {"number": 28, "rule": {"id": "js/bad-code-sanitization"}, "most_recent_instance": {
    "location": {"path": "src/check.ts", "start_line": 102}, "message": {"text": "Improper sanitization."}}}


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-ci-wait-")).resolve()
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    proj, origin, bin_ = tmp / "p", tmp / "origin.git", tmp / "bin"
    bin_.mkdir()
    (bin_ / "gh").write_text(GH)
    (bin_ / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", STAND_D=str(tmp), PYTHONPATH=str(ROOT),
               GIT_AUTHOR_NAME="s", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="s", GIT_COMMITTER_EMAIL="s@s")

    def git(*a):
        subprocess.run(["git", *a], check=True, env=env, stdin=subprocess.DEVNULL, capture_output=True)
    git("init", "-q", "--bare", "-b", "main", str(origin))
    git("init", "-q", "-b", "main", str(proj))
    (proj / "solo-sdd/changes").mkdir(parents=True)
    (proj / "README.md").write_text("r\n")
    git("-C", str(proj), "add", "-A")
    git("-C", str(proj), "commit", "-qm", "init")
    git("-C", str(proj), "remote", "add", "origin", str(origin))
    git("-C", str(proj), "checkout", "-qb", "change/x")

    def sdd(*a):
        p = subprocess.run([sys.executable, "-m", "solo_sdd", "config", *a], cwd=proj, capture_output=True, text=True,
                           env=env, stdin=subprocess.DEVNULL, timeout=60)
        assert p.returncode == 0, p.stdout + p.stderr

    def pr(*a):
        (tmp / "gh.log").unlink(missing_ok=True)
        p = subprocess.run([sys.executable, str(PR), *a], cwd=proj, capture_output=True, text=True, env=env,
                           stdin=subprocess.DEVNULL, timeout=120)
        log = [json.loads(x) for x in (tmp / "gh.log").read_text().splitlines()] if (tmp / "gh.log").exists() else []
        return p, log

    def put(name, value):
        (tmp / name).unlink(missing_ok=True)
        if value is not None:
            (tmp / name).write_text(json.dumps(value))

    def merged(log):
        return any(c[:3] == ["api", "-X", "PUT"] for c in log)

    checks = []

    def check(label, ok, detail):
        checks.append(ok)
        print(("PASS " if ok else "FAIL ") + label + ("" if ok else ": " + detail))

    # 1. the timeout from the file, then the flag winning and ending the wait
    sdd("set", "delivery.ci-timeout", "3600")
    put("checks.json", GREEN)
    p1, _ = pr("wait", URL, "--interval", "1")
    put("checks.json", [{"name": "Checks", "state": "QUEUED", "bucket": "pending", "link": ""}])
    t = time.monotonic()
    p2, _ = pr("wait", URL, "--timeout", "2", "--interval", "1")
    took = time.monotonic() - t
    check("1 limits: timeout 3600 s (file), then timeout 2 s (flag) gives up after %.1f s" % took,
          p1.returncode == 0 and p1.stdout == f"PR #7 {URL} CI: green\n" and "timeout 3600 s (file)" in p1.stderr
          and p2.returncode == 4 and "timeout 2 s (flag)" in p2.stderr and 2 <= took < 15,
          "%r %r / %r %r" % (p1.stdout, p1.stderr, p2.stdout, p2.stderr))
    sdd("unset", "delivery.ci-timeout")

    # 2. CI optional: no checks is none and merges; a red check still blocks
    sdd("set", "delivery.require-ci", "off")
    sdd("set", "delivery.ci-no-checks", "1")
    put("checks.json", None)
    w, _ = pr("wait", URL, "--interval", "1")
    m, mlog = pr("merge", URL, "squash", "abc123")
    put("checks.json", [{"name": "Checks", "state": "FAILURE", "bucket": "fail", "link": RUN}])
    w2, _ = pr("wait", URL, "--interval", "1")
    m2, mlog2 = pr("merge", URL, "squash", "abc123")
    check("2 require-ci off: CI: none code %d, merge code %d with the request; red: wait code %d, merge code %d"
          % (w.returncode, m.returncode, w2.returncode, m2.returncode),
          w.returncode == 0 and w.stdout == f"PR #7 {URL} CI: none\n" and m.returncode == 0 and merged(mlog)
          and w2.returncode == 3 and w2.stdout.startswith(f"PR #7 {URL} CI: red\n") and m2.returncode == 1
          and not merged(mlog2), "%r %r %r %r" % (w.stdout, m.stderr, w2.stdout, m2.stderr))
    sdd("unset", "delivery.require-ci")
    sdd("unset", "delivery.ci-no-checks")

    # 3. code scanning as a warning
    sdd("set", "delivery.code-scanning", "warn")
    put("checks.json", GREEN)
    put("alerts.json", [ALERT])
    w, _ = pr("wait", URL, "--interval", "1")
    m, mlog = pr("merge", URL, "squash", "abc123")
    check("3 code-scanning warn: green with the alert line, code %d; merge code %d" % (w.returncode, m.returncode),
          w.returncode == 0 and w.stdout.splitlines() == [
              f"PR #7 {URL} CI: green", "#28 js/bad-code-sanitization src/check.ts:102 Improper sanitization."]
          and m.returncode == 0 and merged(mlog), "%r %r" % (w.stdout, m.stderr))
    sdd("unset", "delivery.code-scanning")
    put("alerts.json", None)

    # 4. a draft PR marked ready before the merge request; the branch kept
    sdd("set", "delivery.draft", "on")
    sdd("set", "delivery.delete-branch", "off")
    o, olog = pr("open", str(proj), "main", "Title")
    put("view.json", {"isDraft": True})
    m, mlog = pr("merge", URL, "squash", "abc123")
    create = [c for c in olog if c[:2] == ["pr", "create"]]
    order = [c[:3] for c in mlog if c[:2] == ["pr", "ready"] or c[:3] == ["api", "-X", "PUT"]]
    check("4 draft on: pr create --draft, then pr ready before the merge request; delete-branch off: no delete",
          o.returncode == 0 and len(create) == 1 and "--draft" in create[0] and m.returncode == 0
          and order == [["pr", "ready", URL], ["api", "-X", "PUT"]]
          and not any(c[:3] == ["api", "-X", "DELETE"] for c in mlog), "%r %r %r %r" % (o.stderr, create, m.stderr, order))

    print("%d of %d checks passed" % (sum(checks), len(checks)))
    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
