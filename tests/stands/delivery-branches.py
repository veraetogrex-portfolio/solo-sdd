#!/usr/bin/env python3
"""Live scenario of delivery-branches without a GitHub repository (Fallback): the real global/sdd_pr.py and
global/sdd_worktree.py, real git, a bare repository with dev, staging, release/1.9.0, release/1.10.0 and main
(default main) instead of the remote. Only gh is faked (first in PATH): it keeps PRs in a file, merges a PR
into its base branch in a helper clone and logs every call.

Usage: python3 tests/stands/delivery-branches.py (from the repository root)
Code 0: every step matched. The stand creates and removes its temporary folder itself."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PR = ROOT / "global/sdd_pr.py"
WT = ROOT / "global/sdd_worktree.py"
GITENV = dict(GIT_AUTHOR_NAME="stand", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="stand", GIT_COMMITTER_EMAIL="s@s")

GH = f"""#!{sys.executable}
import json, os, re, subprocess, sys
d, bare = os.environ["STAND_D"], os.environ["STAND_BARE"]
a = sys.argv[1:]
open(d + "/gh.log", "a").write(json.dumps(a) + "\\n")
state = json.load(open(d + "/state.json"))
def save():
    json.dump(state, open(d + "/state.json", "w"))
def git(*x, cwd=None):
    return subprocess.run(["git", *x], capture_output=True, text=True, cwd=cwd)
def find(url):
    n = int(re.search(r"/pulls?/(\\d+)", url).group(1))
    return next(p for p in state["prs"] if p["n"] == n)
def url(p):
    return "https://github.com/o/stand/pull/%d" % p["n"]
def opt(name):
    return a[a.index(name) + 1] if name in a else None
if a[:2] == ["pr", "list"]:
    print(json.dumps([{{"number": p["n"], "url": url(p)}} for p in state["prs"] if p["head"] == opt("--head")
                      and p["state"] == "OPEN" and opt("--base") in (None, p["base"])]))
elif a[:2] == ["pr", "create"]:
    p = {{"n": len(state["prs"]) + 1, "head": opt("--head"), "base": opt("--base"), "title": opt("--title"),
         "state": "OPEN"}}
    state["prs"].append(p)
    save()
    print(url(p))
elif a[:2] == ["pr", "view"]:
    p = find(a[2])
    oid = git("--git-dir", bare, "rev-parse", "refs/heads/" + p["head"]).stdout.strip()
    print(json.dumps({{"headRefOid": oid, "headRefName": p["head"], "baseRefName": p["base"], "state": p["state"],
                      "title": p["title"], "isCrossRepository": False}}))
elif a[:2] == ["pr", "checks"]:  # CI: a one-step workflow, green
    print(json.dumps([{{"name": "Checks", "state": "SUCCESS", "bucket": "pass", "link": ""}}]))
elif a[:1] == ["api"] and "/compare/" in a[1]:
    base, sha = a[1].split("/compare/")[1].split("...")
    print(git("--git-dir", bare, "rev-list", "--count", sha + ".." + base).stdout.strip())
elif a[:3] == ["api", "-X", "PUT"]:
    p = find(a[3])
    f = dict(x.split("=", 1) for x in a[4:] if "=" in x)
    h = d + "/helper"
    if not os.path.isdir(h):
        git("clone", "-q", bare, h)
    git("fetch", "-q", "origin", cwd=h)
    git("checkout", "-q", "-B", p["base"], "origin/" + p["base"], cwd=h)
    git("merge", "--squash", "origin/" + p["head"], cwd=h)
    git("commit", "-q", "-m", f["commit_title"], cwd=h)
    git("push", "-q", "origin", p["base"], cwd=h)
    p["state"] = "MERGED"
    save()
elif a[:3] == ["api", "-X", "DELETE"]:
    sys.exit(git("--git-dir", bare, "update-ref", "-d", "refs/heads/" + a[3].split("/heads/")[1]).returncode)
elif a[:2] == ["api", "--paginate"]:  # PR files: none touch an owner path
    pass
elif a[:1] == ["api"] and "/code-scanning/" in a[1]:
    sys.stderr.write("gh: no analysis found (HTTP 404)\\n")
    sys.exit(1)
elif a[:1] == ["api"] and "/rules/" in a[1]:
    print("[]")
elif a[:1] == ["api"]:
    print("{{}}")
else:
    sys.exit(1)
"""


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-delivery-")).resolve()
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    env = dict(os.environ, **GITENV, PATH=f"{tmp / 'bin'}:{os.environ['PATH']}", STAND_D=str(tmp),
               STAND_BARE=str(tmp / "origin.git"))
    (tmp / "bin").mkdir()
    (tmp / "bin/gh").write_text(GH)
    (tmp / "bin/gh").chmod(0o755)
    (tmp / "state.json").write_text(json.dumps({"prs": []}))
    bare, main, wt = tmp / "origin.git", tmp / "main", tmp / "wt-toy"

    def g(cwd, *a):
        p = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        if p.returncode:
            raise RuntimeError(f"git {a}: {p.stderr}")
        return p.stdout.strip()

    def write(rel, text, base=main):
        p = Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def tool(script, *a):
        return subprocess.run([sys.executable, str(script), *map(str, a)], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=120, cwd=main)

    def gh_calls(*sub):
        log = tmp / "gh.log"
        return [c for c in map(json.loads, log.read_text().splitlines()) if c[:len(sub)] == list(sub)]

    results = []

    def check(name, good, ok_text, detail):
        results.append(good)
        print(f"ok {name}: {ok_text}" if good else f"FAILED {name}: {detail}")

    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=env)
    subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=env)
    write(".gitignore", "solo-sdd/\n")
    write("README.md", "r\n")
    g(main, "add", "-A")
    g(main, "commit", "-qm", "init")
    g(main, "remote", "add", "origin", str(bare))
    g(main, "push", "-q", "-u", "origin", "main")
    for b in ("staging", "release/1.9.0", "release/1.10.0", "release/1.2.0"):
        g(main, "push", "-q", "origin", "main:refs/heads/" + b)
    g(main, "checkout", "-q", "-b", "dev")  # the team integrates into dev: dev is one commit ahead
    write("dev.txt", "d\n")
    g(main, "add", "-A")
    g(main, "commit", "-qm", "on dev")
    g(main, "push", "-q", "-u", "origin", "dev")
    write("solo-sdd/config", "mode: team\ndelivery.base: dev\ndelivery.promote: staging, release/*, main\n")
    write("solo-sdd/changes/toy/tasks.md", "- [x] 1.1 toy\n")

    # 1. the dispatcher's worktree (cut from the default branch, as before) -> setup -> ship -> land
    g(main, "fetch", "-q", "origin")
    g(main, "worktree", "add", "-q", "-b", "change/toy", str(wt), "origin/main")
    st = tool(WT, "setup", main, wt)
    write("toy.txt", "t\n", wt)
    g(wt, "add", "-A")
    g(wt, "commit", "-qm", "toy change")
    parent, dev = g(wt, "rev-parse", "HEAD^"), g(main, "rev-parse", "origin/dev")
    check("setup", st.returncode == 0 and "start: origin/dev" in st.stdout and parent == dev,
          f"the first commit's parent is origin/dev ({dev[:7]})", f"code {st.returncode} {st.stdout!r} {st.stderr!r}")
    sh = tool(PR, "ship", main, wt, "main", "toy")
    create = gh_calls("pr", "create")
    target = create[0][create[0].index("--base") + 1] if create else None
    url = sh.stdout.split()[2] if sh.stdout.startswith("PR #") else ""
    check("ship", sh.returncode == 0 and "CI: green" in sh.stdout and target == "dev",
          f"{sh.stdout.strip()}, the PR targets {target}", f"code {sh.returncode} target {target} {sh.stdout!r} {sh.stderr!r}")
    ld = tool(PR, "land", main, wt, url, "squash")
    lines = ld.stdout.strip().splitlines()
    on_dev = g(main, "branch", "--show-current") == "dev" and g(main, "rev-parse", "HEAD") == g(main, "rev-parse", "origin/dev")
    merged = (main / "toy.txt").exists() and g(main, "rev-parse", "origin/main") != g(main, "rev-parse", "origin/dev")
    check("land", ld.returncode == 0 and on_dev and merged and not wt.exists(),
          "merged into dev, the main folder on dev at origin/dev, main untouched, the worktree removed",
          f"code {ld.returncode} on_dev {on_dev} merged {merged} {ld.stdout!r} {ld.stderr!r}")
    want = "promotion: dev → staging: sdd-pr.py promote dev staging"
    check("promotion line", lines[-1:] == [want], want, f"{lines[-2:]}")

    # 2. promote dev staging twice: one PR, the same URL, nothing merged
    p1, p2 = tool(PR, "promote", "dev", "staging"), tool(PR, "promote", "dev", "staging")
    same = p1.stdout == p2.stdout and "dev → staging: open, not merged" in p1.stdout
    check("promote dev staging", p1.returncode == p2.returncode == 0 and same and len(gh_calls("pr", "create")) == 2,
          p1.stdout.strip() + ", the second call prints the same URL", f"{p1.stdout!r} {p2.stdout!r} {p2.stderr!r}")

    # 3. promote staging release/*: the newest release branch by version
    p3 = tool(PR, "promote", "staging", "release/*")
    last = gh_calls("pr", "create")[-1]
    check("promote release/*", p3.returncode == 0 and last[last.index("--base") + 1] == "release/1.10.0",
          p3.stdout.strip(), f"{p3.stdout!r} {p3.stderr!r} {last}")

    # nothing merged a promotion PR: the only merge is the toy change into dev
    puts = gh_calls("api", "-X", "PUT")
    check("no promotion merge", len(puts) == 1, "one merge in the run (the toy change into dev)", f"{puts}")

    # broken settings: ship exits 1 naming the line, no PR opened
    write("solo-sdd/config", "delivery.base dev\n")
    before = len(gh_calls("pr", "create"))
    g(main, "worktree", "add", "-q", "-b", "change/two", str(tmp / "wt-two"), "origin/dev")
    sb = tool(PR, "ship", main, tmp / "wt-two", "main", "two")
    check("broken settings", sb.returncode == 1 and "solo-sdd/config:1" in sb.stderr
          and len(gh_calls("pr", "create")) == before, sb.stderr.strip(), f"code {sb.returncode} {sb.stderr!r}")

    print("stand: %d of %d steps passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
