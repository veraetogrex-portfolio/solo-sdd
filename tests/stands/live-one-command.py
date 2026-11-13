#!/usr/bin/env python3
"""Live Scenario stand of change status-live-one-command: three `archived` handbacks that differ only in `LIVE`.
Run from the repository root: `python3 tests/stands/live-one-command.py [path to work_hooks.py]`
(by default the hook from this repository; after `sync.py push`, `~/.claude/hooks/work_hooks.py`). Code 0: all three as expected."""
import json, os, subprocess, sys, tempfile

HOOK = os.path.expanduser(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "../../global/work_hooks.py")
CASES = (("npm run build && node check.ts -> ok", "&&"), ("node check.ts | tail -1 -> ok", "|"),
         ('COUNCIL_DEV=1 node check.ts --title "a; b" -> ok', None))

with tempfile.TemporaryDirectory(prefix="live-stand-") as tmp:
    repo = os.path.realpath(os.path.join(tmp, "repo"))
    arch = "openspec/changes/archive/2026-10-24-demo"
    os.makedirs(os.path.join(repo, arch))
    open(os.path.join(repo, arch, "tasks.md"), "w").write("- [x] a\n")
    git = lambda *a: subprocess.run(["git", "-C", repo, "-c", "user.email=t@t", "-c", "user.name=t"] + list(a),
                                    check=True, capture_output=True, text=True).stdout.strip()
    git("init", "-q"); git("add", "-A"); git("commit", "-qm", "archive demo")
    fields = dict(STATUS="archived", CHANGE="demo", BRANCH="main", WORKTREE=repo, COMMIT=git("rev-parse", "HEAD"), ARCHIVE=arch,
                  VALIDATE="openspec validate --all --strict --no-interactive -> exit 0", TESTS="tests -> exit 0", REVIEW="2 of 2",
                  AGENTS="none", HOOKS="none", NOT_VERIFIED="nothing", NOTES="stand")
    ok = True
    for live, sign in CASES:
        msg = "\n".join("%s: %s" % kv for kv in dict(fields, LIVE=live).items())
        inp = {"session_id": "stand", "cwd": repo, "tool_name": "SubagentHandback", "tool_input": {"message": msg}}
        r = subprocess.run([sys.executable, HOOK, "guard"], input=json.dumps(inp), capture_output=True, text=True,
                           env=dict(os.environ, HOME=tmp))
        out = json.loads(r.stdout)["hookSpecificOutput"] if r.stdout.strip() else {}
        reason = out.get("permissionDecisionReason", "")
        problems = [l[2:] for l in reason.splitlines() if l.startswith("- ")]
        good = (not out) if sign is None else (out.get("permissionDecision") == "deny" and len(problems) == 1
                                               and problems[0].startswith("LIVE:") and "«%s»" % sign in problems[0])
        ok &= good
        print("%s  %s -> %s" % ("ok  " if good else "FAIL", live, "deny: " + "; ".join(problems) if out else "let through"))
    elog = os.path.join(tmp, ".claude/hook-state/errors.log")
    if os.path.exists(elog):  # the hook is fail-open: an internal error would look like "let through"
        ok = False
        print("FAIL  the hook crashed:\n" + open(elog).read())
    print("total: %s" % ("3 of 3 as expected" if ok else "there are mismatches"))
sys.exit(0 if ok else 1)
