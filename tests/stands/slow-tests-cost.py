#!/usr/bin/env python3
"""Stand of change slow-tests-cost: the edited test files on the base commit (BASE, the tree before the change, exported
with git archive into a temporary folder it removes itself) and on the branch.

1. Counts by Python's ast the test methods and the assertions (`assert` statements and `self.assert*` calls) of every
   edited test file on both sides: equal, or the file is named.
2. Runs every test class of those files that the diff touches (the class, a base class or a top-level definition it
   names, directly or through others, differs from the base) as its own process, from outside each tree, with
   SOLO_SDD_TESTS=slow, the base and the branch run of a class side by side, at most 8 at once; prints the seconds of each file (the sum of its classes) and the
   totals, and `SUMMARY: all steps passed` when every class passes on both sides and the branch total is at least 10%
   below the base total.
"""
import ast
import concurrent.futures
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
TIER = "slow"  # the tier the Tests row runs before every delivery
# The tree before this change, pinned: the fork point from main moves once the branch merges. It is main after the
# merge of hooks-test-unittest and test-growth-brake; a later merge of main into the branch moves it here.
BASE = "58e8dae3806323534c5cf58219a3fb156427ce4a"
LIST = ("import sys, unittest\nfor m in sys.argv[1:]:\n    seen = []\n"
        "    def walk(s):\n        for t in s:\n            if isinstance(t, unittest.TestSuite):\n                walk(t)\n"
        "            elif type(t).__name__ not in seen:\n                seen.append(type(t).__name__)\n"
        "    walk(unittest.defaultTestLoader.loadTestsFromName(m))\n    print(m, *seen)\n")


def counts(src):
    """(test methods, assertions) of a test file's source."""
    tests = asserts = 0
    for n in ast.walk(ast.parse(src)):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name.startswith("test_"):
            tests += 1
        elif isinstance(n, ast.Assert):
            asserts += 1
        elif (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr.startswith("assert")
              and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"):
            asserts += 1
    return tests, asserts


def bound(n):
    """The names a top-level statement binds."""
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [n.name]
    if isinstance(n, (ast.Import, ast.ImportFrom)):
        return [(a.asname or a.name).split(".")[0] for a in n.names]
    return [t.id for t in ast.walk(n) if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)]


def tops(src):
    """{top-level name: ast dump of the statements that bind it} of a module's source."""
    out = {}
    for n in ast.parse(src).body:
        for name in bound(n):
            out[name] = out.get(name, "") + ast.dump(n)
    return out


def touched(base_src, branch_src):
    """The top-level names of the branch module that differ from the base or name, directly or through other top-level
    names, one that differs: the test classes whose fixtures, examples or timeouts this change can have moved."""
    old, new = tops(base_src), tops(branch_src)
    changed = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
    uses = {}
    for n in ast.parse(branch_src).body:
        for name in bound(n):
            uses.setdefault(name, set()).update(x.id for x in ast.walk(n) if isinstance(x, ast.Name))
    hit = set(changed)
    while True:
        more = {k for k, v in uses.items() if k not in hit and v & hit}
        if not more:
            return hit & set(new)
        hit |= more


def lost(base, branch):
    """The files whose counts differ: {file: (base counts, branch counts)}."""
    return {f: (base[f], branch.get(f)) for f in base if base[f] != branch.get(f)}


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT)] + list(args), capture_output=True, text=True, check=True,
                          stdin=subprocess.DEVNULL).stdout


def python():
    """The first interpreter that imports hypothesis: this one, then /usr/bin/python3."""
    for exe in (sys.executable, "/usr/bin/python3"):
        if exe and subprocess.run([exe, "-c", "import hypothesis"], capture_output=True,
                                  stdin=subprocess.DEVNULL).returncode == 0:
            return exe
    raise SystemExit("no interpreter here imports hypothesis: python3 -m pip install --user hypothesis")


def env_for(tree):
    e = {k: v for k, v in os.environ.items() if k not in ("SOLO_SDD_TESTS", "PYTHONPATH")}
    e.update(SOLO_SDD_TESTS=TIER, PYTHONPATH=str(tree / "tests"))
    return e


def classes(exe, tree, modules, cwd):
    r = subprocess.run([exe, "-c", LIST] + modules, cwd=cwd, env=env_for(tree), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=120)
    if r.returncode:
        raise SystemExit("listing the classes of %s failed:\n%s" % (tree, r.stderr))
    return {ln.split()[0]: ln.split()[1:] for ln in r.stdout.splitlines() if ln.strip()}


def run_class(exe, tree, unit, cwd):
    t = time.monotonic()
    r = subprocess.run([exe, "-m", "unittest", unit], cwd=cwd, env=env_for(tree), capture_output=True, text=True,
                       stdin=subprocess.DEVNULL, timeout=900)
    ran = re.search(r"(?m)^Ran (\d+) tests? in ", r.stderr)
    return r.returncode, time.monotonic() - t, int(ran.group(1)) if ran else 0, r.stderr[-3000:]


def main():
    sys.stdout.reconfigure(line_buffering=True)
    base = BASE
    on_base = set(git("ls-tree", "-r", "--name-only", base, "tests/").split())
    edited = sorted(f for f in git("diff", "--name-only", base, "--", "tests/").split()
                    if re.fullmatch(r"tests/test_\w+\.py", f) and f in on_base and (ROOT / f).is_file())
    new = sorted(f for f in git("diff", "--name-only", base, "--", "tests/").split()
                 if re.fullmatch(r"tests/test_\w+\.py", f) and f not in on_base)
    print("base: %s; edited test files: %s; new, not timed: %s" % (base[:12], ", ".join(edited) or "none",
                                                                   ", ".join(new) or "none"))
    ok = bool(edited)
    b = {f: counts(git("show", "%s:%s" % (base, f))) for f in edited}
    h = {f: counts((ROOT / f).read_text(encoding="utf-8")) for f in edited}
    for f in edited:
        print("counts %s: base %d tests %d asserts, branch %d tests %d asserts" % ((f,) + b[f] + h[f]))
    gone = lost(b, h)
    print("step 1 %s: test methods and assertions %s" % ("FAIL" if gone else "ok",
                                                         "differ in " + ", ".join(gone) if gone else "equal"))
    ok = ok and not gone
    exe = python()
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="slow-tests-cost-")).resolve()
    try:
        tar = tmp / "base.tar"
        git("archive", "-o", str(tar), base)
        (tmp / "base").mkdir()
        subprocess.run(["tar", "-xf", str(tar), "-C", str(tmp / "base")], check=True, stdin=subprocess.DEVNULL)
        (tmp / "cwd").mkdir()
        trees = {"base": tmp / "base", "branch": ROOT}
        modules = [pathlib.Path(f).stem for f in edited]
        units = {side: classes(exe, tree, modules, tmp / "cwd") for side, tree in trees.items()}
        jobs, skipped = [], 0
        for f, m in zip(edited, modules):
            hit = touched(git("show", "%s:%s" % (base, f)), (ROOT / f).read_text(encoding="utf-8"))
            for c in sorted(set(units["base"].get(m, [])) | set(units["branch"].get(m, []))):
                if c in hit:
                    jobs += [(side, m, c) for side in trees]
                else:
                    skipped += 1
        start, secs, tests = time.monotonic(), {}, {}
        print("step 2: %d touched classes on each side (%d untouched not run), %s, SOLO_SDD_TESTS=%s, load %s" % (
            len(jobs) // 2, skipped, exe, TIER, " ".join("%.2f" % x for x in os.getloadavg())))
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, os.cpu_count() or 2)) as pool:
            futs = {pool.submit(run_class, exe, trees[s], "%s.%s" % (m, c), tmp / "cwd"): (s, m, c)
                    for s, m, c in jobs}
            for fut in concurrent.futures.as_completed(futs):
                s, m, c = futs[fut]
                code, sec, ran, err = fut.result()
                secs[(s, m)] = secs.get((s, m), 0.0) + sec
                tests[(s, m)] = tests.get((s, m), 0) + ran
                if code:
                    ok = False
                    print("FAIL %s %s.%s (code %d):\n%s" % (s, m, c, code, err))
        for m in modules:
            print("seconds tests/%s.py: base %.1f (%d tests), branch %.1f (%d tests)" % (
                m, secs.get(("base", m), 0), tests.get(("base", m), 0), secs.get(("branch", m), 0),
                tests.get(("branch", m), 0)))
        tb = sum(v for (s, _), v in secs.items() if s == "base")
        th = sum(v for (s, _), v in secs.items() if s == "branch")
        cut = 100 * (1 - th / tb) if tb else 0
        fast = th <= 0.9 * tb
        print("total seconds: base %.1f, branch %.1f, %.0f%% less; wall %.0f s, load %s" % (
            tb, th, cut, time.monotonic() - start, " ".join("%.2f" % x for x in os.getloadavg())))
        print("step 2 %s: every class passes on both sides and the branch total is %s 10%% below the base" % (
            "ok" if ok and fast else "FAIL", "at least" if fast else "not"))
        ok = ok and fast
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("SUMMARY: all steps passed" if ok else "SUMMARY: FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
