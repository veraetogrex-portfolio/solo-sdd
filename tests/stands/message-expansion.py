#!/usr/bin/env python3
"""Stand of change message-expansion-fix: the repository's process-guard.py and work_hooks.py guard on the scenario
commands, fed as hook input JSON (nothing is run). guard runs with a temporary home and a temporary project with a
solo-sdd/ tree; the stand removes both."""
import json
import os
import pathlib
import subprocess
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
checks = []


def event(cmd, cwd):
    return json.dumps({"session_id": "stand", "cwd": cwd, "tool_name": "Bash", "tool_input": {"command": cmd}})


with tempfile.TemporaryDirectory(prefix="mx-home-") as home:
    tree = os.path.join(home, "tree")
    os.makedirs(os.path.join(tree, "solo-sdd/specs"))
    subprocess.run(["git", "init", "-q", tree], check=True, capture_output=True, stdin=subprocess.DEVNULL)

    def pg(cmd):
        return subprocess.run([PY, str(REPO / "global/process-guard.py")], input=event(cmd, tree), capture_output=True,
                              text=True, timeout=10).returncode == 0

    def guard(cmd):
        r = subprocess.run([PY, str(REPO / "global/work_hooks.py"), "guard"], input=event(cmd, tree), capture_output=True,
                           text=True, timeout=10, env=dict(os.environ, HOME=home))
        return not (r.stdout.strip() and json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny")

    cases = [  # (hook, command, passes)
        (pg, 'T="${TMPDIR:-/tmp}"; git commit -m "graceful shutdown"', True),
        (pg, 'echo ${HOME}; git commit -m "graceful shutdown"', True),
        (guard, 'T="${TMPDIR:-/tmp}"; git commit -m "a; gh pr merge 5"', True),
        (guard, 'T="${TMPDIR:-/tmp}"; grep -n "process.env" apps/desktop/src/main', False),
        (pg, 'X=${ kill 1; }; git commit -m "done"', False),
        (pg, 'echo ${X:-"a b"}; git commit -m "graceful shutdown"', False),
        (pg, 'echo ${X:-\\}}; git commit -m "graceful shutdown"', False),
        (pg, 'T=${X; git commit -m "graceful shutdown"', False),
        (guard, 'T=${X:-"a b"}; git commit -m "a; gh pr merge 5"', False),
        (pg, 'T="${TMPDIR:-/tmp}"; grep -n "kill" docs/x.md', True),
    ]
    for hook, cmd, passes in cases:
        good = hook(cmd) == passes
        checks.append(good)
        print("%s %s %s: %s" % ("PASS" if good else "FAIL", "process-guard" if hook is pg else "guard",
                                "passes" if passes else "refuses", cmd))

print("message-expansion stand: %d/%d checks passed" % (sum(checks), len(checks)))
raise SystemExit(0 if all(checks) else 1)
