#!/usr/bin/env python3
"""Stand of change command-guard-fixes: the real process-guard.py on the scenario commands, then solo-sdd install
--hooks / doctor / uninstall on temporary homes, and the deployed hook run by the command settings.json names before
a real git commit. Temporary folders are removed by the stand."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
HOME = os.path.expanduser("~")
checks = []


def check(name, good):
    checks.append((name, good))


def event(cmd, cwd=HOME):
    return json.dumps({"session_id": "stand", "cwd": cwd, "tool_name": "Bash", "tool_input": {"command": cmd}})


def pg(cmd):
    r = subprocess.run([PY, str(REPO / "global/process-guard.py")], input=event(cmd), capture_output=True, text=True, timeout=10)
    return r.returncode


# 1. Messages and paths are not commands
for cmd in ('git commit -m "fix: graceful shutdown of the worker"', 'gh pr create --title "Add kill switch"', "cat docs/kill.md"):
    check("process-guard passes: " + cmd, pg(cmd) == 0)
for cmd in ('bash -c "kill 1"', 'git commit -m "$(pkill node)"', "/bin/kill 1", "/usr/bin/pkill node"):
    check("process-guard refuses: " + cmd, pg(cmd) == 2)

def cli(home, *args):
    env = dict(os.environ, HOME=home, PYTHONPATH=str(REPO))
    r = subprocess.run([PY, "-m", "solo_sdd", *args], cwd=home, env=env, capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    return r.returncode, r.stdout


def settings(home):
    p = os.path.join(home, ".claude/settings.json")
    return json.load(open(p)) if os.path.exists(p) else None


def pg_entries(s):
    return [g for g in ((s or {}).get("hooks") or {}).get("PreToolUse", []) if "process-guard.py" in json.dumps(g)]


DENY = ["Bash(%s *)" % n for n in ("pkill", "killall", "kill", "osascript", "launchctl", "shutdown")]

with tempfile.TemporaryDirectory(prefix="cg-home-") as home:
    # 2. A fresh home
    code, _ = cli(home, "install", "--agents", "claude", "--hooks")
    s = settings(home)
    check("fresh home: install --hooks exit 0, one process-guard entry, six deny rules",
          code == 0 and len(pg_entries(s)) == 1 and s["permissions"]["deny"] == DENY)
    check("fresh home: doctor prints ok process guard: connected", "ok process guard: connected" in cli(home, "doctor")[1].splitlines())
    # 4. The deployed hook, run by the command settings.json names, lets a commit with such a message through
    repo = os.path.join(home, "repo")
    subprocess.run(["git", "init", "-q", repo], check=True, stdin=subprocess.DEVNULL)
    commit = 'git commit --allow-empty -m "probe: graceful shutdown"'
    hook = pg_entries(s)[0]["hooks"][0]["command"]
    r = subprocess.run(["/bin/sh", "-c", hook], input=event(commit, repo), capture_output=True, text=True,
                       env=dict(os.environ, HOME=home), timeout=10)
    done = r.returncode == 0 and subprocess.run(
        ["/bin/sh", "-c", commit], cwd=repo, capture_output=True, stdin=subprocess.DEVNULL,
        env=dict(os.environ, HOME=home, GIT_AUTHOR_NAME="s", GIT_AUTHOR_EMAIL="s@x", GIT_COMMITTER_NAME="s",
                 GIT_COMMITTER_EMAIL="s@x")).returncode == 0
    check("deployed hook passes the commit and the commit is made", done and os.path.isfile(os.path.join(home, ".claude/hooks/process-guard.py")))
    r = subprocess.run(["/bin/sh", "-c", hook], input=event("pkill node", repo), capture_output=True, text=True,
                       env=dict(os.environ, HOME=home), timeout=10)
    check("deployed hook refuses pkill node", r.returncode == 2)
    code, _ = cli(home, "uninstall")
    s = settings(home)
    check("fresh home: uninstall leaves no entry and no deny rule",
          code == 0 and not pg_entries(s) and not ((s or {}).get("permissions") or {}).get("deny"))

with tempfile.TemporaryDirectory(prefix="cg-hand-") as home:
    # 3. Connected by hand
    mine = {"matcher": "Bash|Monitor", "hooks": [{"type": "command", "command": 'exec /usr/bin/python3 "$HOME/.claude/hooks/process-guard.py"'}]}
    os.makedirs(os.path.join(home, ".claude"))
    json.dump({"hooks": {"PreToolUse": [mine]}}, open(os.path.join(home, ".claude/settings.json"), "w"))
    code, _ = cli(home, "install", "--agents", "claude", "--hooks")
    check("by hand: after install one entry, the hand one", code == 0 and pg_entries(settings(home)) == [mine])
    code, _ = cli(home, "uninstall")
    check("by hand: after uninstall the entry stays", code == 0 and pg_entries(settings(home)) == [mine])

for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("command-guards: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
