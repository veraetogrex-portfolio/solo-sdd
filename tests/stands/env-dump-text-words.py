#!/usr/bin/env python3
"""Stand of change fix-env-dump-text-words: the real guard hook by its entry point (`work_hooks.py guard`, a PreToolUse
JSON on stdin, cwd the repository), first from a temporary worktree of the base commit 286817e, then from this tree.
The temporary home and worktree are removed by the stand."""
import json
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
BASE = "286817e"
REASON = "The command prints the whole environment or a secret"
SEEN = [r'grep -n "secret\|printenv\|env |echo \$" skills/debug-profile/SKILL.md', r'grep -n "foo\|env\[" global/sdd_eval.py',
        '[ -n "$(git status --short)" ] && echo yes; (cd /tmp && env -i HOME=$HOME PATH=/usr/bin:/bin python3 report.py '
        '< /dev/null | tail -4)', 'echo "$(date)"; env X=1 python3 -V']
PASS = SEEN + ['echo "$(date)"; env -u HOME python3 -V']
REFUSED = ["export -p", "env", "env | grep TOKEN", "printenv", 'grep x "$(env)"', 'echo "$(date)"; env -i HOME=$HOME printenv',
           'echo "$(date)"; env -u X printenv', 'echo "$(date)"; env X=1 xargs printenv', 'echo "$(date)"; env -C /tmp printenv',
           'echo "$(date)"; env X=1 e""nv', 'echo "$(date)"; env p""rintenv', 'echo "$(date)"; env -u HOME /usr/bin/env',
           'echo "$(date)"; env -u HOME "env"', 'echo "$(date)"; env -S "X=1 printenv"', 'echo "$(date)"; env -u printenv',
           'echo "$(date)"; grep -o "printenv" f | sh', 'echo "$(date)"; grep x f | xargs "printenv"',
           'echo "$(date)"; grep "${HOME}env" f', 'echo "$(date)"; env Y="$(env -u X printenv)" sh -c \'echo $Y\'',
           'echo "$(date)"; rg --pre "printenv" x f', 'echo "$(date)"; rg "--pre=printenv" x f',
           'echo "$(date)"; rg --hostname-bin "printenv" x f', 'echo "$(date)"; sed \'s/.*/env/e\' f',
           'echo "$(date)"; awk \'BEGIN{"env" | getline x; print x}\' /dev/null'] + ['echo "$(date)"; env A-B=1', 'echo "$(date)"; env -i \'A B=1\'', 'echo "$(date)"; { grep -o "printenv" f; } | sh', 'echo "$(date)"; (grep -o "printenv" f) | sh', 'echo "$(date)"; grep -o "printenv" f | tee >(sh)', 'echo "$(date)"; grep -o "printenv" f | python3 -', 'echo "$(date)"; sudo -u grep "env"', 'echo "$(date)"; env X=1 /usr/bin/e[n]v'] + ['echo "$(date)"; env A.B=1 >/dev/null', 'echo "$(date)"; env A-B=1 2>&1 | head', 'echo "$(date)"; env A.B=1 > /tmp/x', 'echo "$(date)"; env -i \'A B=1\' 2>&1', 'echo "$(date)"; grep -o "printenv" f | sudo -u cat sh', 'echo "$(date)"; grep -o "printenv" f | env -u tee sh', 'echo "$(date)"; grep -o "printenv" f | exec -a cat sh', 'echo "$(date)"; grep -o "printenv" f | >cat sh', 'echo "$(date)"; exec -a grep "env"', 'echo "$(date)"; time -o grep "env"', 'echo "$(date)"; caffeinate -t grep "env"'] + ['echo "$(date)"; env A.B=1 >& 2', 'echo "$(date)"; env A.B=1 2>& 1', 'echo "$(date)"; env A.B=1 >& /tmp/x', 'echo "$(date)"; env A.B=1 <& 0', 'echo "$(date)"; env A.B=1 {fd}>/tmp/x', 'echo "$(date)"; env A.B=1 {fd}>&1'] + ['echo "$(date)"; env >! /dev/stdout', 'echo "$(date)"; env A.B=1 >! /tmp/x', 'echo "$(date)"; env A.B=1 >>! /dev/stdout', 'echo "$(date)"; env A.B=1 >&! /tmp/x', 'echo "$(date)"; env A.B=1 &>! /tmp/x', 'echo "$(date)"; >! grep "printenv"'] + ['echo "$(date)"; >| grep "printenv"', 'echo "$(date)"; A=1 &>| grep "printenv"', 'echo "$(date)"; 2>| rg "printenv"', 'echo "$(date)"; >&| grep "printenv"']
checks = []


def guard(tree, home, cmd):
    """The hook's answer: '' when the command passes, else the deny reason."""
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CLAUDE", "SOLO_SDD"))}
    event = {"session_id": "stand", "cwd": str(REPO), "tool_name": "Bash", "tool_input": {"command": cmd}}
    r = subprocess.run([PY, os.path.join(tree, "global/work_hooks.py"), "guard"], input=json.dumps(event), capture_output=True,
                       text=True, env=dict(env, HOME=home), cwd=str(REPO), timeout=30)
    out = r.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


with tempfile.TemporaryDirectory(prefix="edt-") as tmp:
    home, base = os.path.join(tmp, "home"), os.path.join(tmp, "base")
    os.makedirs(home)
    subprocess.run(["git", "-C", str(REPO), "worktree", "add", "-q", "--detach", base, BASE], check=True, capture_output=True)
    try:
        for c in SEEN:
            checks.append(("base %s refuses: %s" % (BASE, c), guard(base, home, c).startswith(REASON)))
    finally:
        subprocess.run(["git", "-C", str(REPO), "worktree", "remove", "--force", base], capture_output=True)
    for c in PASS:
        checks.append(("branch passes: " + c, guard(str(REPO), home, c) == ""))
    for c in REFUSED:
        checks.append(("branch refuses: " + c, guard(str(REPO), home, c).startswith(REASON)))

for name, good in checks:
    print(("ok   " if good else "FAIL ") + name)
fails = sum(not g for _, g in checks)
print("env-dump-text-words: %d of %d checks passed" % (len(checks) - fails, len(checks)))
sys.exit(1 if fails else 0)
