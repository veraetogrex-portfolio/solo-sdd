#!/usr/bin/env python3
"""Live scenario of fix-stop-background-shell: the hook global/work_hooks.py of this repository (with --deployed, the
copy ~/.claude/hooks/work_hooks.py that `python3 sync.py push` lays out) run as a process on /usr/bin/python3, the way
Claude Code starts it, fed Stop events of a scratch git repository under a temporary HOME, with `background_tasks` in the
form of the Claude Code hooks reference. A new session_id per run. gh is faked (first in PATH) so no run reaches the
network.

Usage: python3 tests/stands/stop-background-shell.py [--deployed] (from the repository root)
Prints one PASS or FAIL line per check and `<n> of 8 checks passed`; code 0 when all pass. The stand creates and removes
its temporary folder itself."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = Path.home() / ".claude/hooks/work_hooks.py" if sys.argv[1:] == ["--deployed"] else ROOT / "global/work_hooks.py"
PY = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
SHELL = {"id": "b1", "type": "shell", "status": "running", "description": "npm run dev", "command": "npm run dev"}


def main():
    if sys.argv[1:] not in ([], ["--deployed"]):
        print(__doc__)
        return 2
    print("hook: %s" % HOOK)
    tmp = Path(tempfile.mkdtemp(prefix="stand-stop-bg-")).resolve()
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    home, fbin, repo, clean = tmp / "home", tmp / "bin", tmp / "r", tmp / "clean"
    for d in (home, fbin, repo, clean):
        d.mkdir()
    (fbin / "gh").write_text("#!/bin/sh\nexit 1\n")
    (fbin / "gh").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SOLO_SDD_", "GIT_", "CLAUDE"))}
    env.update(HOME=str(home), PATH="%s:%s" % (fbin, os.environ["PATH"]), GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    for d in (repo, clean):
        for a in (["init", "-q"], None, ["add", "-A"], ["commit", "-qm", "base"]):
            if a is None:
                (d / "app.css").write_text("a{}\n")
                continue
            subprocess.run(["git", "-C", str(d), *a], check=True, capture_output=True, env=env, stdin=subprocess.DEVNULL)
    (repo / "app.css").write_text("a{color:red}\n")
    sid = iter(range(100))

    def stop(d, tasks, uses):
        tr = tmp / ("t%d.jsonl" % next(sid))
        tr.write_text("".join(json.dumps({"type": "assistant", "message": {"content": [u]}}) + "\n" for u in uses))
        event = {"session_id": "stand-%s" % tr.stem, "cwd": str(d), "transcript_path": str(tr),
                 "last_assistant_message": "Done.", "background_tasks": tasks}
        p = subprocess.run([PY, str(HOOK), "stop"], input=json.dumps(event), capture_output=True, text=True, env=env,
                           timeout=60)
        if p.returncode:
            raise RuntimeError("hook stop: %s" % p.stderr)
        return p.stdout.strip()

    edit = [{"type": "tool_use", "name": "Edit", "input": {"file_path": str(repo / "app.css")}}]
    checks = []

    def check(n, what, ok, got):
        checks.append(ok)
        print("%s %d %s%s" % ("PASS" if ok else "FAIL", n, what, "" if ok else ": got %r" % got[:300]))

    def blocks(out):
        return '"decision": "block"' in out and "uncommitted edits" in out

    rows = [
        ("no background task: blocked for uncommitted edits", [], True),
        ("a running shell `npm run dev` alone: blocked", [SHELL], True),
        ("a running monitor alone: blocked",
         [{"id": "m1", "type": "monitor", "status": "running", "description": "watch log"}], True),
        ("a running shell, then a running subagent: silent",
         [SHELL, {"id": "a1", "type": "subagent", "status": "running", "agent_type": "general-purpose"}], False),
        ("a running teammate: silent", [{"id": "t1", "type": "teammate", "status": "running"}], False),
        ("a running entry of unknown type x: silent", [{"id": "u1", "type": "x", "status": "running"}], False),
        ("a running entry without type: silent", [{"id": "x1", "status": "running"}], False),
    ]
    for n, (what, tasks, want) in enumerate(rows, 1):
        out = stop(repo, tasks, edit)
        check(n, what, blocks(out) == want and (want or out == ""), out)

    ship = {"id": "b2", "type": "shell", "status": "running", "description": "ship",
            "command": "python3 ~/.local/bin/sdd-pr.py ship https://github.com/o/r/pull/1"}
    bash = [{"type": "tool_use", "name": "Bash", "input": {"command": c}}
            for c in ("git status", "python3 ~/.local/bin/sdd-pr.py ship https://github.com/o/r/pull/1")]
    out = stop(clean, [ship], bash)
    check(8, "the dispatcher waiting for delivery (running shell ship, Bash only, clean repository): silent", out == "", out)

    print("%d of %d checks passed" % (sum(checks), len(checks)))
    return 0 if all(checks) and len(checks) == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
