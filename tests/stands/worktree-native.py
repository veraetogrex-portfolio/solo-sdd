#!/usr/bin/env python3
"""Live Scenario stand of change worktree-native: the `guard` hook and the `.gitignore` command from project-init.
Run from the repository root: `python3 tests/stands/worktree-native.py [path to work_hooks.py]`
(by default the hook from this repository). Code 0: everything as expected."""
import json, os, re, subprocess, sys, tempfile

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../..")
HOOK = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "global/work_hooks.py")
results = []

def check(good, text):
    results.append(good)
    print("%s  %s" % ("ok  " if good else "FAIL", text))

with tempfile.TemporaryDirectory(prefix="wt-native-stand-") as tmp:
    home, repo = os.path.join(tmp, "home"), os.path.realpath(os.path.join(tmp, "repo"))
    os.makedirs(home); os.makedirs(repo)
    subprocess.run(["git", "-C", repo, "init", "-q"], check=True)
    agent = {"description": "Implement x", "prompt": "x", "model": "haiku", "isolation": "worktree"}
    cases = [("Bash", {"command": "claude --worktree feature-auth"}, False),
             ("Bash", {"command": "claude -w"}, False),
             ("EnterWorktree", {"name": "feat"}, False),
             ("EnterWorktree", {"path": repo + "/.claude/worktrees/a"}, False),
             ("Agent", agent, False),
             ("Bash", {"command": "codex exec --worktree 'implement x'"}, True),
             ("Bash", {"command": "git worktree add ../copy"}, True)]
    for tool, tin, want_deny in cases:
        # git worktree add ../copy is refused from a session folder outside the temporary roots (the real home)
        cwd = os.path.expanduser("~") if "worktree add" in tin.get("command", "") else repo
        inp = {"session_id": "stand", "cwd": cwd, "tool_name": tool, "tool_input": tin}
        r = subprocess.run([sys.executable, HOOK, "guard"], input=json.dumps(inp), capture_output=True, text=True,
                           env=dict(os.environ, HOME=home))
        out = json.loads(r.stdout)["hookSpecificOutput"] if r.stdout.strip() else {}
        denied = out.get("permissionDecision") == "deny"
        label = "%s %s -> %s" % (tool, json.dumps(tin, ensure_ascii=False), "deny" if denied else "let through")
        check(denied == want_deny, label + ("  [%s]" % out.get("permissionDecisionReason", "")[:120] if denied != want_deny else ""))
    elog = os.path.join(home, ".claude/hook-state/errors.log")
    if os.path.exists(elog):  # the hook is fail-open: an internal error would look like "let through"
        check(False, "the hook crashed:\n" + open(elog).read())

    skill = open(os.path.join(ROOT, "skills/project-init/SKILL.md")).read()
    cmds = [c for c in re.findall(r"`([^`]+)`", skill) if ".claude/worktrees/" in c and "check-ignore" in c]
    check(len(cmds) == 1, "project-init has exactly one .gitignore command (found %d)" % len(cmds))
    if len(cmds) == 1:
        def run(name, content):
            d = os.path.join(tmp, name); os.makedirs(d)
            subprocess.run(["git", "-C", d, "init", "-q"], check=True)
            if content is not None:
                open(os.path.join(d, ".gitignore"), "wb").write(content)
            return d
        def go(d):
            subprocess.run(["bash", "-c", cmds[0]], cwd=d, capture_output=True)
            return open(os.path.join(d, ".gitignore"), "rb").read()
        ign = lambda d: subprocess.run(["git", "-C", d, "check-ignore", "-q", ".claude/worktrees/a"]).returncode
        d = run("a", b".env")
        lines = go(d).decode().splitlines()
        check(lines == [".env", ".claude/worktrees/"] and ign(d) == 0, "without a trailing newline: %s, check-ignore %d" % (lines, ign(d)))
        check(go(d).decode().splitlines().count(".claude/worktrees/") == 1, "repeated run: the line once")
        d = run("c", b".claude/\n")
        check(go(d) == b".claude/\n", "the .claude/ rule already exists: file unchanged")
        d = run("d", None)
        check(go(d) == b".claude/worktrees/\n" and ign(d) == 0, "no .gitignore: file created")
    ok = all(results)
    print("total: %s" % ("%d of %d as expected" % (len(results), len(results)) if ok else "there are mismatches"))
sys.exit(0 if ok else 1)
