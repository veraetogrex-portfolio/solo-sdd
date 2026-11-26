#!/usr/bin/env python3
"""Stand of change fix-env-runs-env: the real guard hook by its entry point (`work_hooks.py guard`, a PreToolUse JSON on
stdin, cwd the repository), first from a temporary worktree of the base commit 58c1d41, then from this tree, and the known
bypasses sentence of docs/hooks.md. The temporary home and worktree are removed by the stand."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
BASE = "58c1d41"
REASON = "The command prints the whole environment or a secret"
SEEN = ["env env", "env -i env", "env -u X env", "env FOO=1 env", "env env -i", "/usr/bin/env env", "env /usr/bin/env",
        "sudo env env", "timeout 5 env env", 'env "env"', "env -- env", "env -uX env", "env --unset=X env", "printf x | env env",
        "env -S env"]
NON_PLAIN = 'echo "$(date)"; env env ls'  # refused on the base by dump_text, which stopped at the nested env
REFUSED = SEEN + ['echo "$(date)"; env env']
PASS = ["env env ls", "env -i env HOME=/x true", "env env printenv HOME", NON_PLAIN, "env -S 'A=1 env'"]
DOCS = ["`env -S 'A=1 env'`"]
checks = []


def guard(tree, home, cmd):
    """The hook's answer: '' when the command passes, else the deny reason."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "SOLO_SDD"))}
    event = {"session_id": "stand", "cwd": str(REPO), "tool_name": "Bash", "tool_input": {"command": cmd}}
    r = subprocess.run([PY, os.path.join(tree, "global/work_hooks.py"), "guard"], input=json.dumps(event), capture_output=True,
                       text=True, env=dict(env, HOME=home), cwd=str(REPO), timeout=30)
    out = r.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


with tempfile.TemporaryDirectory(prefix="ere-") as tmp:
    home, base = os.path.join(tmp, "home"), os.path.join(tmp, "base")
    os.makedirs(home)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", base, BASE], check=True, capture_output=True)
    try:
        for c in SEEN:
            checks.append(("base %s passes: %s" % (BASE, c), guard(base, home, c) == ""))
        checks.append(("base %s refuses: %s" % (BASE, NON_PLAIN), guard(base, home, NON_PLAIN).startswith(REASON)))
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", base], capture_output=True)
    for c in REFUSED:
        checks.append(("branch refuses: " + c, guard(str(REPO), home, c).startswith(REASON)))
    for c in PASS:
        checks.append(("branch passes: " + c, guard(str(REPO), home, c) == ""))
docs = " ".join((REPO / "docs/hooks.md").read_text().split())
for d in DOCS:
    checks.append(("docs/hooks.md names: " + d, d in docs))

for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("env-runs-env: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
