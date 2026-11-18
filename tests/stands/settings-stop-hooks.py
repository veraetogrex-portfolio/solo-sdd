#!/usr/bin/env python3
"""Live scenario of settings-stop-hooks: the real global/work_hooks.py run as a process on /usr/bin/python3, the way
Claude Code starts it, fed Stop and PreToolUse events of a temporary git project under a temporary HOME. Only gh is
faked (first in PATH): `gh pr view` answers an open PR. The push of step 6 is real, into a bare repository. Steps 7 and 8
run the stop in a git worktree: one that commits its own config, one of a repository that ignores the config file.

Usage: python3 tests/stands/settings-stop-hooks.py (from the repository root)
Prints one PASS or FAIL line per check and `<n> of 8 checks passed`; code 0 when all pass. The stand creates and
removes its temporary folder itself."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / "global/work_hooks.py"
PY = "/usr/bin/python3" if os.path.exists("/usr/bin/python3") else sys.executable
GH = '#!/bin/sh\necho \'{"state": "OPEN", "url": "https://github.com/o/stand/pull/7"}\'\n'


def main():
    tmp = Path(tempfile.mkdtemp(prefix="stand-stop-hooks-")).resolve()
    try:
        return run(tmp)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def run(tmp):
    home, fbin = tmp / "home", tmp / "bin"
    home.mkdir()
    fbin.mkdir()
    (fbin / "gh").write_text(GH)
    (fbin / "gh").chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(("SOLO_SDD_", "GIT_", "CLAUDE"))}
    env.update(HOME=str(home), PATH="%s:%s" % (fbin, os.environ["PATH"]), GIT_CONFIG_NOSYSTEM="1",
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
    sid = iter(range(100))

    def git(cwd, *a):
        subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, env=env, stdin=subprocess.DEVNULL)

    def project(name):
        d = tmp / name
        (d / "solo-sdd/changes/a").mkdir(parents=True)
        (d / "solo-sdd/changes/a/tasks.md").write_text("- [ ] one\n")
        git(tmp, "init", "-q", "-b", "main", str(d))
        git(d, "add", "-A")
        git(d, "commit", "-qm", "init")
        return d

    def config(d, text):
        (d / "solo-sdd/config").write_text(text)

    def hook(cmd, event):
        p = subprocess.run([PY, str(HOOK), cmd], input=json.dumps(event), capture_output=True, text=True, env=env,
                           timeout=60)
        if p.returncode:
            raise RuntimeError("hook %s: %s" % (cmd, p.stderr))
        return json.loads(p.stdout) if p.stdout.strip() else None

    def stop(d, *edited, push=False):
        """The stop reason (empty when not blocked) after a session that edited these files of d, and pushed."""
        uses = [{"type": "tool_use", "name": "Edit", "input": {"file_path": str(d / f)}} for f in edited]
        if push:
            uses.append({"type": "tool_use", "name": "Bash", "input": {"command": "git push -u origin HEAD"}})
        tr = tmp / ("t%d.jsonl" % next(sid))
        tr.write_text("".join(json.dumps({"type": "assistant", "message": {"content": [u]}}) + "\n" for u in uses))
        for f in edited:
            (d / f).write_text("edited %s\n" % tr.name)
        o = hook("stop", {"session_id": tr.stem, "cwd": str(d), "transcript_path": str(tr),
                          "last_assistant_message": "Done."})
        return o["reason"] if o else ""

    checks = []

    def check(n, what, ok, detail):
        checks.append(ok)
        print("%s %d. %s%s" % ("PASS" if ok else "FAIL", n, what, "" if ok else ": " + detail[-600:]))

    d = project("proj")
    r1 = stop(d, "notes.txt")
    config(d, "hooks.stop.uncommitted: off\n")
    r2 = stop(d, "notes.txt")
    check(1, "uncommitted edit: blocked without config, not with hooks.stop.uncommitted: off",
          "uncommitted edits" in r1 and r2 == "", "%r / %r" % (r1, r2))

    config(d, "")
    r1 = stop(d, "app.css")
    config(d, "hooks.stop.ui-check: off\nhooks.stop.uncommitted: off\n")
    r2 = stop(d, "app.css")
    check(2, "app.css without a browser check: blocked, not with hooks.stop.ui-check: off",
          "The interface changed (app.css)" in r1 and r2 == "", "%r / %r" % (r1, r2))

    config(d, "ui.extensions: .html, .jinja\nhooks.stop.uncommitted: off\n")
    r1 = stop(d, "page.jinja")
    check(3, "ui.extensions: .html, .jinja and page.jinja: blocked for the interface check",
          "The interface changed (page.jinja)" in r1, r1)

    config(d, "hooks.stop.uncommitted off\n")
    r1 = stop(d, "notes.txt")
    log = home / ".claude/hook-state/errors.log"
    text = log.read_text() if log.exists() else ""
    check(4, "a broken config line: blocked for uncommitted edits, errors.log names solo-sdd/config:1",
          "uncommitted edits" in r1 and "solo-sdd/config:1" in text, "%r / %r" % (r1, text))

    tasks, claim = d / "solo-sdd/changes/a/tasks.md", d / "solo-sdd/changes/a/CLAIM"
    tick = {"session_id": "tick", "cwd": str(d), "tool_name": "Edit",
            "tool_input": {"file_path": str(tasks), "old_string": "- [ ] one", "new_string": "- [x] one"}}
    config(d, "hooks.auto-claim: off\n")
    o1, off = hook("guard", tick), claim.exists()
    config(d, "")
    o2, on = hook("guard", tick), claim.exists()
    check(5, "a tasks.md tick: no CLAIM with hooks.auto-claim: off, a CLAIM without it",
          o1 is None and not off and o2 is None and on, "%r %r %r %r" % (o1, off, o2, on))

    p = project("proj-pr")
    git(tmp, "init", "-q", "--bare", str(tmp / "origin.git"))
    git(p, "remote", "add", "origin", str(tmp / "origin.git"))
    git(p, "checkout", "-qb", "change/a")
    git(p, "push", "-qu", "origin", "HEAD")
    config(p, "hooks.stop.open-pr: on\ndelivery.merge-by: human\n")
    r1 = stop(p, push=True)
    config(p, "hooks.stop.open-pr: on\ndelivery.merge-by: agent\n")
    r2 = stop(p, push=True)
    check(6, "an open PR after a push: not blocked under delivery.merge-by: human, blocked under agent",
          r1 == "" and "pull/7 is open and not merged" in r2, "%r / %r" % (r1, r2))

    w = project("proj-wt")
    config(w, "hooks.stop.open-pr: on\n")
    git(w, "add", "-A")
    git(w, "commit", "-qm", "config on")
    wt = tmp / "wt"
    git(w, "worktree", "add", "-q", str(wt), "-b", "change/wt")
    config(wt, "hooks.stop.open-pr: off\n")
    git(wt, "commit", "-qam", "config off")
    r1 = stop(wt, push=True)
    r2 = stop(w, push=True)
    check(7, "a worktree that commits hooks.stop.open-pr: off over the main's on: not blocked; the main checkout: blocked",
          r1 == "" and "pull/7 is open and not merged" in r2, "%r / %r" % (r1, r2))

    x = project("proj-ignored")
    (x / ".git/info/exclude").write_text("solo-sdd/config\n")
    config(x, "delivery.merge-by: human\n")
    wt2 = tmp / "wt-ignored"
    git(x, "worktree", "add", "-q", str(wt2), "-b", "change/wt")
    r1 = stop(wt2, push=True)
    check(8, "a worktree without the ignored config: the main's delivery.merge-by: human applies, not blocked",
          not (wt2 / "solo-sdd/config").exists() and r1 == "", r1)

    print("%d of %d checks passed" % (sum(checks), len(checks)))
    return 0 if all(checks) and len(checks) == 8 else 1


if __name__ == "__main__":
    sys.exit(main())
