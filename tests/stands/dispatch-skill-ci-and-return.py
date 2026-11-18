#!/usr/bin/env python3
"""Live scenario of dispatch-skill-ci-and-return: the repository laid out by `sync.py push` under a temporary HOME.
  1. the laid-out ~/.claude/skills/ship/SKILL.md and ~/.claude/skills/spec-dispatch/merge.md (with the step files)
     give `checks not read` its own step: fix gh, no rerun and no empty commit, the outcome of a repeated one;
  2. the check and merge commands copied from the laid-out Return on conflict text, run with the laid-out
     ~/.local/bin/sdd-pr.py on real git: WORKTREE holds an ignored solo-sdd/config `mine` and a commit of its own
     branch, main tracks solo-sdd/config (`add -f`): the check refuses with code 1, no merge, `mine` kept; with
     nothing in the way it prints nothing, code 0, and the merge goes; the previous plain merge and
     `git merge --no-overwrite-ignore` both replace `mine` with main's text.

Usage: python3 tests/stands/dispatch-skill-ci-and-return.py (from the repository root)
Code 0: every check passed. The stand creates and removes its temporary folder itself."""
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINE = "merge would overwrite ignored files in WORKTREE: solo-sdd/config"
results = []


def check(name, good, ok_text, detail):
    results.append(good)
    print(f"ok {name}: {ok_text}" if good else f"FAILED {name}: {detail}")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-ci-return-")).resolve()
    try:
        run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"dispatch-skill-ci-and-return: {sum(results)} of {len(results)} checks passed")
    return 0 if len(results) == 2 and all(results) else 1


def step_rows(text):
    """The lines of a laid-out text that name `checks not read` with the step's three parts."""
    rows = [" ".join(r.split()) for r in text.splitlines() if "checks not read" in r]
    return [r for r in rows if "fix what gh reports" in r and re.search(r"no CI rerun|neither the rerun", r)
            and re.search(r"no empty commit|nor the empty commit|neither the rerun nor the empty commit", r)
            and re.search(r"(second|repeated) .checks not read.", r)]


def run(tmp):
    home = tmp / "home"
    (home / ".claude").mkdir(parents=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="stand", GIT_AUTHOR_EMAIL="s@s", GIT_COMMITTER_NAME="stand",
               GIT_COMMITTER_EMAIL="s@s", HOME=str(home), GIT_CONFIG_NOSYSTEM="1")

    def proc(*a, cwd=ROOT):
        return subprocess.run([str(x) for x in a], capture_output=True, text=True, env=env, cwd=cwd,
                              stdin=subprocess.DEVNULL, timeout=300)

    def g(cwd, *a):
        p = proc("git", "-C", cwd, *a)
        if p.returncode:
            raise RuntimeError(f"git {a}: {p.stderr}")
        return p.stdout.strip()

    def write(base, rel, text):
        p = Path(base) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    # 1. the laid-out skill texts
    push = proc(sys.executable, ROOT / "sync.py", "push")
    ship = home / ".claude/skills/ship/SKILL.md"
    disp = sorted((home / ".claude/skills/spec-dispatch").glob("*.md"))
    ship_rows = step_rows(ship.read_text()) if ship.exists() else []
    disp_text = "\n".join(f.read_text() for f in disp)
    disp_rows = [r for r in step_rows(disp_text) if '"not merged: PR" with the gh error' in r]
    ship_rows = [r for r in ship_rows if "stops as not done with the gh error" in r]
    check("1 checks not read", push.returncode == 0 and bool(ship_rows) and bool(disp_rows),
          "the laid-out ship and spec-dispatch texts name the step: fix gh, no rerun, no empty commit, the repeat",
          f"push code {push.returncode} {push.stderr[-300:]!r} ship rows {ship_rows} spec-dispatch rows {disp_rows}")

    # 2. the Return on conflict commands, as laid out
    para = next((p for p in disp_text.split("\n\n") if "**Return on conflict**" in p), "")
    spans = re.findall(r"`([^`]+)`", para)
    check_cmd = next((s for s in spans if " overwrites <WORKTREE> " in s), "")
    merge_cmd = next((s for s in spans if s.startswith("git -C <WORKTREE> merge ")), "")
    fetch_cmd = next((s for s in spans if s.startswith("git -C <WORKTREE> fetch")), "")
    order = bool(check_cmd and merge_cmd) and para.index(check_cmd) < para.index(merge_cmd)
    flat = " ".join(para.split())
    clauses = [c for c in ("any code but 0 means no merge, hand back `STATUS: not_ready` with the printed line in `NOTES`",
                           "`git -C <WORKTREE> fetch -q` first and `origin/<main>` in both commands") if c not in flat]

    def build(name, track):
        """main with an ignored solo-sdd/config and a bare origin; WORKTREE of change/x with `mine` there and a commit
        of its own; then main commits solo-sdd/config with `add -f` (track) or another file and pushes it."""
        main, wt, bare = tmp / name / "main", tmp / name / "wt", tmp / name / "origin.git"
        proc("git", "init", "-q", "--bare", "-b", "main", bare)
        proc("git", "init", "-q", "-b", "main", main)
        write(main, "README.md", "r\n")
        g(main, "add", "-A")
        g(main, "commit", "-qm", "init")
        write(main, ".git/info/exclude", "solo-sdd/config\n")
        g(main, "worktree", "add", "-q", "-b", "change/x", wt)
        write(wt, "solo-sdd/config", "mine\n")
        write(wt, "x.txt", "x\n")
        g(wt, "add", "x.txt")
        g(wt, "commit", "-qm", "own commit")
        write(main, "solo-sdd/config" if track else "other.txt", "main\n")
        g(main, "add", "-f", "solo-sdd/config" if track else "other.txt")
        g(main, "commit", "-qm", "main moves")
        g(main, "remote", "add", "origin", bare)
        g(main, "push", "-q", "origin", "main")
        return wt

    def cmd(text, wt, *extra, ref="main"):
        words = [str(home) + w[1:] if w.startswith("~/") else w
                 for w in shlex.split(text.replace("<WORKTREE>", str(wt)).replace("<main branch>", ref))]
        return proc(*words[:4], *extra, *words[4:])  # git -C <wt> merge [extra] main

    refusals = []
    for mode in ("local", "pr"):  # pr: the laid-out fetch first, then origin/main in the check
        wt = build("refuse-" + mode, True)
        head = g(wt, "rev-parse", "HEAD")
        fetched = mode == "local" or bool(fetch_cmd) and cmd(fetch_cmd, wt).returncode == 0
        ck = cmd(check_cmd, wt, ref="main" if mode == "local" else "origin/main") if check_cmd else None
        refusals.append((mode, fetched, ck and (ck.returncode, ck.stdout, ck.stderr),
                         (wt / "solo-sdd/config").read_text(), g(wt, "rev-parse", "HEAD") == head))
    refused = all(r[1:] == (True, (1, "", LINE + "\n"), "mine\n", True) for r in refusals)
    wt = build("clear", False)
    ok = cmd(check_cmd, wt) if check_cmd else None
    clear = ok is not None and ok.returncode == 0 and ok.stdout == ok.stderr == ""
    merged = clear and cmd(merge_cmd, wt).returncode == 0 and (wt / "other.txt").exists()
    old = []
    for extra in ((), ("--no-overwrite-ignore",)):
        wt = build("old" + "".join(extra), True)
        m = cmd(merge_cmd, wt, *extra) if merge_cmd else None
        old.append(m is not None and m.returncode == 0 and (wt / "solo-sdd/config").read_text() == "main\n")
    check("2 Return on conflict", order and not clauses and refused and merged and all(old),
          f"the check before the merge, not_ready with the line in NOTES: {LINE} with code 1 in local and pr mode, "
          "no merge, mine kept; clear: code 0 and the merge goes; the plain merge and --no-overwrite-ignore replace mine",
          f"spans {check_cmd!r} {merge_cmd!r} {fetch_cmd!r} order {order} missing {clauses} refusals {refusals} "
          f"clear {ok and (ok.returncode, ok.stdout, ok.stderr)!r} merged {merged} old {old}")


if __name__ == "__main__":
    sys.exit(main())
