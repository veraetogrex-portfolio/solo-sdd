#!/usr/bin/env python3
"""Live scenario of ship-merge-gates, steps 1-5 of its verification.md: the real global/work_hooks.py guard on a project
with and without solo-sdd/, the real `solo-sdd install --hooks` into a temporary HOME, and the /ship step 7 commands
(`sdd-pr.py open`, `wait`, `merge`) against a bare repository with the fake gh of tests/stands/path-checklists.py.

Usage: python3 tests/stands/ship-merge-gates.py (from the repository root)
Code 0: every step matched. The stand creates and removes its temporary folder itself."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "global/work_hooks.py"
PR = ROOT / "global/sdd_pr.py"
WT = ROOT / "global/sdd_worktree.py"


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


base = load("delivery_stand", "delivery-branches.py")
lists = load("checklists_stand", "path-checklists.py")
OLD = ("The owner's global rules (~/.claude/CLAUDE.md, section 13) require Claude to merge its own verified pull requests "
       "with gh pr merge.")
PREFIX = "The owner's merge rule (solo-sdd)"


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-ship-gates-")).resolve()
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    home = tmp / "home"
    env = dict(os.environ, **base.GITENV, HOME=str(home), PATH=f"{tmp / 'bin'}:{os.environ['PATH']}", STAND_D=str(tmp),
               STAND_BARE=str(tmp / "origin.git"))
    env.pop("CLAUDE_PROJECT_DIR", None)
    (tmp / "bin").mkdir()
    home.mkdir()
    for name, text in (("gh-shared", base.GH), ("gh", lists.WRAP)):
        (tmp / "bin" / name).write_text(text)
        (tmp / "bin" / name).chmod(0o755)
    for f, text in (("state.json", '{"prs": []}'), ("bodies.json", "{}"), ("reviews.json", "{}")):
        (tmp / f).write_text(text)
    results = []

    def check(name, good, ok_text, detail):
        results.append(good)
        print(f"ok {name}: {ok_text}" if good else f"FAILED {name}: {detail}")

    def g(cwd, *a):
        p = subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, env=env, stdin=subprocess.DEVNULL)
        if p.returncode:
            raise RuntimeError(f"git {a}: {p.stderr}")
        return p.stdout.strip()

    def write(rel, text, at):
        p = Path(at) / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def guard(cwd, cmd):
        inp = {"session_id": "stand", "cwd": str(cwd), "tool_name": "Bash", "tool_input": {"command": cmd}}
        p = subprocess.run([sys.executable, str(HOOK), "guard"], input=json.dumps(inp), capture_output=True, text=True, env=env)
        out = json.loads(p.stdout) if p.stdout.strip() else {}
        return out.get("hookSpecificOutput", {}).get("permissionDecisionReason")

    def tool(script, *a, cwd):
        return subprocess.run([sys.executable, str(script), *map(str, a)], capture_output=True, text=True, env=env,
                              stdin=subprocess.DEVNULL, timeout=120, cwd=cwd)

    # 1-3. the guard: a project with solo-sdd/ and a repository without it
    tree, plain = tmp / "tree", tmp / "plain"
    for d in (tree, plain):
        subprocess.run(["git", "init", "-q", str(d)], check=True, env=env)
    (tree / "solo-sdd/specs").mkdir(parents=True)
    why = guard(tree, "gh pr merge 5 --squash")
    check("process tree", bool(why) and "sdd-pr.py merge" in why, "gh pr merge 5 --squash refused, the reason names sdd-pr.py merge",
          repr(why))
    api, msg = guard(tree, "gh api -X PUT repos/o/r/pulls/5/merge"), guard(tree, 'git commit -m "explain gh pr merge"')
    check("API form and a message", bool(api) and msg is None, "gh api -X PUT …/pulls/5/merge refused, git commit -m passes",
          f"api {api!r} message {msg!r}")
    other = guard(plain, "gh pr merge 5 --squash")
    check("no tree", other is None, "gh pr merge 5 --squash passes", repr(other))

    # 4. install --hooks replaces the old section 13 entry and keeps the other one
    (home / ".claude").mkdir()
    (home / ".claude/settings.json").write_text(json.dumps({"autoMode": {"allow": ["other entry", OLD]}}))
    p = subprocess.run([sys.executable, "-m", "solo_sdd", "install", "--agents", "claude", "--hooks"], capture_output=True,
                       text=True, env=dict(env, PYTHONPATH=str(ROOT)), cwd=tmp, stdin=subprocess.DEVNULL, timeout=120)
    allow = json.loads((home / ".claude/settings.json").read_text())["autoMode"]["allow"] if p.returncode == 0 else []
    rule = allow[1] if len(allow) == 2 else ""
    check("install --hooks", p.returncode == 0 and allow[:1] == ["other entry"] and rule.startswith(PREFIX)
          and "in a repository without a solo-sdd/ tree merges with gh pr merge" in rule and "CLAUDE.md" not in rule,
          "autoMode.allow: the other entry and one rule «%s…», gh pr merge only without solo-sdd/, no CLAUDE.md" % PREFIX,
          f"code {p.returncode} {p.stdout[-300:]!r} {p.stderr[-300:]!r} allow {allow!r}")

    # 5. /ship step 7 by hand: open, wait, merge for a change that edits a checklist path
    bare, main, wt = tmp / "origin.git", tmp / "main", tmp / "wt-pay"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True, env=env)
    subprocess.run(["git", "init", "-q", "-b", "main", str(main)], check=True, env=env)
    write(".gitignore", "solo-sdd/\n", main)
    write("docs/checklists/money-safety.md", "# Money safety\n\n" + lists.ITEMS, main)
    g(main, "add", "-A")
    g(main, "commit", "-qm", "init")
    g(main, "remote", "add", "origin", str(bare))
    g(main, "push", "-q", "-u", "origin", "main")
    write("solo-sdd/config", "delivery.mode: pr\ndelivery.merge-by: agent\nchecklist.money-safety.paths: billing/**\n"
          "checklist.money-safety.file: docs/checklists/money-safety.md\n", main)
    g(main, "worktree", "add", "-q", "-b", "change/pay", str(wt), "origin/main")
    tool(WT, "setup", main, wt, cwd=main)
    write("billing/charge.py", "x = 1\n", wt)
    g(wt, "add", "-A")
    g(wt, "commit", "-qm", "pay change")
    op = tool(PR, "open", wt, "main", "pay", cwd=wt)
    url = next((w for w in op.stdout.split() if w.startswith("https://")), "")
    wa = tool(PR, "wait", url, "--interval", "1", cwd=wt)
    mg = tool(PR, "merge", url, "squash", g(wt, "rev-parse", "HEAD"), cwd=wt)
    state = json.loads(subprocess.run(["gh", "pr", "view", url, "--json", "state"], capture_output=True, text=True, env=env,
                                      cwd=wt).stdout or "{}").get("state")
    check("ship step 7", op.returncode == 0 and wa.returncode == 0 and mg.returncode == 8
          and mg.stdout.strip() == "PR #1 checklist money-safety: 3 open items" and state == "OPEN",
          f"open code 0, wait code 0, merge code 8 «{mg.stdout.strip()}», the PR open",
          f"open {op.returncode} {op.stdout!r} {op.stderr!r} wait {wa.returncode} {wa.stdout!r} "
          f"merge {mg.returncode} {mg.stdout!r} {mg.stderr!r} state {state}")

    print("stand: %d of %d steps passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
