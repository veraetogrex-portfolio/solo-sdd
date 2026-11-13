"""scripts/pre-push-guard.sh as the pre-push hook of a temporary repository pushing to a bare one."""
import os
import pathlib
import shutil
import subprocess
import unittest
import marks
import shared_repo

from hypothesis import example, given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]
# GUARD_SCRIPT is needed only to check mutations of the script
SCRIPT = os.environ.get("GUARD_SCRIPT") or str(REPO / "scripts" / "pre-push-guard.sh")
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
DELETABLE = 3
OLD = ("history-local", "history-private", "cut-local", "cut-private", "merge-private")
KINDS = OLD + ("main", "new", "delete", "blob")


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=str(cwd), env=ENV, capture_output=True, text=True, check=check,
                          stdin=subprocess.DEVNULL)


def build(folder):
    """work: history-local, history-private and main, three unrelated roots of two commits each; remote.git holds
    main and the branches d0..d2 a push may delete."""
    work = folder / "work"
    git(folder, "init", "-q", "-b", "main", str(work))
    for branch in ("history-local", "history-private", "main"):
        git(work, "checkout", "-q", "--orphan", branch)
        for i in range(2):
            (work / "f").write_text("%s %d\n" % (branch, i))
            git(work, "add", "f")
            git(work, "commit", "-q", "-m", "%s %d" % (branch, i))
    git(folder, "init", "-q", "-b", "main", "--bare", str(folder / "remote.git"))
    git(work, "remote", "add", "origin", str(folder / "remote.git"))
    git(work, "push", "-q", "origin", "main", *["main:refs/heads/d%d" % i for i in range(DELETABLE)])


class OldHistoryPushGuard(unittest.TestCase):
    """Requirement: Old history push guard."""

    def repo(self):
        folder, _ = shared_repo.template("pre-push-guard", build)
        copy = shared_repo.copy(folder)
        self.addCleanup(shutil.rmtree, copy, True)
        work = copy / "work"
        hook = pathlib.Path(git(work, "rev-parse", "--absolute-git-dir").stdout.strip(), "hooks", "pre-push")
        hook.parent.mkdir(exist_ok=True)
        shutil.copy(SCRIPT, hook)
        hook.chmod(0o755)
        return work, copy / "remote.git"

    def source(self, work, kind, n):
        """The object a pushed ref of this kind points to; a new commit on top for cut-*, new and merge-*."""
        rev = lambda r: git(work, "rev-parse", r).stdout.strip()
        tree = rev("main^{tree}")
        if kind in ("history-local", "history-private", "main"):
            return rev("%s~%d" % (kind, n % 2))
        if kind in ("cut-local", "cut-private"):
            parent = "history-%s~%d" % (kind[4:], n % 2)
            return git(work, "commit-tree", tree, "-p", parent, "-m", "cut").stdout.strip()
        if kind == "new":
            return git(work, "commit-tree", tree, "-p", "main", "-m", "new %d" % n).stdout.strip()
        if kind == "merge-private":
            return git(work, "commit-tree", tree, "-p", "main", "-p", "history-private", "-m", "merge").stdout.strip()
        return subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=str(work), env=ENV, input="blob %d\n" % n,
                              capture_output=True, text=True, check=True).stdout.strip()

    refs = st.lists(st.tuples(st.sampled_from(KINDS), st.integers(min_value=0, max_value=1)), min_size=1, max_size=4)

    @marks.slow
    @settings(max_examples=15, deadline=None)
    @given(pushed=refs)
    @example(pushed=[("delete", 0)])
    @example(pushed=[("main", 0)])
    @example(pushed=[("new", 0), ("history-private", 1), ("new", 1)])
    @example(pushed=[("new", 0), ("blob", 0)])
    def test_old_history_push_guard(self, pushed):
        work, remote = self.repo()
        specs, expected = [], {}
        refs = lambda: dict(line.split()[::-1] for line in git(remote, "show-ref").stdout.splitlines())
        before = refs()
        deletions = 0
        for i, (kind, n) in enumerate(pushed):
            if kind == "delete":
                if deletions == DELETABLE:
                    continue
                specs.append(":refs/heads/d%d" % deletions)
                expected["refs/heads/d%d" % deletions] = None
                deletions += 1
                continue
            sha = self.source(work, kind, n)
            name = ("refs/tags/r%d" if kind == "blob" else "refs/heads/r%d") % i
            specs.append("%s:%s" % (sha, name))
            expected[name] = sha
        p = git(work, "push", "origin", *specs, check=False)
        refuse = any(kind in OLD or kind == "blob" for kind, _ in pushed)
        if refuse:
            self.assertNotEqual(p.returncode, 0, p.stderr)
            self.assertIn("pre-push: refused for ", p.stderr)
            self.assertEqual(refs(), before)
        else:
            self.assertEqual(p.returncode, 0, p.stderr)
            after = dict(before, **expected)
            self.assertEqual(refs(), {k: v for k, v in after.items() if v is not None})


if __name__ == "__main__":
    unittest.main()
