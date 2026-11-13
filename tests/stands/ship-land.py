#!/usr/bin/env python3
"""Live scenario of pr-ship-land without a GitHub repository: the real global/sdd_pr.py and
global/sdd_worktree.py, real git, a bare repository instead of the remote. Only gh is faked (first in PATH):
it keeps PRs in a file and behaves like GitHub (list, create, view, checks, behind_by,
squash-merge in a helper clone, branch deletion).

Usage: python3 tests/stands/ship-land.py (from the repository root)
Code 0: every scenario matched. The stand creates and removes its temporary folder itself."""
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
if a[:2] == ["pr", "list"]:
    head = a[a.index("--head") + 1]
    print(json.dumps([{{"number": p["n"], "url": url(p)}} for p in state["prs"] if p["head"] == head and p["state"] == "OPEN"]))
elif a[:2] == ["pr", "create"]:
    p = {{"n": len(state["prs"]) + 1, "head": a[a.index("--head") + 1], "base": a[a.index("--base") + 1],
         "title": a[a.index("--title") + 1], "state": "OPEN", "puts": 0}}
    state["prs"].append(p)
    save()
    print(url(p))
elif a[:2] == ["pr", "view"]:
    p = find(a[2])
    oid = git("--git-dir", bare, "rev-parse", "refs/heads/" + p["head"]).stdout.strip()
    print(json.dumps({{"headRefOid": oid, "headRefName": p["head"], "baseRefName": p["base"], "state": p["state"],
                      "title": p["title"], "isCrossRepository": False}}))
elif a[:2] == ["pr", "checks"]:
    print(json.dumps([{{"name": "Checks", "state": "SUCCESS", "bucket": "pass", "link": ""}}]))
elif a[:1] == ["api"] and "/compare/" in a[1]:
    sha = a[1].split("...")[1]
    print(git("--git-dir", bare, "rev-list", "--count", sha + "..main").stdout.strip())
elif a[:3] == ["api", "-X", "PUT"]:
    p = find(a[3])
    f = dict(x.split("=", 1) for x in a[4:] if "=" in x)
    oid = git("--git-dir", bare, "rev-parse", "refs/heads/" + p["head"]).stdout.strip()
    p["puts"] += 1
    if f["sha"] != oid:
        save()
        sys.stderr.write("gh: Head branch was modified (HTTP 409)\\n")
        sys.exit(1)
    h = d + "/helper"
    if not os.path.isdir(h):
        git("clone", "-q", bare, h)
    git("fetch", "-q", "origin", cwd=h)
    git("checkout", "-q", "-B", "main", "origin/main", cwd=h)
    git("merge", "--squash", "origin/" + p["head"], cwd=h)
    git("commit", "-q", "-m", f["commit_title"], cwd=h)
    git("push", "-q", "origin", "main", cwd=h)
    p["state"] = "MERGED"
    save()
elif a[:3] == ["api", "-X", "DELETE"]:
    r = git("--git-dir", bare, "update-ref", "-d", "refs/heads/" + a[3].split("/heads/")[1])
    sys.exit(r.returncode)
elif a[:1] == ["api"] and "/code-scanning/" in a[1]:  # code scanning is not enabled in the stand
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
    tmp = Path(tempfile.mkdtemp(prefix="stand-shiplang-")).resolve()
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
    bare, main = tmp / "origin.git", tmp / "main"

    def g(cwd, *a, check=True):
        p = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        if check and p.returncode:
            raise RuntimeError(f"git {a}: {p.stderr}")
        return p.stdout.strip()

    def write(base, rel, text):
        p = Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def tool(script, *a):
        return subprocess.run([sys.executable, str(script), *map(str, a)], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=120)

    def gh_calls(sub):
        log = tmp / "gh.log"
        return [c for c in map(json.loads, log.read_text().splitlines()) if c[:2] == sub] if log.exists() else []

    def prs():
        return {p["head"]: p for p in json.loads((tmp / "state.json").read_text())["prs"]}

    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=env)
    subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=env)
    write(main, ".gitignore", "openspec/\n")
    write(main, "docs/cli.md", "one\ntwo\nthree\n")
    write(main, "README.md", "r\n")
    g(main, "add", "-A")
    g(main, "commit", "-qm", "init")
    g(main, "remote", "add", "origin", str(bare))
    g(main, "push", "-q", "-u", "origin", "main")
    write(main, "openspec/n.md", "a\nb\nc\n")

    def change(name, rel, text, msg):
        wt = tmp / f"wt-{name}"
        g(main, "fetch", "-q", "origin")
        g(main, "worktree", "add", "-q", "-b", f"change/{name}", str(wt), "origin/main")
        if tool(WT, "setup", main, wt).returncode:
            raise RuntimeError("setup " + name)
        write(wt, rel, text)
        g(wt, "add", "-A")
        g(wt, "commit", "-qm", msg)
        return wt

    def ship(name, title=None):
        p = tool(PR, "ship", main, tmp / f"wt-{name}", "main", title or f"feat {name}")
        m = p.stdout.split("PR #")[1].split() if "PR #" in p.stdout else ["?", ""]
        return p, m[1]

    def land(name, url):
        return tool(PR, "land", main, tmp / f"wt-{name}", url, "squash")

    results = []

    def check(name, good, ok_text, detail=""):
        results.append(good)
        print(f"ok {name}: {ok_text}" if good else f"FAILED {name}: {detail}")

    # 1. push failure
    change("a", "a.txt", "a\n", "feat a")
    change("b", "b.txt", "b\n", "feat b")
    g(main, "config", "remote.origin.pushurl", "/no/such/path")
    p, _ = ship("a")
    g(main, "config", "--unset-all", "remote.origin.pushurl")
    check("push failure", p.returncode == 1 and "push" in p.stderr and not gh_calls(["pr", "checks"]),
          "code 1, push named, pr checks not called", f"code {p.returncode}, stderr {p.stderr!r}")

    # 2. falling behind
    pa, ua = ship("a")
    pb, ub = ship("b")
    la = land("a", ua)
    lb = land("b", ub)
    open_b = prs()["change/b"]["state"] == "OPEN"
    pb2, ub2 = ship("b")
    merge_head = g(tmp / "wt-b", "log", "-1", "--format=%s").startswith("Merge")
    lb2 = land("b", ub2)
    title = g(main, "log", "-1", "--format=%s")
    good = (pa.returncode == pb.returncode == la.returncode == pb2.returncode == lb2.returncode == 0
            and "CI: green" in pa.stdout + pb.stdout + pb2.stdout and lb.returncode == 5 and open_b
            and merge_head and ub2 == ub and title.startswith("feat b (#"))
    check("falling behind", good, "ship a and b green; land a 0; land b 5, PR b open; ship b green with a merge commit; "
          "land b 0, the main title is b's own commit with (#N)",
          f"{[x.returncode for x in (pa, pb, la, lb, pb2, lb2)]} open_b={open_b} merge_head={merge_head} "
          f"title={title!r} {la.stderr!r} {lb2.stderr!r}")

    # 3. failure after merge
    wtc = change("c", "c.txt", "c\n", "feat c")
    write(wtc, "openspec/n.md", "a\nC\nc\n")
    pc, uc = ship("c")
    write(main, "openspec/n.md", "a\nMAIN\nc\n")
    l1 = land("c", uc)
    write(main, "openspec/n.md", "a\nb\nc\n")
    l2 = land("c", uc)
    check("failure after merge",
          pc.returncode == 0 and l1.returncode == 7 and "merged, not finished: transport" in l1.stderr
          and l2.returncode == 0 and prs()["change/c"]["puts"] == 1,
          "code 7 on transport, a repeated land 0, merge once", f"{l1.returncode}/{l2.returncode} {l1.stderr!r} {l2.stderr!r}")

    # 4. conflict on update
    wtd = change("d", "docs/cli.md", "one\nD\nthree\n", "feat d")
    write(main, "docs/cli.md", "one\nMAINX\nthree\n")
    g(main, "commit", "-qam", "main edit")
    g(main, "push", "-q", "origin", "main")
    pd, _ = ship("d")
    gone = g(bare, "branch", "--list", "change/d") == ""
    check("conflict on update", pd.returncode == 6 and "docs/cli.md" in pd.stderr and gone,
          "code 6, file named, no branch on bare", f"{pd.returncode} {pd.stderr!r} {gone}")

    # 5. cleanup summary
    tool(WT, "remove", main, wtd)
    g(main, "branch", "-D", "change/d")
    left = g(main, "branch", "--list", "change/*")
    wts = g(main, "worktree", "list").splitlines()
    same = g(main, "rev-parse", "main") == g(main, "rev-parse", "origin/main")
    check("cleanup summary", same and len(wts) == 1 and not left,
          "main equals origin/main, one worktree line, no change/* branches", f"{same} {wts} {left!r}")

    n = sum(results)
    print(f"total: {n} of 5")
    return 0 if n == len(results) == 5 else 1


if __name__ == "__main__":
    sys.exit(main())
