#!/usr/bin/env python3
"""Live scenario of settings-working-copy, steps 1-4: the real global/sdd_worktree.py, sdd_dispatch_plan.py and
sdd_dispatch.py in a temporary git project whose settings are written by the real `python3 -m solo_sdd config set`.

Usage: python3 tests/stands/settings-working-copy.py (from the repository root)
Prints one line per check and `<n> of 4 checks passed`; code 0 when all passed. Step 4 needs macOS `sandbox-exec` to
deny the loopback probe. The stand creates and removes its temporary folder itself."""
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WT, PLAN, DISPATCH = (str(ROOT / "global" / n) for n in ("sdd_worktree.py", "sdd_dispatch_plan.py", "sdd_dispatch.py"))
ENV = dict(os.environ, PYTHONPATH=str(ROOT), GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@t")
ENV.pop("SDD_DISPATCH_TIMEOUT", None)
DENY = "(version 1)(allow default)(deny network*)"
results = []


def sh(args, cwd=None, env=None):
    r = subprocess.run([str(a) for a in args], cwd=cwd, capture_output=True, text=True, stdin=subprocess.DEVNULL,
                       timeout=120, env=env or ENV)
    return r.returncode, r.stdout, r.stderr


def git(repo, *args):
    code, out, err = sh(["git", "-C", repo] + list(args))
    if code:
        raise AssertionError("git %s: %s" % (" ".join(args), err))
    return out


def config(main, *args):
    return sh([sys.executable, "-m", "solo_sdd", "config"] + list(args), cwd=main)


def put(base, rel, text):
    p = Path(base, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def check(name, fn):
    try:
        fn()
        results.append(True)
        print("PASS %s" % name)
    except AssertionError as e:
        results.append(False)
        print("FAIL %s: %s" % (name, e))


def need(cond, what):
    if not cond:
        raise AssertionError(what)


def project(base, name):
    main = os.path.join(base, name)
    os.makedirs(main)
    git(main, "init", "-q", "-b", "main")
    put(main, ".gitignore", "node_modules/\n.venv/\n")
    put(main, "AGENTS.md", "# Stand\n\n## Commands\n\n| Tests | `true` |\n")
    put(main, "solo-sdd/project.md", "# Stand\n")
    put(main, "solo-sdd/changes/a/proposal.md", "# a\n\n## Depends On\n\nnone\n\n## Impact\n\n- `x.txt`\n")
    git(main, "add", "-A")
    git(main, "commit", "-qm", "init")
    return main


def main():
    base = tempfile.mkdtemp(prefix="settings-working-copy-")
    try:
        def prepare_and_links():
            main = project(base, "one")
            for key, value in (("worktree.prepare", "touch prepared"), ("worktree.links", "node_modules")):
                code, out, err = config(main, "set", key, value)
                need(code == 0, "config set %s: %s %s" % (key, out, err))
            put(main, "node_modules/p/i.js", "1\n")
            put(main, ".venv/bin/python", "x\n")
            wt = os.path.join(base, "one-wt")
            git(main, "worktree", "add", "-q", "-b", "change/a", wt)
            code, out, err = sh([sys.executable, WT, "setup", main, wt])
            need(code == 0, "setup exit %d: %s" % (code, err))
            need("command: touch prepared" in out, "the summary names the command: %r" % out)
            need(os.path.isfile(os.path.join(wt, "prepared")), "the prepare command ran in the worktree")
            need(os.path.islink(os.path.join(wt, "node_modules", "p")), "node_modules is linked")
            need(not os.path.lexists(os.path.join(wt, ".venv")), ".venv is not linked")
        check("1 worktree.prepare and worktree.links from the config, no Working copy section", prepare_and_links)

        def old_items():
            main = project(base, "two")
            with open(os.path.join(main, "AGENTS.md"), "a", encoding="utf-8") as f:
                f.write("\n## Working copy\n\n- Shared: `CHANGELOG.md`\n- Orchestrators: 4\n")
            code, out, err = config(main, "get", "dispatch.shared")
            need((code, out, err) == (0, "CHANGELOG.md\n", "source: AGENTS.md\n"), "config get dispatch.shared: %r" % ((code, out, err),))
            code, out, err = sh([sys.executable, PLAN, main])
            need(code == 0 and out.startswith("limit: 4,"), "the plan limit: %r %r" % (out, err))
            code, out, err = config(main, "get", "dispatch.limit")
            need((code, out, err) == (0, "4\n", "source: AGENTS.md\n"), "config get dispatch.limit: %r" % ((code, out, err),))
        check("2 the Working copy items as the old source: dispatch.shared and dispatch.limit agree with the plan", old_items)

        def check_timeout():
            main = project(base, "three")
            code, out, err = config(main, "set", "dispatch.check-timeout", "900")
            need(code == 0, "config set: %s %s" % (out, err))
            wt = os.path.join(base, "three-wt")
            git(main, "worktree", "add", "-q", "-b", "change/a", wt)
            need(sh([sys.executable, WT, "setup", main, wt])[0] == 0, "setup")
            put(wt, "x.txt", "x\n")
            git(wt, "add", "-A")
            git(wt, "commit", "-qm", "a: x")
            t = time.monotonic()
            code, out, err = sh([sys.executable, DISPATCH, "land-local", main, wt, "a", "--check", "sleep 5"],
                                env=dict(ENV, SDD_DISPATCH_TIMEOUT="1"))
            need("sleep 5: timeout after 1 s" in out and code in (3, 4), "land-local exit %d: %r %r" % (code, out, err))
            need(time.monotonic() - t < 60, "the variable won over dispatch.check-timeout: 900")
        check("3 SDD_DISPATCH_TIMEOUT wins over dispatch.check-timeout in land-local", check_timeout)

        def loopback():
            need(shutil.which("sandbox-exec") is not None, "no sandbox-exec: the step needs macOS")
            main = project(base, "four")
            lines = {}
            for value in ("on", "off"):
                code, out, err = config(main, "set", "dispatch.loopback", value)
                need(code == 0, "config set: %s %s" % (out, err))
                code, out, err = sh(["sandbox-exec", "-p", DENY, sys.executable, PLAN, main])
                need(code == 0 and len(out.splitlines()) > 1, "the plan under sandbox-exec: %r %r" % (out, err))
                lines[value] = out.splitlines()[1]
            need(lines["on"].startswith("loopback: blocked (needed by the project): "), "on: %r" % lines["on"])
            need(lines["off"].startswith("loopback: blocked: "), "off: %r" % lines["off"])
        check("4 dispatch.loopback on marks a denied loopback as needed by the project, off does not", loopback)
    finally:
        shutil.rmtree(base, ignore_errors=True)
    print("%d of %d checks passed" % (results.count(True), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
