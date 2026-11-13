#!/usr/bin/env python3
"""Stand of change zsh-substitution-fix: process-guard.py and work_hooks.py guard on the Live Scenario commands, fed as
hook input JSON (nothing is run). guard runs with a temporary home and a temporary project with a solo-sdd/ tree; the
stand removes both. --base <hash> runs the hooks of that commit (git show) instead of the working tree."""
import argparse
import json
import os
import pathlib
import subprocess
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
ap = argparse.ArgumentParser()
ap.add_argument("--base", help="a commit whose hooks to run")
args = ap.parse_args()
checks = []


def event(cmd, cwd):
    return json.dumps({"session_id": "stand", "cwd": cwd, "tool_name": "Bash", "tool_input": {"command": cmd}})


with tempfile.TemporaryDirectory(prefix="zs-home-") as home:
    hooks = REPO / "global"
    if args.base:
        hooks = pathlib.Path(home, "hooks")
        hooks.mkdir()
        for name in ("process-guard.py", "work_hooks.py", "model-policy.json"):
            (hooks / name).write_bytes(subprocess.run(["git", "-C", str(REPO), "show", "%s:global/%s" % (args.base, name)],
                                                      check=True, capture_output=True, stdin=subprocess.DEVNULL).stdout)
    tree = os.path.join(home, "tree")
    os.makedirs(os.path.join(tree, "solo-sdd/specs"))
    subprocess.run(["git", "init", "-q", tree], check=True, capture_output=True, stdin=subprocess.DEVNULL)

    def pg(cmd):
        return subprocess.run([PY, str(hooks / "process-guard.py")], input=event(cmd, tree), capture_output=True,
                              text=True, timeout=10).returncode == 0

    def guard(cmd):
        r = subprocess.run([PY, str(hooks / "work_hooks.py"), "guard"], input=event(cmd, tree), capture_output=True,
                           text=True, timeout=10, env=dict(os.environ, HOME=home))
        return not (r.stdout.strip() and json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] == "deny")

    cases = [  # (step, hook, command, passes)
        (1, pg, "git commit -m =(kill 1)", False),
        (1, pg, 'T="${TMPDIR:-/tmp}"; git commit -m =(kill 1)', False),
        (1, pg, "grep =(kill 1) x", False),
        (1, guard, "git commit -m =(gh pr merge 5)", False),
        (2, pg, 'A=(x y); git commit -m "graceful shutdown"', False),
        (2, pg, 'T="${TMPDIR:-/tmp}"; git commit -m "graceful shutdown"', True),
        (2, pg, 'T="${TMPDIR:-/tmp}"; grep -n "kill" docs/x.md', True),
        (3, pg, "${X:-kill} 1", True),
    ]
    for step, hook, cmd, passes in cases:
        good = hook(cmd) == passes
        checks.append(good)
        print("%s step %d %s %s: %s" % ("PASS" if good else "FAIL", step, "process-guard" if hook is pg else "guard",
                                        "passes" if passes else "refuses", cmd))

print("zsh-substitution stand: %d/%d checks passed" % (sum(checks), len(checks)))
raise SystemExit(0 if all(checks) else 1)
