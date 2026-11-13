#!/usr/bin/env python3
"""Live Scenario of pr-human-paths: "owner only" paths without GitHub and without paid model calls.
Real global/sdd_dispatch.py, global/sdd_pr.py, global/sdd_worktree.py and real git; in pr mode
a bare repository instead of the remote. Only gh is faked (first in PATH): it keeps PRs in a file, returns the list
of PR files from `git diff main...<branch>` in bare, checks are green, squash-merge in a helper clone.
openspec is real: empty openspec/specs and openspec/changes pass `openspec validate`.

A. local mode: land-local, a change edits the protected src/core.py -> code 8; a neighbouring change -> code 0.
B. pr mode: land, a change edits .github/workflows/ci.yml -> code 8, no PUT merge; a neighbouring one -> 0.
C. sdd-pr.py merge from WORKTREE finds the main folder itself and reads its AGENTS.md; AGENTS.md outside git:
   the item removed in WORKTREE -> land code 8.

Usage: python3 tests/stands/owner-paths.py (from the repository root)
The last line is "total: N of N"; code 0 only if every scenario matched. The stand creates and removes its temporary folder itself."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PR, WT, DISP = ROOT / "global/sdd_pr.py", ROOT / "global/sdd_worktree.py", ROOT / "global/sdd_dispatch.py"
GITENV = dict(GIT_AUTHOR_NAME="stand", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="stand", GIT_COMMITTER_EMAIL="s@s")
RULE = "- Owner only: `src/core.py`, `docs/guard.md`\n"
AGENTS = "# stand\n\n## Delivery\n\n- Mode: %s\n" + RULE + "\n## Other\n\ntext\n"

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
elif a[:2] == ["api", "--paginate"] and a[2].endswith("/files"):
    p = find(a[2])
    rng = "main...refs/heads/" + p["head"]
    for line in git("--git-dir", bare, "diff", "--name-status", "-M", rng).stdout.splitlines():
        cols = line.split("\\t")
        name, prev = cols[-1], (cols[1] if cols[0].startswith("R") else None)
        diff = git("--git-dir", bare, "diff", rng, "--", name).stdout
        patch = "\\n".join(l for l in diff.splitlines() if l[:1] in "+-" and not l.startswith(("+++", "---")))
        print(json.dumps({{"filename": name, "previous_filename": prev, "patch": patch}}))
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
    tmp = Path(tempfile.mkdtemp(prefix="stand-ownerpaths-")).resolve()
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
    results = []

    def check(name, good, detail):
        results.append(good)
        print(f"ok: {name}" if good else f"FAIL: {name} — {detail}")

    def g(cwd, *a):
        p = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        if p.returncode:
            raise RuntimeError(f"git {a}: {p.stderr}")
        return p.stdout.strip()

    def write(base, rel, text):
        p = Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def tool(script, *a, cwd=None):
        return subprocess.run([sys.executable, str(script), *map(str, a)], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=120, cwd=cwd)

    def repo(name, mode, tracked_agents, remote=False):
        """MAIN repository: AGENTS.md under git or in .gitignore, an empty openspec/ outside git."""
        main = tmp / name
        subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=env)
        write(main, ".gitignore", "openspec/\n" + ("" if tracked_agents else "AGENTS.md\n"))
        write(main, "AGENTS.md", AGENTS % mode)
        write(main, "src/core.py", "core = 1\n")
        write(main, "docs/a.md", "a\n")
        write(main, "docs/guard.md", "g\n")
        write(main, ".github/workflows/ci.yml", "on: push\n")
        (main / "openspec/specs").mkdir(parents=True)
        (main / "openspec/changes").mkdir()
        g(main, "add", "-A")
        g(main, "commit", "-qm", "init")
        if remote:
            subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(tmp / "origin.git")], check=True, env=env)
            g(main, "remote", "add", "origin", str(tmp / "origin.git"))
            g(main, "push", "-q", "-u", "origin", "main")
        return main

    def change(main, name, rel, text, setup=False):
        wt = tmp / f"wt-{main.name}-{name}"
        g(main, "worktree", "add", "-q", "-b", f"change/{name}", str(wt), "main")
        if setup and tool(WT, "setup", main, wt).returncode:
            raise RuntimeError("setup " + name)
        write(wt, rel, text)
        g(wt, "add", "-A")
        g(wt, "commit", "-qm", f"feat {name}")
        return wt

    # A. local mode
    m = repo("local", "local", True)
    wc = change(m, "core", "src/core.py", "core = 2\n")
    wd = change(m, "docs", "docs/a.md", "a2\n")
    head = g(m, "rev-parse", "HEAD")
    p = tool(DISP, "land-local", m, wc, "core")
    check("local: a change with src/core.py waits for the owner (code 8, path named)",
          p.returncode == 8 and "waits for the owner: src/core.py" in p.stdout, f"code {p.returncode} {p.stdout!r} {p.stderr!r}")
    kept = g(m, "rev-parse", "HEAD") == head and bool(g(m, "branch", "--list", "change/core")) and wc.is_dir()
    check("local: main unchanged, branch and worktree in place", kept, "main, branch or folder changed")
    p = tool(DISP, "land-local", m, wd, "docs")
    check("local: the neighbouring change merged (code 0, docs/a.md changed)",
          p.returncode == 0 and (m / "docs/a.md").read_text() == "a2\n", f"code {p.returncode} {p.stdout!r} {p.stderr!r}")

    # B. pr mode
    m = repo("pr", "pr", False, remote=True)
    (tmp / "state.json").write_text(json.dumps({"prs": []}))

    def shipped(name, rel, text):
        wt = change(m, name, rel, text, setup=True)
        p = tool(PR, "ship", m, wt, "main", f"feat {name}")
        if p.returncode:
            raise RuntimeError(f"ship {name}: {p.stdout} {p.stderr}")
        return wt, p.stdout.split("PR #")[1].split()[1]

    def state(head):
        return next(x for x in json.loads((tmp / "state.json").read_text())["prs"] if x["head"] == head)

    wci, uci = shipped("ci-cache", ".github/workflows/ci.yml", "on: [push, pull_request]\n")
    p = tool(PR, "land", m, wci, uci, "squash")
    check("pr: a change with ci.yml waits for the owner (code 8, path named)",
          p.returncode == 8 and "waits for the owner: .github/workflows/ci.yml" in p.stdout, f"code {p.returncode} {p.stdout!r} {p.stderr!r}")
    s = state("change/ci-cache")
    check("pr: PUT merge not sent, PR open, worktree in place",
          s["puts"] == 0 and s["state"] == "OPEN" and wci.is_dir(), f"puts={s['puts']} state={s['state']} wt={wci.is_dir()}")
    wo, uo = shipped("other", "docs/a.md", "a2\n")
    p = tool(PR, "land", m, wo, uo, "squash")
    check("pr: the neighbouring change without protected paths merged (code 0, PR MERGED)",
          p.returncode == 0 and state("change/other")["state"] == "MERGED", f"code {p.returncode} {p.stdout!r} {p.stderr!r}")

    # C. the main folder from WORKTREE and AGENTS.md outside git
    wg, ug = shipped("guarded", "docs/guard.md", "g2\n")
    head = g(wg, "rev-parse", "HEAD")
    p = tool(PR, "merge", ug, "squash", head, cwd=wg)
    check("merge from WORKTREE finds the AGENTS.md of the main folder (code 8, docs/guard.md)",
          p.returncode == 8 and "waits for the owner: docs/guard.md" in p.stdout, f"code {p.returncode} {p.stdout!r} {p.stderr!r}")
    check("merge from WORKTREE: PUT not sent", state("change/guarded")["puts"] == 0, "PUT sent")
    wx, ux = shipped("sneaky", "docs/a.md", "a3\n")
    write(wx, "AGENTS.md", (wx / "AGENTS.md").read_text().replace(RULE, ""))
    p = tool(PR, "land", m, wx, ux, "squash")
    ignored = subprocess.run(["git", "-C", str(m), "check-ignore", "-q", "AGENTS.md"], env=env).returncode == 0
    check("AGENTS.md outside git, item removed in WORKTREE: land code 8 with AGENTS.md",
          ignored and p.returncode == 8 and "AGENTS.md («Owner only:»)" in p.stdout and state("change/sneaky")["puts"] == 0,
          f"ignored={ignored} code {p.returncode} {p.stdout!r} {p.stderr!r}")

    n = sum(results)
    print(f"total: {n} of {len(results)}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
