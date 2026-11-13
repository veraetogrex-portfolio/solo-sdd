"""Checks the helpers of change slow-tests-cost: tests/shared_repo.py (Shared repository fixtures), the example counts
of tests/marks.py (Example budgets) and the counter of its stand tests/stands/slow-tests-cost.py (No check lost)."""
import importlib.util
import os
import pathlib
import shutil
import subprocess
import sys
import itertools
import tempfile
import unittest
import marks
import shared_repo

from hypothesis import Phase, given, settings, strategies as st

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("slow_tests_cost", HERE / "stands/slow-tests-cost.py")
stand = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(stand)


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout.strip()


def build(root):
    """A bare remote, a main repository with origin pointing at it and a linked worktree of branch feat."""
    root = pathlib.Path(root)
    git(root, "init", "-q", "--bare", "remote.git")
    git(root, "init", "-q", "-b", "main", "main")
    (root / "main/README.md").write_text("r\n")
    git(root / "main", "add", "-A")
    git(root / "main", "commit", "-qm", "init")
    git(root / "main", "remote", "add", "origin", str(root / "remote.git"))
    git(root / "main", "push", "-q", "origin", "main")
    git(root / "main", "worktree", "add", "-q", "-b", "feat", str(root / "wt"))
    return git(root / "main", "rev-parse", "HEAD")


def state(root):
    """What a test sees of a fixture folder: HEADs, refs, status, local config and remote refs, the folder's own path
    written as <root>."""
    root = pathlib.Path(root)

    def g(repo, *args):
        return git(root / repo, *args).replace(str(root), "<root>")
    return {"main": (g("main", "rev-parse", "HEAD"), g("main", "for-each-ref"),
                     g("main", "status", "--porcelain", "--untracked-files=all"), g("main", "config", "--local", "-l")),
            "wt": (g("wt", "rev-parse", "HEAD"), g("wt", "status", "--porcelain", "--untracked-files=all"),
                   g("wt", "rev-parse", "--git-dir")),
            "remote": g("remote.git", "for-each-ref")}


EDITS = ["commit", "untracked", "branch", "push", "config", "wt-commit"]
SERIAL = itertools.count()  # names no earlier edit used, also when a mutant lets edits reach the template


def edit(root, n, op):
    n = "%d-%d" % (n, next(SERIAL))
    main, wt = pathlib.Path(root, "main"), pathlib.Path(root, "wt")
    if op == "commit":
        (main / ("c%s.txt" % n)).write_text("x\n")
        git(main, "add", "-A")
        git(main, "commit", "-qm", "c%s" % n)
    elif op == "untracked":
        (main / ("u%s.txt" % n)).write_text("u\n")
    elif op == "branch":
        git(main, "branch", "b%s" % n)
    elif op == "push":
        git(main, "push", "-q", "origin", "HEAD:refs/heads/p%s" % n)
    elif op == "config":
        git(main, "config", "test.edit%s" % n, "yes")
    else:
        (wt / ("w%s.txt" % n)).write_text("w\n")
        git(wt, "add", "-A")
        git(wt, "commit", "-qm", "w%s" % n)


def check_copies(copy, key, phases=tuple(Phase)):
    """Requirement Shared repository fixtures as a property over any edits of one copy, with this copy function."""
    folder, _ = shared_repo.template(key, build)
    want = state(folder)

    @settings(max_examples=marks.examples(50), deadline=None, database=None, report_multiple_bugs=False,
              phases=phases)
    @given(st.lists(st.sampled_from(EDITS), max_size=5))
    def prop(ops):
        first = copy(folder)
        try:
            for n, op in enumerate(ops):
                edit(first, n, op)
            fresh = copy(folder)
            try:
                assert state(fresh) == want, ops
            finally:
                if fresh != folder:
                    shutil.rmtree(fresh, ignore_errors=True)
        finally:
            if first != folder:
                shutil.rmtree(first, ignore_errors=True)
    prop()


NO_SHRINK = (Phase.explicit, Phase.generate)  # a mutant only has to fail, not to fail minimally


def copy_keeping_paths(src):
    """Mutant: a plain copy that leaves the template's paths (origin URL, worktree gitdir) in place."""
    dst = pathlib.Path(tempfile.mkdtemp(prefix="shared-copy-")).resolve()
    shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)
    return dst


class SharedRepository(unittest.TestCase):
    """Requirement: Shared repository fixtures."""

    def fresh(self):
        folder, head = shared_repo.template("scenarios", build)
        c = shared_repo.copy(folder)
        self.addCleanup(shutil.rmtree, c, True)
        return folder, c, head

    def test_two_tests_of_one_class(self):
        folder, first, head = self.fresh()
        edit(first, 1, "commit")
        edit(first, 2, "untracked")
        self.assertIn("?? u2-", git(first / "main", "status", "--porcelain"))
        git(first / "main", "push", "-q", "origin", "main")
        self.assertIn("c1", git(first / "remote.git", "log", "--format=%s", "main"))
        _, second, _ = self.fresh()
        self.assertEqual(git(second / "main", "rev-parse", "HEAD"), head)
        self.assertEqual(git(second / "main", "status", "--porcelain"), "")
        self.assertEqual(git(second / "remote.git", "rev-parse", "main"), head)
        self.assertEqual(git(folder / "remote.git", "rev-parse", "main"), head)

    def test_a_fixture_with_a_remote_and_a_worktree(self):
        folder, c, _ = self.fresh()
        url = git(c / "main", "remote", "get-url", "origin")
        self.assertEqual(url, str(c / "remote.git"))
        gitdir = (c / "main/.git/worktrees/wt/gitdir").read_text().strip()
        self.assertEqual(gitdir, str(c / "wt/.git"))
        self.assertEqual((c / "wt/.git").read_text().strip(), "gitdir: %s" % (c / "main/.git/worktrees/wt"))
        self.assertEqual(git(c / "wt", "rev-parse", "--abbrev-ref", "HEAD"), "feat")
        self.assertEqual(git(c / "wt", "status", "--porcelain"), "")
        self.assertIn(str(c / "wt"), git(c / "main", "worktree", "list"))
        self.assertNotIn(str(folder), git(c / "main", "worktree", "list"))

    def test_a_symlink_into_the_template_points_into_the_copy(self):
        folder, _ = shared_repo.template("link", lambda root: os.symlink(str(root / "t"), str(root / "l")))
        c = shared_repo.copy(folder)
        self.addCleanup(shutil.rmtree, c, True)
        self.assertEqual(os.readlink(str(c / "l")), str(c / "t"))

    def test_a_part_of_a_template(self):
        """A copy of one folder of a template whose files name another one (a clone's reflog names its source)."""
        def clone(root):
            build(root)
            git(root, "clone", "-q", str(root / "remote.git"), str(root / "c"))
        folder, _ = shared_repo.template("part", clone)
        dst = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, dst, True)
        shared_repo.copy(folder / "c", dst / "c", {folder / "remote.git": dst / "remote.git"})
        logs = (dst / "c/.git/logs/HEAD").read_text()
        self.assertIn(str(dst / "remote.git"), logs)
        self.assertNotIn(str(folder), logs + git(dst / "c", "remote", "get-url", "origin"))

    def test_built_once_per_key(self):
        calls = []
        a = shared_repo.template("once", lambda root: calls.append(root) or len(calls))
        b = shared_repo.template("once", lambda root: calls.append(root) or len(calls))
        self.assertEqual((a, len(calls)), (b, 1))


@marks.slow
class SharedRepositoryProperty(unittest.TestCase):
    """Requirement Shared repository fixtures as a property; the two mutants fail it."""

    def test_a_fresh_copy_equals_the_template(self):
        check_copies(shared_repo.copy, "property")

    def test_mutant_hands_out_the_template(self):
        with self.assertRaises(AssertionError):
            check_copies(lambda src: src, "mutant-template", NO_SHRINK)

    def test_mutant_keeps_the_origin_url(self):
        with self.assertRaises(AssertionError):
            check_copies(copy_keeping_paths, "mutant-paths", NO_SHRINK)


class ExampleBudgets(unittest.TestCase):
    """Requirement: Example budgets."""

    def test_each_tier(self):
        for tier, want in (("fast", 20), ("slow", 20), ("release", 120), (None, 20)):
            self.assertEqual(marks.examples(120, tier=tier), want, tier)
            self.assertEqual(marks.examples(120, 30, tier=tier), 120 if tier == "release" else 30, tier)
            self.assertEqual(marks.examples(120, 5, tier=tier), 120 if tier == "release" else 20, tier)
            self.assertEqual(marks.examples(15, tier=tier), 15, tier)

    def counts(self, tier):
        """The example counts test_sdd_dispatch_plan's test_abandoned_claims_property gets on import in the tier."""
        env = {k: v for k, v in os.environ.items() if k != "SOLO_SDD_TESTS"}
        if tier:
            env["SOLO_SDD_TESTS"] = tier
        code = ("import test_sdd_dispatch_plan as t\n"
                "print(t.Property.test_abandoned_claims_property._hypothesis_internal_use_settings.max_examples)")
        r = subprocess.run([sys.executable, "-c", code], cwd=HERE, env=env, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return int(r.stdout.split()[-1])

    def test_a_round_and_a_direct_run(self):
        self.assertEqual(self.counts("slow"), 20)
        self.assertEqual(self.counts("release"), 120)
        self.assertEqual(self.counts(None), 20)


class NoCheckLost(unittest.TestCase):
    """Requirement: No check lost. The stand's counter on a real test file and on a mutant of it."""

    def test_a_deleted_assert_in_is_reported(self):
        src = (HERE / "test_sdd_dispatch.py").read_text(encoding="utf-8")
        tests, asserts = stand.counts(src)
        self.assertGreater(tests, 0)
        mutant = src.replace("        self.assertIn(\"LIVE: timeout after 1 s\", r.stdout)\n", "", 1)
        self.assertNotEqual(mutant, src)
        self.assertEqual(stand.counts(mutant), (tests, asserts - 1))
        base = {"tests/test_sdd_dispatch.py": stand.counts(src), "tests/test_x.py": (1, 1)}
        self.assertEqual(stand.lost(base, dict(base)), {})
        got = stand.lost(base, {"tests/test_sdd_dispatch.py": stand.counts(mutant), "tests/test_x.py": (1, 1)})
        self.assertEqual(list(got), ["tests/test_sdd_dispatch.py"])

    def test_what_counts(self):
        src = ("class T:\n    def test_a(self):\n        assert 1\n        self.assertEqual(1, 1)\n"
               "        self.assertTrue(x.assertIn)\n        other.assertIn(1, 2)\n    def helper(self):\n"
               "        self.assertIn(1, [1])\n    async def test_b(self):\n        pass\n")
        self.assertEqual(stand.counts(src), (2, 4))

    def test_touched_classes(self):
        """The stand times the classes the diff reaches: through a base class and a helper they name."""
        base = ("import os\n\ndef build(r):\n    os.mkdir(r)\n\nclass Fix:\n    def setUp(self):\n        build(1)\n\n"
                "class A(Fix):\n    def test_a(self):\n        pass\n\nclass B:\n    def test_b(self):\n        pass\n")
        branch = base.replace("os.mkdir(r)", "os.makedirs(r)")
        self.assertEqual(stand.touched(base, branch) & {"A", "B", "Fix"}, {"A", "Fix"})
        self.assertEqual(stand.touched(base, base), set())
        self.assertIn("B", stand.touched(base, base.replace("pass\n", "assert 1\n")))


if __name__ == "__main__":
    unittest.main()
