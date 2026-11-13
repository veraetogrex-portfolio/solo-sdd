#!/usr/bin/env python3
"""Live Scenario stand of change acceptance-evidence, steps 1-3, on the real global/work_hooks.py and global/sdd_dispatch.py.
Everything lives in one temporary folder (a git project, a worktree with an archived change, a HOME for the hook state)
that the stand removes itself."""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
HOOK, DISPATCH = str(ROOT / "global/work_hooks.py"), str(ROOT / "global/sdd_dispatch.py")
results = []


def check(name, good, detail):
    results.append(good)
    print(("ok   " if good else "FAIL ") + name + ": " + detail)


def tool(name, **ti):
    return {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": name, "input": ti}]}}


def guard(home, proj, lines, n):
    tr = os.path.join(home, "t%d.jsonl" % n)
    pathlib.Path(tr).write_text("".join(json.dumps(l) + "\n" for l in lines))
    inp = {"session_id": "S1", "cwd": proj, "tool_name": "Bash", "transcript_path": tr,
           "tool_input": {"command": "solo-sdd archive add-words --yes"}}
    r = subprocess.run([sys.executable, HOOK, "guard"], input=json.dumps(inp), capture_output=True, text=True,
                       env=dict(os.environ, HOME=home), timeout=60)
    out = json.loads(r.stdout) if r.stdout.strip() else None
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else "passed"


def accept(tmp, wt, live, env=None):
    st = os.path.join(tmp, "st.txt")
    pathlib.Path(st).write_text("STATUS: archived\nCHANGE: add-words\nWORKTREE: %s\nVALIDATE: true -> exit 0\n"
                                "LIVE: %s\nARCHIVE: changes/archive/2026-11-11-add-words\n" % (wt, live))
    t = time.monotonic()
    r = subprocess.run([sys.executable, DISPATCH, "accept", st], capture_output=True, text=True, timeout=120,
                       stdin=subprocess.DEVNULL, env=dict(os.environ, **(env or {})))
    return r.returncode, " | ".join(r.stdout.strip().splitlines()), time.monotonic() - t


tmp = os.path.realpath(tempfile.mkdtemp(prefix="acceptance-evidence-"))
try:
    home, proj = os.path.join(tmp, "home"), os.path.join(tmp, "proj")
    app, tasks = os.path.join(proj, "src/app.py"), os.path.join(proj, "solo-sdd/changes/add-words/tasks.md")
    for p in (app, tasks):
        os.makedirs(os.path.dirname(p), exist_ok=True)
        pathlib.Path(p).write_text("x\n")
    os.makedirs(home)
    subprocess.run(["git", "init", "-q", proj], check=True, stdin=subprocess.DEVNULL)
    edit, review, tick = tool("Edit", file_path=app), tool("Agent", description="Review: add-words", prompt="x"), tool("Edit", file_path=tasks)
    r = guard(home, proj, [edit], 1)
    check("1 no review: refused", "src/app.py" in r and "Review:" in r, r)
    r = guard(home, proj, [edit, review, edit, tick], 2)
    check("1 review, then a Nit fix and a tasks.md tick: passes", r == "passed", r)

    # Python, not a shell file: a temporary folder may be mounted without exec rights
    wt = os.path.join(tmp, "wt")
    arch = os.path.join(wt, "changes/archive/2026-11-11-add-words")
    os.makedirs(os.path.join(wt, "tests/stands"))
    os.makedirs(arch)
    pathlib.Path(wt, "tests/stands/words.py").write_text(
        "import sys, time\nif len(sys.argv) > 1: time.sleep(100)\nprint('words: 3 of 3 checks passed')\n")
    pathlib.Path(arch, "verification.md").write_text(
        "## Live Scenario\n\n1. `python3 tests/stands/words.py` prints the checks.\n2. Hanging: `python3 tests/stands/words.py --hang`, "
        "`sleep 100 | cat`.\n\n## Needs\n\nnone\n")
    subprocess.run(["git", "init", "-q", wt], check=True, stdin=subprocess.DEVNULL)
    code, out, _ = accept(tmp, wt, "echo ok -> ok")
    check("2 invented LIVE: code 1, not in the Live Scenario", code == 1 and "LIVE: echo ok — not in the Live Scenario" in out, out)
    code, out, _ = accept(tmp, wt, "python3 tests/stands/words.py -> 3 of 3 checks passed")
    check("2 LIVE from the scenario: compared as before", (code, out) == (0, "status matches"), out)
    code, out, _ = accept(tmp, wt, "python3 tests/stands/words.py -> 4 of 4")
    check("2 LIVE from the scenario, other text: text missing", code == 1 and "text missing" in out, out)

    for live in ("python3 tests/stands/words.py --hang", "sleep 100 | cat"):
        code, out, sec = accept(tmp, wt, live + " -> ok", {"SDD_DISPATCH_TIMEOUT": "2"})
        check("3 %s: timeout, code 1, under 10 s" % live, code == 1 and "LIVE: timeout after 2 s" in out and sec < 10,
              "%s (%.1f s)" % (out, sec))
finally:
    shutil.rmtree(tmp, ignore_errors=True)
print("acceptance-evidence: %d of %d checks passed" % (sum(results), len(results)))
sys.exit(0 if all(results) else 1)
