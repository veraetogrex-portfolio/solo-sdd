#!/usr/bin/env python3
"""Stand of change worktree-guard-words: the repository's work_hooks.py guard on the scenario commands of Worktree add
by shell words and Worktree path line state, fed as hook input JSON (nothing of them is run), then the dispatcher's two
launch commands from skills/spec-dispatch/SKILL.md, checked by the guard and run in a scratch repository. The home and
the session folder lie outside the temporary roots; the stand removes them, the repository and the mktemp folder."""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
PLAIN = "git worktree add [-b <name> | -B <name> | --detach | -f] <path> [<commit>]"
checks = []


def check(good, text):
    checks.append(good)
    print("%s %s" % ("ok" if good else "FAIL", text))


home = os.path.realpath(tempfile.mkdtemp(prefix="wgw-home-", dir=os.path.expanduser("~")))
repo = os.path.realpath(tempfile.mkdtemp(prefix="wgw-repo-"))
made = None
try:
    def reason(cmd, cwd=home):
        inp = json.dumps({"session_id": "stand", "cwd": cwd, "tool_name": "Bash", "tool_input": {"command": cmd}})
        r = subprocess.run([PY, str(REPO / "global/work_hooks.py"), "guard"], input=inp, capture_output=True, text=True,
                           timeout=10, env=dict(os.environ, HOME=home))
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"] if r.stdout.strip() else ""

    cases = [  # (command, session folder, passes)
        ('git worktree "add" ~/wt', home, False),
        ('git "worktree" add ~/wt', home, False),
        ("git worktree ad\\d ~/wt", home, False),
        ("W=worktree; git $W add ~/wt", home, False),
        ("cat <<'EOF'\ngit worktree add /tmp/a\nEOF\ngit -C ~ worktree add wt", home, False),
        ("git worktree add -fb x /tmp/wt", home, False),
        ("git -C x worktree add /tmp/wt", home, False),
        ("git worktree add ~/code/proj/tmp/wt", home, False),
        ("git worktree add ../wt # /tmp/", home, False),
        ('git worktree add "${TMPDIR:-/tmp}/wt-x"', home, True),
        ("git worktree add -b feat /tmp/wt-y main", home, True),
        ('git commit -m "docs: explain git worktree add"', home, True),
        ("echo 'git worktree add /tmp/x'", home, True),
        ('TMPDIR=$HOME/Code; git worktree add "$TMPDIR/wt"', home, False),
        ('export TMPDIR=~/Code && git worktree add "${TMPDIR:-/tmp}/wt"', home, False),
        ("ln -s ~/Code /tmp/lnk && git worktree add /tmp/lnk/wt", home, False),
        ("cd ~/Code && git worktree add wt", "/private/tmp", False),
    ]
    for cmd, cwd, passes in cases:
        why = reason(cmd, cwd)
        good = not why if passes else PLAIN in why
        where = "folder outside the temporary roots" if cwd == home else cwd
        check(good, "%s (%s): %s" % ("passes" if passes else "refused naming the plain form", where, cmd.replace("\n", "\\n")))

    # the dispatcher's launch, two calls from MAIN
    subprocess.run(["git", "init", "-q", repo], check=True, capture_output=True, stdin=subprocess.DEVNULL)
    subprocess.run(["git", "-C", repo, "-c", "user.email=s@s", "-c", "user.name=s", "commit", "-q", "--allow-empty", "-m", "init"],
                   check=True, capture_output=True, stdin=subprocess.DEVNULL)
    mk = 'mktemp -d "${TMPDIR:-/tmp}/sdd-XXXXXX"'
    check(not reason(mk, repo), "passes: " + mk)
    made = subprocess.run(["bash", "-c", mk], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    add = "git worktree add -b change/x %s/wt-x" % made
    check(not reason(add, repo), "passes: git worktree add -b change/x <D>/wt-x")
    subprocess.run(["bash", "-c", add], cwd=repo, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL)
    listed = subprocess.run(["git", "worktree", "list"], cwd=repo, capture_output=True, text=True).stdout
    wt = os.path.join(made, "wt-x")
    check(wt in listed or os.path.realpath(wt) in listed, "git worktree list shows <D>/wt-x")
    log = os.path.join(home, ".claude/hook-state/errors.log")
    check(not os.path.exists(log), "no hook errors")
finally:
    for d in (home, repo, made):
        if d:
            shutil.rmtree(d, ignore_errors=True)

print("worktree-guard-words: %d of %d checks passed" % (sum(checks), len(checks)))
raise SystemExit(0 if all(checks) else 1)
