#!/usr/bin/env python3
"""Stand of change fix-env-dump-valued-options: the real guard hook by its entry point (`work_hooks.py guard`, a PreToolUse
JSON on stdin, cwd the repository), first from a temporary worktree of the base commit 46d45ad, then from this tree, and
the known bypasses sentence of docs/hooks.md. The temporary home and worktree are removed by the stand."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
BASE = "46d45ad"
REASON = "The command prints the whole environment or a secret"
SEEN = ["env -u X printenv", "env -C /tmp printenv", "sudo -u root printenv", "sudo -u root printenv GITHUB_TOKEN",
        "env -u X sh -c env", "caffeinate -t 5 printenv"]
REFUSED = SEEN + ["env -P /usr/bin printenv", "/usr/bin/env -u X printenv", "timeout 5 env -u X printenv", "sudo -u root env",
                  "sudo -u root sh -c printenv", "caffeinate -w 1 printenv", "exec -a NAME printenv", "npx -p x printenv",
                  "npx --package x printenv", "time -o /tmp/x printenv", "/usr/bin/time -f %e printenv",
                  "eval eval eval eval env", "eval eval eval eval printenv"]
PASS = ["env -u HOME python3 -V", "env -C /tmp ls", "env -u X sh -c ls", "sudo -u root ls", "caffeinate -t 5 ls",
        "npx -p x eslint .", "time -o /tmp/x ls", "env -u X printenv HOME", "eval eval eval eval ls",
        "eval eval eval env X=1 python3 -V", "awk 'BEGIN{system(\"env\")}' /dev/null", "python3 -c 'import os; print(os.environ)'",
        "xargs printenv", "sed 's/.*/env/e' f", "env -S env"]
DOCS = ["an interpreter's script that runs or reads the environment", "a dump word another program runs from its arguments"]
checks = []


def guard(tree, home, cmd):
    """The hook's answer: '' when the command passes, else the deny reason."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "SOLO_SDD"))}
    event = {"session_id": "stand", "cwd": str(REPO), "tool_name": "Bash", "tool_input": {"command": cmd}}
    r = subprocess.run([PY, os.path.join(tree, "global/work_hooks.py"), "guard"], input=json.dumps(event), capture_output=True,
                       text=True, env=dict(env, HOME=home), cwd=str(REPO), timeout=30)
    out = r.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


with tempfile.TemporaryDirectory(prefix="edv-") as tmp:
    home, base = os.path.join(tmp, "home"), os.path.join(tmp, "base")
    os.makedirs(home)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", base, BASE], check=True, capture_output=True)
    try:
        for c in SEEN:
            checks.append(("base %s passes: %s" % (BASE, c), guard(base, home, c) == ""))
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
print("env-dump-valued-options: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
