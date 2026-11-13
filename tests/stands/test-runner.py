#!/usr/bin/env python3
"""Stand of change test-runner: the repository's tests/run.py and tests/affected.json over quick stand files named as
every real tests/test_*.py, in a temporary folder it removes itself. Runs no real test."""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

TESTS = pathlib.Path(__file__).resolve().parents[1]
REAL = sorted("tests/" + p.name for p in TESTS.glob("test_*.py"))
BROKEN = "tests/test_sdd_pr.py"
results = []


def step(name, ok, detail=""):
    results.append(ok)
    print(("ok " if ok else "FAIL ") + name + ("" if ok else ": " + detail))


def main():
    root = pathlib.Path(tempfile.mkdtemp(prefix="stand-test-runner-"))
    try:
        (root / "tests").mkdir()
        for f in ("run.py", "affected.json"):
            shutil.copy(TESTS / f, root / "tests" / f)
        for f in REAL:
            (root / f).write_text("print('OUT %s')\n" % f)

        def run(*args):
            p = subprocess.run([sys.executable, "tests/run.py", *args], cwd=root, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, timeout=120)
            return p.returncode, p.stdout, p.stderr, re.findall(r"^(?:ok|FAIL) (\S+) \(", p.stdout, re.M)

        code, out, err, ran = run()
        step("all green", code == 0 and "failed: 0," in out and sorted(ran) == REAL and "OUT " not in out,
             f"code {code}, {len(ran)} of {len(REAL)} files")

        (root / BROKEN).write_text("print('OUT %s'); raise SystemExit(1)\n" % BROKEN)
        code, out, err, ran = run()
        shown = re.findall(r"^OUT (\S+)$", out, re.M)
        step("one file broken", code == 1 and shown == [BROKEN] and ("FAIL %s (" % BROKEN) in out
             and sorted(ran) == REAL, f"code {code}, output of {shown}")
        code, out, err, ran = run("--jobs", "1")
        step("failed first", ran[:1] == [BROKEN], f"first {ran[:1]}")

        code, out, err, ran = run("--failed")
        step("--failed", (code, ran) == (1, [BROKEN]), f"code {code}, ran {ran}")

        two = ["tests/test_cli.py", "tests/test_init.py"]
        code, out, err, ran = run(*two)
        step("two named files", (code, sorted(ran)) == (0, two), f"code {code}, ran {ran}")

        code, out, err, ran = run("tests/test_missing.py")
        step("unknown name", code == 2 and ran == [] and "tests/test_missing.py" in err, f"code {code}, ran {ran}")

        amap = json.loads((TESTS / "affected.json").read_text(encoding="utf-8"))
        path = "global/sdd_dispatch_plan.py"
        named = set(amap["always"]) | {t for v in amap["map"].values() for t in v}
        want = set(amap["always"]) | {f for f in REAL if f not in named}
        want |= {t for k, v in amap["map"].items() if k == path or (k.endswith("/") and path.startswith(k)) for t in v}
        want &= set(REAL)
        code, out, err, ran = run("--affected", path)
        step("--affected " + path, set(ran) == want and len(ran) == len(want) < len(REAL)
             and {"tests/test_sdd_dispatch_plan.py", "tests/test_sdd_eval.py"} <= set(ran),
             f"ran {len(ran)} of {len(REAL)}, missing {sorted(want - set(ran))}, extra {sorted(set(ran) - want)}")

        code, out, err, ran = run("--affected", "tools/new.py")
        step("--affected tools/new.py", sorted(ran) == REAL, f"ran {len(ran)} of {len(REAL)}")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    failed = results.count(False)
    print("SUMMARY: all steps passed" if not failed else f"SUMMARY: {failed} steps failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
