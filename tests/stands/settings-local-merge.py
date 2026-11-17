#!/usr/bin/env python3
"""Live Scenario of settings-local-merge: `sdd-dispatch.py land-local` merges by `delivery.local-merge`.

Real global/sdd_dispatch.py, global/sdd_worktree.py and git. Each check builds its own main repository with a
solo-sdd/ tree and a worktree on change/b (three commits, the last `b: done`) and runs
`python3 global/sdd_dispatch.py land-local <MAIN> <WORKTREE> b`; its `solo-sdd validate --all` is this tree's
command (a `solo-sdd` shim first in PATH runs `python3 -m solo_sdd` of this repository).

1. no delivery.local-merge -> code 0, the main head has two parents
2. squash -> code 0, one parent, subject `b: done`, change/b deleted
3. rebase, the main branch moved ahead -> code 0, no merge commit, the three commits on top
4. squash, a conflicting README.md -> code 6 naming README.md, `git status --short` in MAIN empty, change/b in place

Usage: python3 tests/stands/settings-local-merge.py (from any folder). The last line is `<n> of 4 checks passed`;
code 0 only when all passed. The stand creates and removes its temporary folder itself.
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISP, WT = ROOT / "global/sdd_dispatch.py", ROOT / "global/sdd_worktree.py"


def git(repo, *args):
    p = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, env=ENV, stdin=subprocess.DEVNULL)
    if p.returncode:
        raise RuntimeError("git %s: %s" % (" ".join(args), p.stderr.strip()))
    return p.stdout.strip()


def commit(repo, rel, text, msg):
    (Path(repo) / rel).parent.mkdir(parents=True, exist_ok=True)
    (Path(repo) / rel).write_text(text, encoding="utf-8")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)


def build(d, method, readme=False, ahead=False):
    main, wt = d / "main", d / "wt"
    main.mkdir()
    git(main, "init", "-q", "-b", "main")
    commit(main, "solo-sdd/project.md", "# stand\n", "tree")
    if method:
        commit(main, "solo-sdd/config", "delivery.local-merge: %s\n" % method, "config")
    commit(main, "README.md", "base\n", "init")
    git(main, "worktree", "add", "-q", "-b", "change/b", str(wt))
    subprocess.run([sys.executable, str(WT), "setup", str(main), str(wt)], capture_output=True, env=ENV,
                   stdin=subprocess.DEVNULL, check=True)
    commit(wt, "README.md" if readme else "a.txt", "change\n", "b: start")
    commit(wt, "b.txt", "b\n", "b: more")
    commit(wt, "c.txt", "c\n", "b: done")
    if readme:
        commit(main, "README.md", "other\n", "other")
    if ahead:
        commit(main, "ahead.txt", "ahead\n", "ahead")
    return main, wt


def land(main, wt):
    r = subprocess.run([sys.executable, str(DISP), "land-local", str(main), str(wt), "b"], capture_output=True,
                       text=True, env=ENV, stdin=subprocess.DEVNULL, timeout=300)
    return r.returncode, (r.stdout + r.stderr).strip()


def parents(main):
    return git(main, "rev-list", "--parents", "-n", "1", "HEAD").split()[1:]


def check_default(d):
    main, wt = build(d, None)
    code, out = land(main, wt)
    return code == 0 and len(parents(main)) == 2, "code %d, parents %d: %s" % (code, len(parents(main)), out)


def check_squash(d):
    main, wt = build(d, "squash")
    prev = git(main, "rev-parse", "HEAD")
    code, out = land(main, wt)
    subject, branch = git(main, "log", "-1", "--format=%s"), git(main, "branch", "--list", "change/b")
    ok = code == 0 and parents(main) == [prev] and subject == "b: done" and branch == ""
    return ok, "code %d, parents %d, subject %r, branch %r: %s" % (code, len(parents(main)), subject, branch, out)


def check_rebase(d):
    main, wt = build(d, "rebase", ahead=True)
    ahead = git(main, "rev-parse", "HEAD")
    code, out = land(main, wt)
    merges = git(main, "log", "--merges", "--format=%h")
    top = git(main, "log", "--format=%s", ahead + "..HEAD").splitlines()
    ok = code == 0 and merges == "" and top == ["b: done", "b: more", "b: start"]
    return ok, "code %d, merges %r, on top %s: %s" % (code, merges, top, out)


def check_conflict(d):
    main, wt = build(d, "squash", readme=True)
    head, tip = git(main, "rev-parse", "HEAD"), git(main, "rev-parse", "change/b")
    code, out = land(main, wt)
    status = git(main, "status", "--short")
    ok = (code == 6 and "README.md" in out and status == "" and git(main, "rev-parse", "HEAD") == head
          and git(main, "rev-parse", "change/b") == tip and wt.is_dir())
    return ok, "code %d, status %r: %s" % (code, status, out)


def main():
    global ENV
    tmp = Path(tempfile.mkdtemp(prefix="stand-local-merge-"))
    try:
        shim = tmp / "bin" / "solo-sdd"
        shim.parent.mkdir()
        shim.write_text("#!/bin/sh\nexec %s -m solo_sdd \"$@\"\n" % sys.executable)
        shim.chmod(0o755)
        ENV = dict(os.environ, PATH=str(shim.parent) + os.pathsep + os.environ.get("PATH", ""), PYTHONPATH=str(ROOT),
                   GIT_AUTHOR_NAME="stand", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="stand",
                   GIT_COMMITTER_EMAIL="s@s", GIT_CONFIG_NOSYSTEM="1", HOME=str(tmp))
        checks = (("default merge: a merge commit", check_default), ("squash: one commit `b: done`", check_squash),
                  ("rebase: linear on the moved main", check_rebase), ("squash conflict: code 6, clean", check_conflict))
        passed = 0
        for n, (name, fn) in enumerate(checks, 1):
            d = tmp / str(n)
            d.mkdir()
            try:
                ok, why = fn(d)
            except (RuntimeError, subprocess.SubprocessError) as e:
                ok, why = False, str(e)
            passed += ok
            print("%s %d. %s%s" % ("PASS" if ok else "FAIL", n, name, "" if ok else " -- " + why))
        print("%d of %d checks passed" % (passed, len(checks)))
        return 0 if passed == len(checks) else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
