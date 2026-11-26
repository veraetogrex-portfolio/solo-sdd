#!/usr/bin/env python3
"""Stand of change fix-pipe-walk-env: the real guard hook by its entry point (`work_hooks.py guard`, a PreToolUse JSON on
stdin, cwd the repository), first from a temporary worktree of the base commit 5549bc4, then from this tree. The temporary
home and worktree are removed by the stand."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
BASE = "5549bc4"
REASON = "The command prints the whole environment or a secret"
REFUSED = ["echo env |& sh", "echo env |& bash -s", "echo env |\nsh", "eval -- env", "echo env | eval -- sh", "echo env | (sh)",
           "echo env | ( sh )", "echo env | ( (sh))", "echo env | (eval sh)"]
PASS = ["echo ls |& sh", "echo ls |\nsh", "eval -- ls", "echo ls | eval -- sh", "echo ls | (sh)"]
checks = []


def guard(tree, home, cmd):
    """The hook's answer: '' when the command passes, else the deny reason."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "SOLO_SDD"))}
    event = {"session_id": "stand", "cwd": str(REPO), "tool_name": "Bash", "tool_input": {"command": cmd}}
    r = subprocess.run([PY, os.path.join(tree, "global/work_hooks.py"), "guard"], input=json.dumps(event), capture_output=True,
                       text=True, env=dict(env, HOME=home), cwd=str(REPO), timeout=30)
    out = r.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


with tempfile.TemporaryDirectory(prefix="pwe-") as tmp:
    home, base = os.path.join(tmp, "home"), os.path.join(tmp, "base")
    os.makedirs(home)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", base, BASE], check=True, capture_output=True)
    try:
        for c in REFUSED:
            checks.append(("base %s passes: %r" % (BASE, c), guard(base, home, c) == ""))
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", base], capture_output=True)
    for c in REFUSED:
        checks.append(("branch refuses: %r" % c, guard(str(REPO), home, c).startswith(REASON)))
    for c in PASS:
        checks.append(("branch passes: %r" % c, guard(str(REPO), home, c) == ""))

for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("pipe-walk-env: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
