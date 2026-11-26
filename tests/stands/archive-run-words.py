#!/usr/bin/python3
"""Live scenario of change archive-run-words, steps 1-2, on the real guard hook (global/work_hooks.py).

1. A transcript where the session edits `src/app.py` and runs no `Review:` agent: every form is refused naming
   `src/app.py`; the TEXT rows pass (`echo solo-sdd archive add-words`, a wrapper's option value `solo-sdd`).
2. The same forms against a change with a foreign CLAIM and no edits: refused as a foreign archive.
Run from the repository root: python3 tests/stands/archive-run-words.py drives the repository's hook;
SOLO_SDD_HOOK=<path> drives another copy instead, such as the deployed ~/.claude/hooks/work_hooks.py. Temporary folders
are removed (HOME of the hook is one of them); the last line is the summary."""
import json, os, pathlib, subprocess, sys, tempfile

HOOK = os.environ.get("SOLO_SDD_HOOK") or pathlib.Path(__file__).resolve().parents[2] / "global" / "work_hooks.py"
FORMS = ["uvx --from solo-sdd solo-sdd archive add-words", "uv run python -m solo_sdd archive add-words",
         "python3 -W ignore -m solo_sdd archive add-words", "python3 -msolo_sdd archive add-words",
         "sudo -u root solo-sdd archive add-words", "env -u X solo-sdd archive add-words",
         "bash -c -- 'solo-sdd archive add-words'",
         # change fix-archive-runs-wrapper-values: the values of the other wrappers' options, a subshell, a short cluster
         "caffeinate -t 5 solo-sdd archive add-words", "caffeinate -w 1 solo-sdd archive add-words",
         "exec -a NAME solo-sdd archive add-words", "npx -p x solo-sdd archive add-words",
         "time -o /tmp/x solo-sdd archive add-words", "/usr/bin/time -f %e solo-sdd archive add-words",
         "(sudo -u root solo-sdd archive add-words)", "(env -u X solo-sdd archive add-words)",
         "sudo -Hu root solo-sdd archive add-words", "env -iu X solo-sdd archive add-words"]
TEXT = ["echo solo-sdd archive add-words", "uvx --from solo-sdd solo-sdd validate --all",
        "npx -p solo-sdd archive add-words", "npx --package solo-sdd archive add-words", "sudo -Hu solo-sdd archive add-words"]


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, capture_output=True, stdin=subprocess.DEVNULL, timeout=60, check=True)


def guard(env, inp):
    p = subprocess.run(["/usr/bin/python3", str(HOOK), "guard"], input=json.dumps(inp), capture_output=True, text=True,
                       env=env, timeout=60)
    return json.loads(p.stdout)["hookSpecificOutput"]["permissionDecisionReason"] if p.stdout.strip() else None


with tempfile.TemporaryDirectory() as t:
    t = os.path.realpath(t)
    env = dict(os.environ, HOME=os.path.join(t, "home"))
    edited, claimed = os.path.join(t, "edited"), os.path.join(t, "claimed")
    os.makedirs(os.path.join(edited, "src")); os.makedirs(os.path.join(edited, "solo-sdd/changes/add-words"))
    os.makedirs(os.path.join(claimed, "solo-sdd/changes/add-words"))
    pathlib.Path(edited, "src/app.py").write_text("x = 1\n")
    pathlib.Path(claimed, "solo-sdd/changes/add-words/CLAIM").write_text("claude 2026-11-11 session=OTHER\n")
    for d in (edited, claimed):
        git(d, "init", "-q")
    tr = os.path.join(t, "t.jsonl")
    pathlib.Path(tr).write_text(json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Edit", "input": {"file_path": os.path.join(edited, "src/app.py")}}]}}) + "\n")
    checks = []
    for c in FORMS:
        r = guard(env, {"session_id": "S1", "cwd": edited, "tool_name": "Bash", "transcript_path": tr, "tool_input": {"command": c}})
        checks.append(("1 review gate", c, bool(r) and "src/app.py" in r))
        r = guard(env, {"session_id": "S1", "cwd": claimed, "tool_name": "Bash", "tool_input": {"command": c}})
        checks.append(("2 foreign CLAIM", c, bool(r) and "taken by another agent" in r))
    for c in TEXT:
        r = guard(env, {"session_id": "S1", "cwd": edited, "tool_name": "Bash", "transcript_path": tr, "tool_input": {"command": c}})
        checks.append(("1 passes", c, r is None))
    for step, c, good in checks:
        print("%s %s: %s" % ("ok " if good else "FAILED", step, c))
    print("archive-run-words: %d of %d checks passed" % (sum(g for _, _, g in checks), len(checks)))
    passed = sum(g for _, _, g in checks)
sys.exit(0 if passed == len(checks) else 1)
