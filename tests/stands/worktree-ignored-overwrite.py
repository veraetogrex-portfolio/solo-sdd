#!/usr/bin/env python3
"""Live scenario of fix-worktree-ignored-overwrite: the real global/sdd_dispatch.py land-local and global/sdd_pr.py
ship on real git, a bare repository instead of the remote, a fake gh (it logs and fails: no network).
WORKTREE of change/b holds an ignored solo-sdd/config with `mine`; then MAIN tracks solo-sdd/config with `add -f`.
  1. land-local under delivery.local-merge: rebase: code 1, the refusal line, `mine` kept, nothing moved;
  2. ship after MAIN's commit reached origin: code 1, the refusal line, `mine` kept, change/b not pushed;
  3. skills/spec-dispatch/merge.md as `sync.py push` lays it out under a temporary HOME names both lines
     "not merged" with no return to the orchestrator.

Usage: python3 tests/stands/worktree-ignored-overwrite.py (from the repository root)
Code 0: every check passed. The stand creates and removes its temporary folder itself."""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISPATCH, PR, WT = (ROOT / "global" / n for n in ("sdd_dispatch.py", "sdd_pr.py", "sdd_worktree.py"))
LAND_LINE = "not merged: rebase would overwrite ignored files in WORKTREE: solo-sdd/config"
SHIP_LINE = "not shipped: merge would overwrite ignored files in WORKTREE: solo-sdd/config"
MINE = "delivery.local-merge: rebase\n# mine\n"
GH = f"""#!{sys.executable}
import os, sys
open(os.environ["STAND_D"] + "/gh.log", "a").write(" ".join(sys.argv[1:]) + "\\n")
sys.exit(1)
"""
SOLO = f"""#!/bin/sh
PYTHONPATH="{ROOT}" exec "{sys.executable}" -m solo_sdd "$@"
"""
results = []


def check(name, good, ok_text, detail):
    results.append(good)
    print(f"ok {name}: {ok_text}" if good else f"FAILED {name}: {detail}")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-wt-ignored-")).resolve()
    try:
        run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"worktree-ignored-overwrite: {sum(results)} of {len(results)} checks passed")
    return 0 if results and all(results) else 1


def run(tmp):
    env = dict(os.environ, GIT_AUTHOR_NAME="stand", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="stand",
               GIT_COMMITTER_EMAIL="s@s", PATH=f"{tmp / 'bin'}:{os.environ['PATH']}", STAND_D=str(tmp),
               HOME=str(tmp / "home"), GIT_CONFIG_NOSYSTEM="1")
    for name, text in (("gh", GH), ("solo-sdd", SOLO)):
        (tmp / "bin").mkdir(exist_ok=True)
        (tmp / "bin" / name).write_text(text)
        (tmp / "bin" / name).chmod(0o755)
    (tmp / "home" / ".claude").mkdir(parents=True)

    def g(cwd, *a):
        p = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        if p.returncode:
            raise RuntimeError(f"git {a}: {p.stderr}")
        return p.stdout.strip()

    def rev(cwd, ref):  # the previous code's land-local removes change/b and WORKTREE after the merge
        p = subprocess.run(["git", "-C", str(cwd), "rev-parse", "-q", "--verify", ref], capture_output=True, text=True,
                           env=env, stdin=subprocess.DEVNULL) if Path(cwd).exists() else None
        return p.stdout.strip() if p and not p.returncode else "<missing>"

    def tool(*a, cwd):
        return subprocess.run([sys.executable, *map(str, a)], capture_output=True, text=True, env=env, cwd=cwd,
                              stdin=subprocess.DEVNULL, timeout=300)

    def read(path):
        return path.read_text() if path.exists() else "<missing>"

    def write(base, rel, text):
        p = Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def build(name):
        """MAIN with origin, WORKTREE of change/b with an ignored solo-sdd/config `mine`, then MAIN tracks the file."""
        bare, main, wt = tmp / name / "origin.git", tmp / name / "main", tmp / name / "wt-b"
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=env)
        subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=env)
        write(main, "README.md", "r\n")
        write(main, "solo-sdd/project.md", "# Project\n")  # a solo-sdd/ tree: land-local validates with solo-sdd
        g(main, "add", "-A")
        g(main, "commit", "-qm", "init")
        g(main, "remote", "add", "origin", str(bare))
        g(main, "push", "-q", "-u", "origin", "main")
        write(main, ".git/info/exclude", "solo-sdd/config\n")
        write(main, "solo-sdd/config", "delivery.local-merge: rebase\n")
        g(main, "worktree", "add", "-q", "-b", "change/b", str(wt))
        tool(WT, "setup", main, wt, cwd=main)
        write(wt, "solo-sdd/config", MINE)  # the worktree's own value of the ignored file
        write(wt, "b.txt", "b\n")
        g(wt, "add", "b.txt")
        g(wt, "commit", "-qm", "b change")
        g(main, "add", "-f", "solo-sdd/config")
        g(main, "commit", "-qm", "track config")
        return bare, main, wt

    # 1. land-local under rebase refuses before reset --keep
    _, main, wt = build("land")
    heads = lambda: (rev(main, "HEAD"), rev(main, "change/b"), rev(wt, "HEAD"))
    before = heads()
    ld = tool(DISPATCH, "land-local", main, wt, "b", cwd=main)
    text = read(wt / "solo-sdd/config")
    check("1 land-local", ld.returncode == 1 and LAND_LINE in ld.stdout.splitlines() and text == MINE
          and heads() == before, f"code 1, {LAND_LINE}, the file keeps mine, nothing moved",
          f"code {ld.returncode} {ld.stdout!r} {ld.stderr!r} WORKTREE file {text!r} MAIN file "
          f"{read(main / 'solo-sdd/config')!r} moved {heads() != before}")

    # 2. ship refuses before merging origin/main into WORKTREE
    bare, main, wt = build("ship")
    g(main, "push", "-q", "origin", "main")
    wt_head = rev(wt, "HEAD")
    sh = tool(PR, "ship", main, wt, "main", "b", cwd=main)
    text = read(wt / "solo-sdd/config")
    pushed = g(bare, "branch", "--list", "change/b")
    gh = read(tmp / "gh.log")
    check("2 ship", sh.returncode == 1 and SHIP_LINE in sh.stderr.splitlines() and text == MINE and not pushed
          and gh == "<missing>" and rev(wt, "HEAD") == wt_head,
          f"code 1, {SHIP_LINE}, the file keeps mine, change/b not pushed, no gh call",
          f"code {sh.returncode} {sh.stdout!r} {sh.stderr!r} file {text!r} pushed {pushed!r} gh {gh!r}")

    # 3. the dispatcher's merge step as sync.py push lays it out
    p = tool(ROOT / "sync.py", "push", cwd=ROOT)
    laid = sorted((tmp / "home").rglob("spec-dispatch/merge.md"))
    rows = [line for f in laid for line in f.read_text().splitlines()]
    names = [any(key in r and "with no return to the orchestrator" in r for r in rows)
             for key in ("`not merged: rebase would overwrite ignored files in WORKTREE: <paths>`",
                         "`not shipped: merge would overwrite ignored files in WORKTREE: <paths>`")]
    check("3 merge.md", p.returncode == 0 and laid and all(names),
          f"{len(laid)} laid-out copies name both lines with no return to the orchestrator",
          f"push code {p.returncode} {p.stdout[-400:]!r} {p.stderr[-400:]!r} copies {laid} found {names}")


if __name__ == "__main__":
    sys.exit(main())
