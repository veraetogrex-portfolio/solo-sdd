#!/usr/bin/env python3
"""Stand of change fix-eval-pipe-env: the real guard hook by its entry point (`work_hooks.py guard`, a PreToolUse JSON on
stdin, cwd the repository), first from a temporary worktree of the base commit b6844a4, then from this tree. The temporary
home and worktree are removed by the stand."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
BASE = "b6844a4"
REASON = "The command prints the whole environment or a secret"
DEEP = "eval eval eval eval echo env | sh"  # refused on the base by the past-depth rule
SEEN = ["eval echo env | sh", "eval echo printenv | bash", "eval 'echo env' | sh", "eval echo env | tee | sh",
        "eval 'echo env; true' | sh", "echo env | eval sh", "echo env | eval 'true; sh'", "echo env | eval 'cat | sh'",
        "printf env | eval eval sh", "echo env | eval 'eval true; sh'", "echo env | eval eval eval eval sh",
        "echo env | eval cat | sh", "echo env | eval tee | sh", "eval echo env | eval sh",
        "echo env | eval cat | eval cat | eval cat | eval cat | sh"]
REFUSED = SEEN + [DEEP]
PASS = ["eval echo hi | sh", "echo ls | eval sh", "echo ok | eval cat", "echo env | eval true", "eval \"echo 'env\" | sh"]
checks = []


def guard(tree, home, cmd):
    """The hook's answer: '' when the command passes, else the deny reason."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "SOLO_SDD"))}
    event = {"session_id": "stand", "cwd": str(REPO), "tool_name": "Bash", "tool_input": {"command": cmd}}
    r = subprocess.run([PY, os.path.join(tree, "global/work_hooks.py"), "guard"], input=json.dumps(event), capture_output=True,
                       text=True, env=dict(env, HOME=home), cwd=str(REPO), timeout=30)
    out = r.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


with tempfile.TemporaryDirectory(prefix="epe-") as tmp:
    home, base = os.path.join(tmp, "home"), os.path.join(tmp, "base")
    os.makedirs(home)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", base, BASE], check=True, capture_output=True)
    try:
        for c in SEEN:
            checks.append(("base %s passes: %s" % (BASE, c), guard(base, home, c) == ""))
        checks.append(("base %s refuses: %s" % (BASE, DEEP), guard(base, home, DEEP).startswith(REASON)))
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", base], capture_output=True)
    for c in REFUSED:
        checks.append(("branch refuses: " + c, guard(str(REPO), home, c).startswith(REASON)))
    for c in PASS:
        checks.append(("branch passes: " + c, guard(str(REPO), home, c) == ""))

for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("eval-pipe-env: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
