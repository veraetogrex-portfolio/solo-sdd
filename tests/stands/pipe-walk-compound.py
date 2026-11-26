#!/usr/bin/env python3
"""Stand of change fix-pipe-walk-compound: the real guard hook by its entry point (`work_hooks.py guard`, a PreToolUse JSON
on stdin), first from a temporary worktree of the base commit 17c3c00, then from this tree. The dump and merge forms run
with cwd the repository (it has a solo-sdd/ tree), the archive form in a temporary repository whose change add-words holds
a foreign CLAIM. The temporary home, repository and worktree are removed by the stand."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
BASE = "17c3c00"
REASON = "The command prints the whole environment or a secret"
DUMPS = ["echo env | (true; sh)", "echo env | (cd /tmp && sh)", "echo env | if true; then sh; fi",
         "echo env | case x in x) sh;; esac", "echo env | sh -c sh", "echo env | sh>out", "echo env | (sh)>out",
         "echo env | (sh)2>/dev/null", "echo env | (cat) | sh", "echo env | (eval cat) | sh", "case x in x) env;; esac"]
MERGE, ARCHIVE = "eval -- gh pr merge 1", "eval -- solo-sdd archive add-words"
PASS = ["echo ls | (true; sh)", "echo ls | sh -c sh", "echo ls | sh>out", "echo ls | (cat) | sh", "case x in x) ls;; esac",
        "echo ls | (true; sh ')')", "echo env | (cat) > out"]
checks = []


def guard(tree, home, cmd, cwd):
    """The hook's answer: '' when the command passes, else the deny reason."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "SOLO_SDD"))}
    event = {"session_id": "stand", "cwd": cwd, "tool_name": "Bash", "tool_input": {"command": cmd}}
    r = subprocess.run([PY, os.path.join(tree, "global/work_hooks.py"), "guard"], input=json.dumps(event), capture_output=True,
                       text=True, env=dict(env, HOME=home), cwd=cwd, timeout=30)
    out = r.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


def forms(claimed):
    """(command, cwd, the start or a part of the reason the branch gives)."""
    return [(c, str(REPO), REASON) for c in DUMPS] + [(MERGE, str(REPO), "sdd-pr.py merge"),
                                                      (ARCHIVE, claimed, "taken by another agent")]


with tempfile.TemporaryDirectory(prefix="pwc-") as tmp:
    tmp = os.path.realpath(tmp)
    home, base, claimed = os.path.join(tmp, "home"), os.path.join(tmp, "base"), os.path.join(tmp, "claimed")
    os.makedirs(home)
    os.makedirs(os.path.join(claimed, "solo-sdd/changes/add-words"))
    pathlib.Path(claimed, "solo-sdd/changes/add-words/CLAIM").write_text("claude 2026-11-26 session=OTHER\n")
    subprocess.run(["git", "init", "-q"], cwd=claimed, check=True, capture_output=True)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", base, BASE], check=True, capture_output=True)
    try:
        for c, cwd, _ in forms(claimed):
            checks.append(("base %s passes: %r" % (BASE, c), guard(base, home, c, cwd) == ""))
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", base], capture_output=True)
    for c, cwd, why in forms(claimed):
        r = guard(str(REPO), home, c, cwd)
        checks.append(("branch refuses: %r" % c, r.startswith(why) if why == REASON else why in r))
    for c in PASS:
        checks.append(("branch passes: %r" % c, guard(str(REPO), home, c, str(REPO)) == ""))

for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("pipe-walk-compound: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
