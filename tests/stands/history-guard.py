#!/usr/bin/python3
"""Live scenario of change history-guard, steps 1-3.

The real hook as Claude Code starts it: `/usr/bin/python3 <hook> guard` with a PreToolUse JSON on stdin, `cwd` a
temporary git repository with one commit and a bare remote, HOME a temporary folder. The base hook runs from a temporary
worktree of commit e262b7e (main when the change was planned), the branch hook from this repository.
Run from the repository root: python3 tests/stands/history-guard.py. The temporary folder and the worktree are removed;
the last line is the summary."""
import json, os, pathlib, shutil, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PY = "/usr/bin/python3"
BASE = "e262b7e"
FORCED = ("git push --force origin main", "git reset --hard HEAD")
TEXT = ('git commit -m "never git push --force"', "python3 sync.py push --force", "git push origin main")
results = []


def step(name, good, detail):
    results.append(good)
    print("%s %s: %s" % ("ok " if good else "FAILED", name, detail))


def git(*a, cwd=None):
    return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t"] + list(a), cwd=cwd, capture_output=True, text=True,
                          check=True, stdin=subprocess.DEVNULL).stdout.strip()


tmp = tempfile.mkdtemp(prefix="history-guard-")
base = os.path.join(tmp, "wt-base-" + BASE)
try:
    home, repo, remote = (os.path.join(tmp, x) for x in ("home", "repo", "remote.git"))
    os.makedirs(os.path.join(home, ".claude"))
    git("init", "-q", "--bare", remote)
    git("init", "-q", repo)
    git("commit", "-q", "--allow-empty", "-m", "one", cwd=repo)
    git("remote", "add", "origin", remote, cwd=repo)
    git("push", "-q", "origin", "HEAD:main", cwd=repo)
    git("worktree", "add", "-q", "--detach", base, BASE, cwd=ROOT)
    env = dict(os.environ, HOME=home, PATH="/usr/bin:/bin")
    env.pop("SOLO_SDD_EXPENSIVE_OK", None)

    def guard(hook_root, command):
        inp = {"session_id": "stand", "cwd": repo, "tool_name": "Bash", "tool_input": {"command": command}}
        p = subprocess.run([PY, os.path.join(hook_root, "global/work_hooks.py"), "guard"], input=json.dumps(inp), env=env,
                           capture_output=True, text=True, timeout=60)
        out = json.loads(p.stdout)["hookSpecificOutput"] if p.returncode == 0 and p.stdout.strip() else {}
        return out.get("permissionDecisionReason") if out.get("permissionDecision") == "deny" else None

    on_base = [guard(base, c) for c in FORCED]
    step("1 base " + BASE, on_base == [None, None], "; ".join("%s -> %s" % (c, "deny" if r else "passes") for c, r in zip(FORCED, on_base)))
    on_branch = [guard(str(ROOT), c) for c in FORCED]
    named = all(r and "No `--force` and no `git reset --hard`" in r and "new commit" in r and "git stash" in r for r in on_branch)
    step("2 branch refuses", named, "; ".join("%s -> %s" % (c, "deny" if r else "passes") for c, r in zip(FORCED, on_branch))
         + "; the reasons name the rule, a new commit and git stash: %s" % named)
    text = [guard(str(ROOT), c) for c in TEXT]
    step("3 branch passes", text == [None] * 3, "; ".join("%s -> %s" % (c, "deny" if r else "passes") for c, r in zip(TEXT, text)))
    log = os.path.join(home, ".claude/hook-state/errors.log")
    step("hook errors", not os.path.exists(log), open(log).read()[-300:] if os.path.exists(log) else "none")
finally:
    subprocess.run(["git", "worktree", "remove", "--force", base], cwd=ROOT, capture_output=True, stdin=subprocess.DEVNULL)
    shutil.rmtree(tmp, True)

print("history-guard stand: %d of %d steps ok%s" % (sum(results), len(results), "" if all(results) and results else ", FAILED"))
