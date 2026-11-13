"""Checks tests/run.py on a temporary tests/ folder holding a copy of the runner and small test files, and the real map."""
import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
import marks

from hypothesis import given, settings, strategies as st

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
_spec = importlib.util.spec_from_file_location("tests_run", HERE / "run.py")
run_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_mod)

PASS = "print('PASS-OUT')\n"
FAIL = "print('FAIL-OUT'); raise SystemExit(1)\n"
SLOW = "import time; time.sleep(2)\n"


class Tree:
    """A temporary root with tests/run.py and the given test files."""

    def __init__(self, case, files, amap=None):
        self.root = pathlib.Path(tempfile.mkdtemp())
        case.addCleanup(shutil.rmtree, self.root, True)
        (self.root / "tests").mkdir()
        for f in ("run.py", "marks.py"):
            shutil.copy(HERE / f, self.root / "tests" / f)
        for name, body in files.items():
            self.put(name, body)
        if amap is not None:
            (self.root / "tests" / "affected.json").write_text(json.dumps(amap))

    def put(self, name, body):
        (self.root / "tests" / name).write_text(body)

    @property
    def state(self):
        return self.root / "tests" / ".last-failed"

    def run(self, *args, stdin=subprocess.DEVNULL):
        p = subprocess.run([sys.executable, "tests/run.py", *args], cwd=self.root, stdin=stdin,
                           capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout, p.stderr

    @staticmethod
    def lines(out, word):
        return [m.group(1) for m in re.finditer(r"^%s (\S+) \(\d+\.\d s\)$" % word, out, re.M)]


class OneTestCommand(unittest.TestCase):
    """Requirement: One test command."""

    def test_a_green_suite(self):
        t = Tree(self, {"test_a.py": PASS, "test_b.py": PASS})
        code, out, _ = t.run()
        self.assertEqual(code, 0, out)
        self.assertEqual(sorted(t.lines(out, "ok")), ["tests/test_a.py", "tests/test_b.py"])
        self.assertNotIn("PASS-OUT", out)
        self.assertRegex(out, r"(?m)^files: 2, failed: 0, seconds: \d+\.\d$")

    @marks.slow
    def test_a_failing_file(self):
        t = Tree(self, {"test_a.py": PASS, "test_fail.py": FAIL, "test_slow.py": SLOW})
        code, out, _ = t.run()
        self.assertEqual(code, 1, out)
        self.assertEqual(t.lines(out, "FAIL"), ["tests/test_fail.py"])
        self.assertLess(out.index("FAIL-OUT"), out.index("FAIL tests/test_fail.py"))
        self.assertEqual(sorted(t.lines(out, "ok")), ["tests/test_a.py", "tests/test_slow.py"])
        self.assertNotIn("PASS-OUT", out)
        self.assertRegex(out, r"(?m)^files: 3, failed: 1, seconds: ")

    def test_a_fail_line_starts_its_own_line(self):
        t = Tree(self, {"test_nl.py": "import sys; sys.stdout.write('partial'); raise SystemExit(1)\n"})
        code, out, _ = t.run()
        self.assertEqual((code, t.lines(out, "FAIL")), (1, ["tests/test_nl.py"]), out)

    @marks.slow
    def test_files_run_in_parallel_up_to_jobs(self):
        t = Tree(self, {"test_s1.py": SLOW, "test_s2.py": SLOW})
        start = time.monotonic()
        self.assertEqual(t.run("--jobs", "2")[0], 0)
        self.assertLess(time.monotonic() - start, 3.6)  # two 2 s files side by side, with room for a loaded machine
        start = time.monotonic()
        self.assertEqual(t.run("--jobs", "1")[0], 0)
        self.assertGreaterEqual(time.monotonic() - start, 4.0)

    def test_stdin_is_closed(self):
        t = Tree(self, {"test_in.py": "import sys; assert sys.stdin.read() == ''\n"})
        r, w = os.pipe()  # the write end stays open: a file that inherits the pipe would wait forever
        self.addCleanup(os.close, w)
        try:
            code, out, _ = t.run(stdin=r)
        finally:
            os.close(r)
        self.assertEqual(code, 0, out)

    def test_bad_jobs(self):
        t = Tree(self, {"test_a.py": PASS})
        for bad in ("0", "-1", "x", "５", " 2"):
            code, out, err = t.run("--jobs", bad)
            self.assertEqual((code, t.lines(out, "ok")), (2, []), bad)


class NamedFiles(unittest.TestCase):
    """Requirement: Named files."""

    def test_the_oracle_run_of_sdd_eval(self):
        t = Tree(self, {"test_cli.py": PASS, "test_init.py": FAIL, "test_other.py": PASS})
        code, out, _ = t.run("tests/test_cli.py", "tests/test_init.py")
        self.assertEqual(code, 1, out)
        self.assertEqual(t.lines(out, "ok") + t.lines(out, "FAIL"), ["tests/test_cli.py", "tests/test_init.py"])
        self.assertIn("files: 2, failed: 1", out)

    def test_a_name_twice_runs_once(self):
        t = Tree(self, {"test_cli.py": PASS})
        code, out, _ = t.run("tests/test_cli.py", "tests/test_cli.py")
        self.assertEqual((code, t.lines(out, "ok")), (0, ["tests/test_cli.py"]))

    def test_an_unknown_name(self):
        t = Tree(self, {"test_cli.py": PASS, "helper.py": PASS})
        for name in ("tests/test_missing.py", "tests/helper.py", "tests/run.py"):
            code, out, err = t.run("tests/test_cli.py", name)
            self.assertEqual(code, 2, name)
            self.assertIn(name, err)
            self.assertEqual(t.lines(out, "ok"), [], name)
        self.assertFalse(t.state.exists())

    def test_two_selectors(self):
        t = Tree(self, {"test_cli.py": PASS}, {"always": [], "map": {}})
        for args in (["tests/test_cli.py", "--failed"], ["--failed", "--affected", "x"],
                     ["tests/test_cli.py", "--affected", "x"]):
            code, out, err = t.run(*args)
            self.assertEqual((code, t.lines(out, "ok")), (2, []), args)
            self.assertIn("exclude each other", err)


class FailedFirst(unittest.TestCase):
    """Requirement: Failed files first."""

    def test_a_rerun_after_red(self):
        t = Tree(self, {"test_a.py": PASS, "test_sdd_pr.py": FAIL, "test_b.py": PASS})
        self.assertEqual(t.run()[0], 1)
        self.assertEqual(t.state.read_text(), "tests/test_sdd_pr.py\n")
        code, out, _ = t.run("--jobs", "1")
        self.assertEqual(re.findall(r"^(?:ok|FAIL) (\S+)", out, re.M)[0], "tests/test_sdd_pr.py")
        code, out, _ = t.run("--failed")
        self.assertEqual((code, t.lines(out, "ok") + t.lines(out, "FAIL")), (1, ["tests/test_sdd_pr.py"]))

    def test_a_partial_run_keeps_other_failures(self):
        t = Tree(self, {"test_sdd_pr.py": FAIL, "test_cli.py": PASS})
        t.state.write_text("tests/test_sdd_pr.py\ntests/test_cli.py\n")
        self.assertEqual(t.run("tests/test_cli.py")[0], 0)
        self.assertEqual(t.state.read_text(), "tests/test_sdd_pr.py\n")

    def test_the_state_file_is_git_ignored(self):
        if not (ROOT / ".git").exists():
            self.skipTest("not a git checkout")
        p = subprocess.run(["git", "check-ignore", "-q", "tests/.last-failed"], cwd=ROOT, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0)

    def test_a_broken_state_file(self):
        t = Tree(self, {"test_a.py": PASS, "test_b.py": FAIL})
        for content in (b"", b"\xff\xfe\xfa\x80\n", b"tests/test_gone.py\ntests/test_a.py\ntests/test_a.py\n"):
            t.state.write_bytes(content)
            code, out, _ = t.run()
            self.assertEqual(code, 1)
            self.assertEqual(sorted(t.lines(out, "ok") + t.lines(out, "FAIL")), ["tests/test_a.py", "tests/test_b.py"])
            self.assertEqual(t.state.read_text(), "tests/test_b.py\n", content)


NAMES = st.sampled_from(["tests/test_%s.py" % c for c in "abcdefg"])


def check_state(plan, next_state):
    """The property of Failed files first over any suite, selection and state file content."""

    @settings(max_examples=300, deadline=None, database=None)
    @given(st.lists(NAMES, unique=True), st.data())
    def prop(files, data):
        selected = data.draw(st.lists(st.sampled_from(files))) if files else []
        lines = data.draw(st.lists(st.one_of(NAMES, st.sampled_from(["", "junk", "tests/test_gone.py"]))))
        state = data.draw(st.sampled_from([None, "\n".join(lines), "".join(x + "\n" for x in lines)]))
        failures_pool = list(dict.fromkeys(selected))
        failures = data.draw(st.lists(st.sampled_from(failures_pool), unique=True)) if failures_pool else []
        order = plan(selected, state)
        want = list(dict.fromkeys(selected))
        assert sorted(order) == sorted(want), (order, want)
        old = set((state or "").splitlines())
        k = sum(1 for f in want if f in old)
        assert all(f in old for f in order[:k]) and not any(f in old for f in order[k:]), order
        new = next_state(files, order, state, failures)
        assert len(new) == len(set(new)), new
        assert set(new) == set(failures) | ((old & set(files)) - set(want)), (new, failures, old)

    prop()


class FailedFirstProperty(unittest.TestCase):
    """Requirement: Failed files first, as a property; three mutants of the runner fail it."""

    def test_the_runner_holds(self):
        check_state(run_mod.plan, run_mod.next_state)

    @marks.slow
    def test_mutant_runs_a_file_named_twice_twice(self):
        def plan(selected, state):
            sel = list(dict.fromkeys(selected))
            lines = (state or "").splitlines()
            return [f for f in lines if f in sel] + [f for f in sel if f not in lines]
        with self.assertRaises(AssertionError):
            check_state(plan, run_mod.next_state)

    def test_mutant_drops_a_file_missing_from_the_state(self):
        def plan(selected, state):
            return [f for f in run_mod.plan(selected, state) if f in set((state or "").splitlines())]
        with self.assertRaises(AssertionError):
            check_state(plan, run_mod.next_state)

    @marks.slow
    def test_mutant_overwrites_the_state(self):
        with self.assertRaises(AssertionError):
            check_state(run_mod.plan, lambda files, selected, state, failures: list(failures))


AMAP = {"always": ["tests/test_always.py"],
        "map": {"src/a.py": ["tests/test_a.py"], "lib/": ["tests/test_b.py"], "lib/c.py": ["tests/test_c.py"]}}
FILES = {"test_a.py": PASS, "test_b.py": PASS, "test_c.py": PASS, "test_always.py": PASS, "test_free.py": PASS}


class AffectedFiles(unittest.TestCase):
    """Requirement: Affected files."""

    def ran(self, *paths):
        t = Tree(self, FILES, AMAP)
        code, out, _ = t.run("--affected", *paths)
        self.assertEqual(code, 0, out)
        return sorted(p[len("tests/test_"):-3] for p in t.lines(out, "ok"))

    def test_mapped_always_and_unnamed_files(self):
        self.assertEqual(self.ran("src/a.py"), ["a", "always", "free"])
        self.assertEqual(self.ran("lib/x.py"), ["always", "b", "free"])
        self.assertEqual(self.ran("lib/c.py", "src/a.py"), ["a", "always", "b", "c", "free"])
        self.assertEqual(self.ran("lib"), ["always", "b", "c", "free"])
        self.assertEqual(self.ran("lib/"), ["always", "b", "c", "free"])
        self.assertEqual(self.ran("src"), ["a", "always", "free"])

    def test_an_unknown_path(self):
        everything = ["a", "always", "b", "c", "free"]
        self.assertEqual(self.ran("tools/new.py"), everything)
        self.assertEqual(self.ran("src/a.py", "tools/new.py"), everything)
        self.assertEqual(self.ran("../outside.py"), everything)

    def test_a_broken_map_runs_everything(self):
        t = Tree(self, FILES)
        (t.root / "tests" / "affected.json").write_text("{broken")
        code, out, err = t.run("--affected", "src/a.py")
        self.assertEqual((code, len(t.lines(out, "ok"))), (0, 5))
        self.assertIn("the whole suite runs", err)

    def test_an_edit_of_the_plan_script(self):
        amap = json.loads((HERE / "affected.json").read_text(encoding="utf-8"))
        files = run_mod.suite()
        got = set(run_mod.affected(["global/sdd_dispatch_plan.py"], files, amap))
        self.assertTrue({"tests/test_sdd_dispatch_plan.py", "tests/test_sdd_eval.py"} <= got, got)
        self.assertTrue(set(amap["always"]) <= got)
        named = set(amap["always"]) | {t for v in amap["map"].values() for t in v}
        self.assertTrue({f for f in files if f not in named} <= got)
        self.assertFalse({"tests/test_sdd_pr.py", "tests/test_sdd_worktree.py", "tests/test_work_hooks.py"} & got, got)

    def test_a_stale_map(self):
        amap = json.loads((HERE / "affected.json").read_text(encoding="utf-8"))
        stale = [k for k in amap["map"] if not ((ROOT / k).is_dir() if k.endswith("/") else (ROOT / k).is_file())]
        tests = set(run_mod.suite())
        values = set(amap["always"]) | {t for v in amap["map"].values() for t in v}
        stale += sorted(v for v in values if v not in tests)
        self.assertEqual(stale, [])
        importers = {f for f in tests if re.search(r"(?m)^import marks$", (ROOT / f).read_text(encoding="utf-8"))}
        self.assertEqual(set(amap["map"]["tests/marks.py"]) - {"tests/test_runner.py"}, importers - {"tests/test_runner.py"})

MARKED = """import unittest
import marks


class T(unittest.TestCase):
    def test_plain(self):
        pass

    @marks.slow
    def test_slow(self):
        self.fail("SLOW-RAN")

    @marks.release
    def test_release(self):
        self.fail("RELEASE-RAN")


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
DIRECT = """import os
import sys
import unittest


class T(unittest.TestCase):
    def test_a_direct_run(self):
        here = os.path.dirname(os.path.abspath(__file__))
        assert __name__ == "__main__" and sys.argv[0] == __file__ and os.path.isabs(__file__), (sys.argv, __file__)
        assert sys.path[0] == here, sys.path[0]


if __name__ == "__main__":
    unittest.main()
"""


def no_tier():
    return {k: v for k, v in os.environ.items() if k != "SOLO_SDD_TESTS"}


def skipped_line(out):
    lines = out.splitlines()
    i = next(i for i, ln in enumerate(lines) if ln.startswith("files: "))
    return lines[i + 1]


class TestMarks(unittest.TestCase):
    """Requirement: Test marks."""

    def direct(self, tier, name="test_m.py", body=MARKED):
        t = Tree(self, {name: body})
        env = no_tier() if tier is None else dict(os.environ, SOLO_SDD_TESTS=tier)
        p = subprocess.run([sys.executable, "tests/" + name, "-v"], cwd=t.root, env=env, stdin=subprocess.DEVNULL,
                           capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout + p.stderr

    def test_a_release_test_in_a_round(self):
        code, out = self.direct("slow")
        self.assertNotIn("RELEASE-RAN", out)
        self.assertRegex(out, r"test_release .*skipped '[^']*release[^']*'")
        self.assertIn("SLOW-RAN", out)

    def test_a_direct_run(self):
        code, out = self.direct(None)
        self.assertEqual(code, 1, out)
        self.assertIn("SLOW-RAN", out)
        self.assertIn("RELEASE-RAN", out)
        self.assertNotIn("skipped", out)

    def test_a_typo_in_the_tier(self):
        code, out = self.direct("slwo")
        self.assertNotEqual(code, 0)
        for w in ("slwo", "fast", "slow", "release"):
            self.assertIn(w, out)
        self.assertNotIn("Ran ", out)
        p = subprocess.run([sys.executable, "tests/test_cli.py"], cwd=ROOT, stdin=subprocess.DEVNULL, timeout=120,
                           env=dict(os.environ, SOLO_SDD_TESTS="slwo"), capture_output=True, text=True)
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("slwo", p.stderr)
        self.assertNotIn("Ran ", p.stderr)


class Tiers(unittest.TestCase):
    """Requirement: Tiers in the runner."""

    def test_the_fast_tier(self):
        t = Tree(self, {"test_m.py": MARKED, "test_d.py": DIRECT})
        code, out, _ = t.run("--tier", "fast")
        self.assertEqual(code, 0, out)
        self.assertEqual(skipped_line(out), "skipped: 2")

    def test_the_slow_and_release_tiers(self):
        t = Tree(self, {"test_m.py": MARKED})
        for args, ran, skipped in ((["--tier", "slow"], ["SLOW-RAN"], 1), ([], ["SLOW-RAN"], 1),
                                   (["--tier", "release"], ["SLOW-RAN", "RELEASE-RAN"], 0)):
            code, out, _ = t.run(*args)
            self.assertEqual(code, 1, (args, out))
            got = [w for w in ("SLOW-RAN", "RELEASE-RAN") if w in out]
            self.assertEqual((got, skipped_line(out)), (ran, "skipped: %d" % skipped), args)

    @marks.slow
    def test_a_slow_unmarked_test(self):
        t = Tree(self, {"test_sleep.py": SLEEPER, "test_m.py": MARKED})
        code, out, _ = t.run("--tier", "fast")
        self.assertEqual(code, 1, out)
        self.assertRegex(out, r"(?m)^T\.test_sleep took [3-9]\.\d s, over the 2 s of the fast tier")
        self.assertEqual(t.lines(out, "FAIL"), ["tests/test_sleep.py"])
        self.assertEqual(t.lines(out, "ok"), ["tests/test_m.py"])
        code, out, _ = t.run("--tier", "slow", "tests/test_sleep.py")
        self.assertEqual(code, 0, out)

    def test_affected_files(self):
        t = Tree(self, {"test_a.py": MARKED, "test_b.py": PASS}, {"always": [], "map": {"src/a.py": ["tests/test_a.py"],
                                                                                         "src/b.py": ["tests/test_b.py"]}})
        code, out, _ = t.run("--affected", "src/a.py")
        self.assertEqual((code, t.lines(out, "FAIL")), (1, ["tests/test_a.py"]), out)
        self.assertIn("SLOW-RAN", out)
        self.assertNotIn("RELEASE-RAN", out)
        self.assertEqual(skipped_line(out), "skipped: 1")

    def test_a_case_run_inside_a_test(self):
        body = ("import unittest\n\n\nclass T(unittest.TestCase):\n    def test_outer(self):\n"
                "        inner = type('Inner', (unittest.TestCase,), {'test_x': unittest.skip('inner')(lambda s: None)})\n"
                "        unittest.defaultTestLoader.loadTestsFromTestCase(inner).run(unittest.TestResult())\n\n\n"
                "if __name__ == '__main__':\n    unittest.main()\n")
        t = Tree(self, {"test_n.py": body})
        code, out, _ = t.run("--tier", "fast")
        self.assertEqual((code, skipped_line(out)), (0, "skipped: 0"), out)

    @marks.slow
    def test_a_file_without_unittest_tests(self):
        t = Tree(self, {"test_plain.py": "import time; time.sleep(2.5)\n"})
        for tier in ("fast", "slow", "release"):
            code, out, _ = t.run("--tier", tier)
            self.assertEqual(code, 0, (tier, out))
            self.assertRegex(out, r"(?m)^ok tests/test_plain\.py \([2-9]\.\d s\)$")

    def test_named_files_and_a_tier(self):
        t = Tree(self, {"test_m.py": MARKED, "test_b.py": PASS, "test_d.py": DIRECT})
        code, out, _ = t.run("--jobs", "2", "--tier", "fast", "tests/test_m.py", "tests/test_d.py")
        self.assertEqual((code, sorted(t.lines(out, "ok"))), (0, ["tests/test_d.py", "tests/test_m.py"]), out)

    def test_a_bad_tier(self):
        t = Tree(self, {"test_a.py": PASS})
        for bad in ("slwo", "", "Fast"):
            code, out, err = t.run("--tier", bad)
            self.assertEqual((code, t.lines(out, "ok")), (2, []), bad)


TIERS = ("fast", "slow", "release")


def check_marks(mark):
    """The property of Test marks over any marks of the tests of one case and any tier or none."""

    @settings(max_examples=300, deadline=None, database=None)
    @given(st.lists(st.sampled_from([None, "slow", "release"]), max_size=6),
           st.sampled_from([None, "fast", "slow", "release"]))
    def prop(assigned, tier):
        body = {}
        for i, m in enumerate(assigned):
            def test(self):
                pass
            body["test_%d" % i] = test if m is None else mark(m, tier)(test)
        res = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromTestCase(type("Case", (unittest.TestCase,), body)).run(res)
        skipped = {t._testMethodName for t, _ in res.skipped}
        want = {"test_%d" % i for i, m in enumerate(assigned)
                if m is not None and tier is not None and TIERS.index(m) > TIERS.index(tier)}
        assert skipped == want and res.testsRun == len(assigned), (assigned, tier, skipped)

    prop()


def load_marks():
    spec = importlib.util.spec_from_file_location("tests_marks", HERE / "marks.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestMarksProperty(unittest.TestCase):
    """Requirement: Test marks, as a property; two mutants of the marks fail it."""

    def test_the_marks_hold(self):
        check_marks(load_marks().mark)

    def test_mutant_runs_release_tests_in_slow(self):
        mark = load_marks().mark
        with self.assertRaises(AssertionError):
            check_marks(lambda m, tier: mark("slow" if m == "release" else m, tier))

    def test_mutant_skips_marked_tests_without_the_variable(self):
        mark = load_marks().mark
        with self.assertRaises(AssertionError):
            check_marks(lambda m, tier: mark(m, tier or "fast"))


RELEASE = {"test_sdd_eval": None, "test_publish_first": None, "test_cli": "EntryPoint.test_wheel",
           "test_npm_package": "Contents"}
PROBE = """import json, sys, unittest
names = json.loads(sys.argv[1])
out = {}
for mod, part in names.items():
    for t in unittest.defaultTestLoader.loadTestsFromName(mod if part is None else mod + "." + part):
        for case in (t if isinstance(t, unittest.TestSuite) else [t]):
            m = getattr(case, case._testMethodName)
            why = [getattr(o, "__unittest_skip_why__", "") for o in (type(case), m) if getattr(o, "__unittest_skip__", 0)]
            out[case.id()] = any("SOLO_SDD_TESTS=" in w for w in why)
print(json.dumps(out))
"""


def tests_row():
    cmds = (ROOT / "AGENTS.md").read_text(encoding="utf-8").split("## Commands", 1)[1].split("\n## ", 1)[0]
    row = next(ln for ln in cmds.splitlines() if ln.startswith("| Tests |"))
    return re.findall(r"`([^`]*)`", row)


class ReleaseSet(unittest.TestCase):
    """Requirement: Release set."""

    def skips(self, tier):
        env = no_tier() if tier is None else dict(os.environ, SOLO_SDD_TESTS=tier)
        p = subprocess.run([sys.executable, "-c", PROBE, json.dumps(RELEASE)], cwd=HERE, env=env, timeout=120,
                           stdin=subprocess.DEVNULL, capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return json.loads(p.stdout)

    def test_the_release_set(self):
        slow = self.skips("slow")
        self.assertTrue(any(k.startswith("test_sdd_eval.") for k in slow) and any(
            k.startswith("test_publish_first.") for k in slow), slow)
        self.assertIn("test_cli.EntryPoint.test_wheel", slow)
        self.assertIn("test_npm_package.Contents.test_pack", slow)
        self.assertEqual([k for k, v in slow.items() if not v], [])
        self.assertEqual([k for k, v in self.skips("release").items() if v], [])
        self.assertEqual([k for k, v in self.skips(None).items() if v], [])

    def test_a_round(self):
        spans = tests_row()
        fast = [c for c in spans if "--tier fast" in c]
        aff = [c for c in spans if "--affected" in c]
        self.assertTrue(fast and aff, spans)
        for c in fast + aff:
            self.assertNotRegex(c, r"--tier (slow|release)", c)
        self.assertTrue(any("--tier release" in c for c in spans[1:]), spans)

    def test_the_command_scripts_read(self):
        spec = importlib.util.spec_from_file_location("sdd_eval", ROOT / "global/sdd_eval.py")
        sdd_eval = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sdd_eval)
        cmd = sdd_eval.test_command(ROOT)
        self.assertEqual(cmd, tests_row()[0])
        self.assertTrue(cmd.startswith("python3 tests/run.py ") and cmd.endswith(" --tier slow"), cmd)


if __name__ == "__main__":
    unittest.main()
