#!/usr/bin/env python3
"""Stand of change fix-setup-links-exclude (Requirement: Worktree venv link, scenario A later link fails).
A temporary MAIN tracks app/keep.txt and has an untracked app/node_modules and .venv; its worktree root is made
read-only (app/ stays writable), so the repository's sdd_worktree.py setup links app/node_modules and then fails
on the root .venv link. The made link must be in info/exclude, invisible to git status, and remove must not refuse.
Nothing outside the temporary folder changes."""
import os
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
TOOL = REPO / "global/sdd_worktree.py"
GIT = ["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null"]
ENV = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")  # no global ignore hides node_modules


def git(repo, *args):
    return subprocess.run(GIT + ["-C", str(repo)] + list(args), capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, check=True, env=ENV).stdout


def tool(cmd, main, wt):
    return subprocess.run([sys.executable, str(TOOL), cmd, str(main), str(wt)], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=120, env=ENV)


def put(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if os.geteuid() == 0:
    print("setup-links-exclude: skipped, running as root: a read-only mode does not stop a write")
    sys.exit(0)

checks = []
with tempfile.TemporaryDirectory(prefix="setup-links-exclude-") as d:
    main, wt = pathlib.Path(d) / "main", pathlib.Path(d) / "wt"
    main.mkdir()
    git(main, "init", "-q", "-b", "main")
    put(main / "app/keep.txt", "k\n")
    git(main, "add", "-A")
    git(main, "commit", "-qm", "init")
    git(main, "worktree", "add", "-q", "-b", "feat", str(wt))
    put(main / "app/node_modules/p/i.js", "1\n")
    put(main / ".venv/bin/python", "x\n")
    os.chmod(wt, 0o555)
    try:
        setup = tool("setup", main, wt)
    finally:
        os.chmod(wt, 0o755)
    checks.append(("setup ends with code 1 after the app/node_modules link",
                   setup.returncode == 1 and (wt / "app/node_modules/.sdd-worktree").exists(),
                   "code %d: %s" % (setup.returncode, setup.stderr.strip())))
    exclude = (main / ".git/info/exclude").read_text(encoding="utf-8").splitlines()
    status = git(wt, "status", "--short")
    checks.append(("info/exclude has node_modules, git status does not list app/node_modules",
                   "node_modules" in exclude and "app/node_modules" not in status, "status: %r" % status))
    remove = tool("remove", main, wt)
    checks.append(("remove is not refused for the links", remove.returncode == 0 and not wt.exists(),
                   "code %d: %s" % (remove.returncode, remove.stderr.strip())))

for name, ok, detail in checks:
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else " (" + detail + ")"))
passed = sum(ok for _, ok, _ in checks)
print("setup-links-exclude: %d of %d checks passed" % (passed, len(checks)))
sys.exit(0 if passed == len(checks) else 1)
