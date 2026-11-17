#!/usr/bin/env python3
"""Live scenario of settings-delivery-items, steps 1-5: the real `python3 -m solo_sdd config` in a temporary git
project, and the real global/sdd_pr.py merge in that project with only gh faked (first in PATH): a green open PR whose
files the stand names, every gh call written to a log so the stand sees that no merge was requested.

Usage: python3 tests/stands/settings-delivery-items.py (from the repository root)
Prints one line per check and `<n> of 5 checks passed`; code 0 when all passed. The stand creates and removes its
temporary folder itself."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "global/sdd_pr.py"
URL = "https://github.com/o/stand/pull/7"
GH = f"""#!{sys.executable}
import json, os, sys
a, d = sys.argv[1:], os.environ["STAND_D"]
open(d + "/gh.log", "a").write(json.dumps(a) + "\\n")
if a[:2] == ["pr", "view"]:
    print(json.dumps({{"headRefOid": "abc123", "headRefName": "change/x", "baseRefName": "main", "state": "OPEN",
                      "title": "x", "isCrossRepository": False, "body": "", "author": {{"login": "bot"}}}}))
elif a[:2] == ["api", "--paginate"]:
    for name in open(d + "/files.txt").read().split():
        print(json.dumps({{"filename": name, "previous_filename": None, "patch": "@@ -1 +1 @@\\n-a\\n+b\\n"}}))
elif a[:2] == ["pr", "checks"]:
    print(json.dumps([{{"name": "t", "state": "SUCCESS", "bucket": "pass", "link": ""}}]))
elif a[:3] in (["api", "-X", "PUT"], ["api", "-X", "DELETE"]):
    pass
elif a[:1] == ["api"]:
    print(0)
"""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-delivery-items-")).resolve()
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    proj, bin_ = tmp / "p", tmp / "bin"
    bin_.mkdir()
    (bin_ / "gh").write_text(GH)
    (bin_ / "gh").chmod(0o755)
    env = dict(os.environ, PATH=f"{bin_}:{os.environ['PATH']}", STAND_D=str(tmp), PYTHONPATH=str(ROOT))
    subprocess.run(["git", "init", "-q", "-b", "main", str(proj)], check=True, stdin=subprocess.DEVNULL)
    (proj / "solo-sdd/changes").mkdir(parents=True)
    (proj / "AGENTS.md").write_text("# p\n\n## Delivery\n\n- Mode: pr\n- Owner only: `docs/**`\n")

    def sdd(*a):
        p = subprocess.run([sys.executable, "-m", "solo_sdd", "config", *a], cwd=proj, capture_output=True, text=True,
                           env=env, stdin=subprocess.DEVNULL, timeout=60)
        return p.returncode, p.stdout, p.stderr

    def merge(files):
        (tmp / "files.txt").write_text("\n".join(files) + "\n")
        (tmp / "gh.log").write_text("")
        p = subprocess.run([sys.executable, str(PR), "merge", URL, "squash", "abc123"], cwd=proj, capture_output=True,
                           text=True, env=env, stdin=subprocess.DEVNULL, timeout=120)
        puts = [c for c in map(json.loads, (tmp / "gh.log").read_text().splitlines()) if c[:3] == ["api", "-X", "PUT"]]
        return p.returncode, p.stdout.strip(), puts

    results = []

    def check(name, good, shown):
        results.append(good)
        print(("ok " if good else "FAILED ") + name + ": " + shown)

    got = sdd("get", "delivery.owner-only")
    check("1 old item", got == (0, "docs/**\n", "source: AGENTS.md\n"), repr(got))

    s = sdd("set", "delivery.pr-title", "<id>: <summary>")
    g = sdd("get", "delivery.pr-title")
    long = sdd("set", "delivery.deploy", "x" * 201)
    check("2 text set", s[0] == 0 and g == (0, "<id>: <summary>\n", "source: file\n") and long[0] == 1
          and "at most 200 characters" in long[1], "%r %r %r" % (s[:2], g, long[:2]))

    d = sdd("describe", "delivery.pr-title")
    check("3 describe", d[0] == 0 and "  group: delivery" in d[1].splitlines()
          and "  type: text: one line, at most 200 characters" in d[1].splitlines(), repr(d[1].splitlines()[:5]))

    sdd("set", "delivery.owner-only", "deploy/**")
    m = merge(["deploy/prod.yml", "README.md"])
    check("4 owner path", m == (8, "PR #7 waits for the owner: deploy/prod.yml", []), repr(m))

    m = merge(["solo-sdd/config"])
    check("5 config edit", m == (8, "PR #7 waits for the owner: solo-sdd/config", []), repr(m))

    print("%d of %d checks passed" % (results.count(True), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
