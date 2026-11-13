#!/usr/bin/env python3
"""Stand of change test-marks: the repository's tests/run.py and tests/marks.py over quick stand files in a temporary
folder it removes itself, then the two release files of the repository in the slow tier, where every test is skipped.
Runs no real slow test."""
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

TESTS = pathlib.Path(__file__).resolve().parents[1]
ROOT = TESTS.parent
MARKED = """import os
import unittest
import marks


def ran(name):
    with open(os.environ["STAND_LOG"], "a") as h:
        h.write(name + "\\n")


class T(unittest.TestCase):
    def test_plain(self):
        ran("plain")

    @marks.slow
    def test_slow(self):
        ran("slow")

    @marks.release
    def test_release(self):
        ran("release")


@marks.release
class R(unittest.TestCase):
    def test_in_class(self):
        ran("release-class")


if __name__ == "__main__":
    unittest.main()
"""
SLEEPER = """import time
import unittest


class T(unittest.TestCase):
    def test_sleep(self):
        time.sleep(3)


if __name__ == "__main__":
    unittest.main()
"""
results = []


def step(name, ok, detail=""):
    results.append(ok)
    print(("ok " if ok else "FAIL ") + name + ("" if ok else ": " + detail))


def python():
    """The first interpreter that imports hypothesis, which the release files of the repository need."""
    for exe in (sys.executable, "/usr/bin/python3"):
        try:
            if subprocess.run([exe, "-c", "import hypothesis"], stdin=subprocess.DEVNULL,
                              capture_output=True).returncode == 0:
                return exe
        except OSError:
            pass
    return sys.executable


def main():
    exe = python()
    root = pathlib.Path(tempfile.mkdtemp(prefix="stand-test-marks-"))
    log = root / "ran.log"
    env = {k: v for k, v in os.environ.items() if k != "SOLO_SDD_TESTS"}
    env["STAND_LOG"] = str(log)
    try:
        (root / "tests").mkdir()
        for f in ("run.py", "marks.py"):
            shutil.copy(TESTS / f, root / "tests" / f)
        (root / "tests" / "test_marked.py").write_text(MARKED)

        def run(*args, cwd=root, extra=None):
            log.write_text("")
            p = subprocess.run([exe, *args], cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                               timeout=300, env=dict(env, **(extra or {})))
            skipped = re.search(r"(?m)^skipped: (\d+)$", p.stdout)
            return p.returncode, p.stdout + p.stderr, sorted(log.read_text().split()), skipped and int(skipped.group(1))

        code, out, ran, skipped = run("tests/run.py", "--tier", "fast")
        step("fast: no marked test runs", (code, ran, skipped) == (0, ["plain"], 3), f"code {code}, ran {ran}, "
             f"skipped {skipped}")
        code, out, ran, skipped = run("tests/run.py", "--tier", "slow")
        step("slow: the slow tests run, release skipped", (code, ran, skipped) == (0, ["plain", "slow"], 2),
             f"code {code}, ran {ran}, skipped {skipped}")
        code, out, ran, skipped = run("tests/run.py", "--tier", "release")
        step("release: every test runs", (code, ran, skipped) == (0, ["plain", "release", "release-class", "slow"], 0),
             f"code {code}, ran {ran}, skipped {skipped}")

        code, out, ran, _ = run("tests/test_marked.py")
        step("direct run without the variable: every test runs",
             (code, ran) == (0, ["plain", "release", "release-class", "slow"]), f"code {code}, ran {ran}")
        code, out, ran, _ = run("tests/test_marked.py", extra={"SOLO_SDD_TESTS": "slwo"})
        step("SOLO_SDD_TESTS=slwo fails the file naming it", code != 0 and "slwo" in out and ran == [],
             f"code {code}, ran {ran}: {out.strip()[-200:]}")

        (root / "tests" / "test_sleep.py").write_text(SLEEPER)
        code, out, ran, _ = run("tests/run.py", "--tier", "fast")
        m = re.search(r"(?m)^T\.test_sleep took (\d+\.\d) s, over the 2 s of the fast tier", out)
        step("fast: an unmarked 3 s test fails the run, named with its seconds",
             code == 1 and m is not None and float(m.group(1)) >= 3.0 and "FAIL tests/test_sleep.py (" in out,
             f"code {code}: {out.strip()[-300:]}")
        if m:
            print("  " + m.group(0))

        files = ["tests/test_publish_first.py", "tests/test_sdd_eval.py"]
        count = subprocess.run([exe, "-c", "import sys, unittest; sys.path.insert(0, 'tests'); print(unittest."
                                "defaultTestLoader.loadTestsFromNames(%r).countTestCases())"
                                % [f[len("tests/"):-3] for f in files]], cwd=ROOT, stdin=subprocess.DEVNULL,
                               capture_output=True, text=True, env=env, timeout=120)
        total = int(count.stdout) if count.returncode == 0 and count.stdout.strip().isdigit() else None
        code, out, _, skipped = run("tests/run.py", "--tier", "slow", *files, cwd=ROOT)
        step("repository: every test of the two release files skipped in slow",
             code == 0 and total is not None and skipped == total > 0,
             f"code {code}, skipped {skipped} of {total}: {count.stderr.strip()[-200:]}")
        print(f"  skipped: {skipped} of {total} tests")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    if all(results):
        print("SUMMARY: all steps passed")
        return 0
    print("SUMMARY: %d of %d steps failed" % (results.count(False), len(results)))
    return 1


if __name__ == "__main__":
    sys.exit(main())
