#!/usr/bin/python3
"""Live scenario of change settings-branch-names, steps 1-3: the branch prefix in `solo-sdd config` and the dispatch plan.

A temporary git repository with a solo-sdd/ tree and two ready committed changes `a` and `b`:
1. `config set delivery.branch-prefix feat/` gives code 0; with a branch `change/a` the plan prints `launch: a b`.
2. With a branch `feat/a` the plan prints `launch: b`, and `a` waits with `not merged: branch feat/a`.
3. `config set delivery.branch-prefix change/` while `feat/a` exists: exit 1 naming `feat/a`, the value stays `feat/`.
Run from the repository root: python3 tests/stands/settings-branch-names.py. The temporary folder is removed; the last
line is `<n> of 3 checks passed`."""
import os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
PLAN = str(ROOT / "global" / "sdd_dispatch_plan.py")
GIT = ["git", "-c", "init.defaultBranch=main", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"]
passed = []


def step(name, good, detail):
    passed.append(bool(good))
    print("%s %s: %s" % ("ok " if good else "FAILED", name, " | ".join(detail.strip().splitlines())))


def run(cwd, *args):
    p = subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
                       env=dict(os.environ, PYTHONPATH=str(ROOT)))
    return p.returncode, p.stdout, p.stderr


def main():
    tmp = tempfile.mkdtemp(prefix="settings-branch-names-")
    try:
        d = os.path.join(tmp, "proj")
        for cid in ("a", "b"):
            os.makedirs(os.path.join(d, "solo-sdd", "changes", cid))
            with open(os.path.join(d, "solo-sdd", "changes", cid, "proposal.md"), "w", encoding="utf-8") as f:
                f.write("# %s\n\n## Depends On\n\nnone\n" % cid)
        with open(os.path.join(d, "solo-sdd", "project.md"), "w", encoding="utf-8") as f:
            f.write("# Project\n")
        git = lambda *a: run(d, *(GIT + list(a)))
        git("init", "-q")
        git("add", "-A")
        git("commit", "-qm", "two changes")
        config = lambda *a: run(d, sys.executable, "-m", "solo_sdd", "config", *a)
        plan = lambda: run(d, sys.executable, PLAN, d)[1]

        code, out, _ = config("set", "delivery.branch-prefix", "feat/")
        git("branch", "change/a")
        got = plan()
        step("1 old prefix branch", code == 0 and "launch: a b\n" in got, "config set code %d; %s" % (
            code, next((l for l in got.splitlines() if l.startswith("launch:")), got)))

        git("branch", "feat/a")
        got = plan()
        step("2 team prefix branch", "launch: b\n" in got and "  a — not merged: branch feat/a" in got,
             "; ".join(l.strip() for l in got.splitlines() if l.startswith(("launch:", "  a"))))

        code, out, _ = config("set", "delivery.branch-prefix", "change/")
        value = config("get", "delivery.branch-prefix")[1].strip()
        step("3 guard", code == 1 and "feat/a" in out and value == "feat/", "exit %d: %s; value %s" % (code, out, value))
    finally:
        shutil.rmtree(tmp, True)
    print("%d of %d checks passed" % (sum(passed), len(passed)))
    return 0 if all(passed) and len(passed) == 3 else 1


if __name__ == "__main__":
    sys.exit(main())
