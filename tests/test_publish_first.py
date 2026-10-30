"""scripts/publish-first.sh на временном репозитории: поддельный gh, bare-репозиторий вместо GitHub."""
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from hypothesis import given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]
# PUBLISH_SCRIPT нужен только для проверки мутаций скрипта
SCRIPT = os.environ.get("PUBLISH_SCRIPT") or str(REPO / "scripts" / "publish-first.sh")
OWNER = "veraetogrex-portfolio"

BLOCK = [
    "docs/debug-profile.md",
    "docs/process-safety-verification.md",
    "docs/waiting.md",
    "global/claude-gui.py",
    "global/claude-process-safety-settings.json",
    "global/claude-safe.py",
    "skills/model-council/",
    "tests/probe_claude_development.py",
    "tests/probe_claude_process_safety.py",
    "tests/test_claude_gui.py",
    "tests/test_claude_safe.py",
]
IGNORE = "__pycache__/\n.env\n\n# под одного владельца, к разработке solo-sdd не относится\n" + "\n".join(BLOCK) + "\n"

FAKE_GH = r"""#!/bin/bash
case "$1 $2" in
  "api user") echo "${GH_LOGIN:-veraetogrex-portfolio}" ;;
  "repo view")
    case "${GH_VIEW:-not-found}" in
      exists) echo "name: solo-sdd" ;;
      network-error) echo "error connecting to api.github.com" >&2; exit 1 ;;
      *) echo "GraphQL: Could not resolve to a Repository with the name '$3'. (repository)" >&2; exit 1 ;;
    esac ;;
  "repo create")
    echo "$*" >> "$GH_LOG"
    [ -z "$GH_CREATE_FAIL" ] || exit 1
    git init --bare -q "$GH_BARE" && git remote add origin "$GH_BARE" ;;
  "repo edit") echo "$*" >> "$GH_LOG" ;;
  *) echo "неожиданный вызов gh: $*" >&2; exit 3 ;;
esac
"""


def run(cwd, *cmd, env=None, check=True):
    p = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and p.returncode:
        raise AssertionError(f"{cmd}: {p.returncode}\n{p.stdout}\n{p.stderr}")
    return p


class Stand:
    """Репозиторий-фикстура + поддельный gh + путь bare-remote."""

    def __init__(self, cleanup, extra_commits=0, env=None):
        self.tmp = tempfile.mkdtemp()
        cleanup(shutil.rmtree, self.tmp, True)
        self.root = os.path.join(self.tmp, "repo")
        self.bare = os.path.join(self.tmp, "bare.git")
        self.log = os.path.join(self.tmp, "gh.log")
        os.mkdir(self.root)
        os.mkdir(os.path.join(self.tmp, "bin"))
        gh = os.path.join(self.tmp, "bin", "gh")
        pathlib.Path(gh).write_text(FAKE_GH)
        os.chmod(gh, 0o755)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(
            PATH=os.path.join(self.tmp, "bin") + os.pathsep + os.environ["PATH"],
            HOME=self.tmp, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1",
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com",
            GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.com",
            GH_BARE=self.bare, GH_LOG=self.log,
        )
        self.env.update(env or {})
        self.git("init", "-q", "-b", "main")
        self.put("README.md", "readme\n")
        self.put("LICENSE", "MIT\n")
        self.put(".gitignore", IGNORE)
        self.put("tests/test_public_tree.py", "import sys; sys.exit(0)\n")
        self.put("openspec/changes/a/proposal.md", "a\n")
        self.put("docs/waiting.md", "wait\n")
        self.git("add", "-f", "-A")
        self.git("commit", "-q", "-m", "first")
        for i in range(extra_commits):
            self.put("README.md", f"readme {i}\n")
            self.commit(f"more {i}")

    def git(self, *args, check=True):
        return run(self.root, "git", *args, env=self.env, check=check)

    def put(self, rel, text):
        p = pathlib.Path(self.root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)

    def commit(self, msg, *paths):
        self.git(*(["add", "-f", *paths] if paths else ["add", "-A"]))
        self.git("commit", "-q", "-m", msg)

    def script(self, *args, env=None):
        e = dict(self.env, **(env or {}))
        return run(self.root, "bash", SCRIPT, *args, env=e, check=False)

    def snapshot(self):
        cmds = [("branch",), ("tag",), ("remote",), ("status", "--porcelain"), ("rev-parse", "HEAD"),
                ("ls-files",), ("worktree", "list"), ("symbolic-ref", "HEAD")]
        snap = [self.git(*c, check=False).stdout for c in cmds]
        snap.append(pathlib.Path(self.root, ".gitignore").read_text())
        return snap

    def bare_refs(self):
        return run(self.bare, "git", "for-each-ref", "--format=%(refname) %(objectname)", env=self.env).stdout

    def publish(self, **kw):
        p = self.script("--go", **kw)
        assert p.returncode == 0, p.stdout + p.stderr
        return p


class Base(unittest.TestCase):
    def stand(self, **kw):
        return Stand(self.addCleanup, **kw)


class TestFirstPublicationWithoutHistory(Base):
    def test_unknown_argument_exit_2(self):
        self.assertEqual(self.stand().script("--bogus").returncode, 2)

    def test_dry_run_prints_plan_and_changes_nothing(self):
        s = self.stand()
        before = s.snapshot()
        p = s.script()
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("git push -u origin refs/heads/main:refs/heads/main refs/tags/v0.1.0:refs/tags/v0.1.0", p.stdout)
        self.assertIn("gh repo create veraetogrex-portfolio/solo-sdd --public", p.stdout)
        self.assertEqual(s.snapshot(), before)
        self.assertFalse(os.path.exists(s.log))

    def test_open_changes_and_change_branches_do_not_block(self):
        s = self.stand()
        s.put("openspec/changes/b/proposal.md", "b\n")
        s.commit("b")
        s.git("branch", "change/x")
        s.put("openspec/changes/a/CLAIM", "claude\n")
        s.put("docs/waiting.md", "changed\n")
        self.assertEqual(s.script().returncode, 0)
        p = s.script("--go")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("change/x", s.git("branch").stdout)
        self.assertTrue(os.path.exists(os.path.join(s.root, "openspec/changes/a/CLAIM")))
        self.assertEqual(pathlib.Path(s.root, "docs/waiting.md").read_text(), "changed\n")

    def test_publication(self):
        s = self.stand()
        s.git("branch", "change/x")
        old_head = s.git("rev-parse", "HEAD").stdout.strip()
        s.publish()
        refs = [l.split()[0] for l in s.bare_refs().splitlines()]
        self.assertEqual(sorted(refs), ["refs/heads/main", "refs/tags/v0.1.0"])
        self.assertEqual(run(s.bare, "git", "rev-list", "--count", "main", env=s.env).stdout.strip(), "1")
        self.assertEqual(run(s.bare, "git", "log", "-1", "--format=%s", "main", env=s.env).stdout.strip(), "solo-sdd 0.1.0")
        self.assertEqual(s.git("rev-parse", "history-local").stdout.strip(), old_head)
        diff = s.git("diff", "--name-only", "history-local", "main").stdout.split()
        self.assertEqual(sorted(diff), [".gitignore", "docs/waiting.md", "openspec/changes/a/proposal.md"])
        tree = s.git("ls-tree", "-r", "--name-only", "main").stdout.splitlines()
        for bad in ["docs/waiting.md", "tests/test_claude_safe.py"] + [t for t in tree if t.startswith("openspec/")]:
            self.assertNotIn(bad, tree)
        self.assertEqual(s.git("log", "main", "--", "openspec").stdout, "")
        for f in ("openspec/changes/a/proposal.md", "docs/waiting.md"):
            self.assertTrue(os.path.exists(os.path.join(s.root, f)), f)
            self.assertEqual(s.git("check-ignore", "-q", f, check=False).returncode, 0, f)
        self.assertEqual(s.git("status", "--porcelain").stdout, "")
        self.assertIn("change/x", s.git("branch").stdout)
        log = pathlib.Path(s.log).read_text()
        self.assertIn("--public", log)
        for t in ("openspec", "claude-code", "codex", "spec-driven-development"):
            self.assertIn(f"--add-topic {t}", log)

    def test_only_two_refs_pushed_with_extra_local_refs(self):
        s = self.stand()
        s.git("branch", "change/x")
        s.git("tag", "old-tag")
        s.publish()
        self.assertEqual(len(s.bare_refs().splitlines()), 2, s.bare_refs())

    # --- предусловия
    CASES = {
        "не main": (lambda s: s.git("checkout", "-q", "-b", "other"), None, "текущая ветка не main"),
        "history-local": (lambda s: s.git("branch", "history-local"), None, "history-local уже есть"),
        "тег": (lambda s: s.git("tag", "v0.1.0"), None, "v0.1.0 уже есть"),
        "origin": (lambda s: s.git("remote", "add", "origin", "/nonexistent"), None, "origin уже есть"),
        "worktree": (lambda s: s.git("worktree", "add", "-q", os.path.join(s.tmp, "wt"), "-b", "wt-b"), None, "worktree"),
        "грязный файл": (lambda s: s.put("README.md", "dirty\n"), None, "не чистая"),
        "test_public_tree": (lambda s: (s.put("tests/test_public_tree.py", "import sys; print('ПЛОХО'); sys.exit(1)\n"), s.commit("x")), None, "test_public_tree.py не прошёл"),
        "чужой login": (None, {"GH_LOGIN": "someone"}, "gh вошёл как 'someone'"),
        "repo exists": (None, {"GH_VIEW": "exists"}, "уже существует"),
        "gh network": (None, {"GH_VIEW": "network-error"}, "не удалось проверить"),
        "файл из блока": (lambda s: (s.put("global/claude-safe.py", "x\n"), s.commit("x", "global/claude-safe.py")), None, "global/claude-safe.py"),
        "короткий блок": (lambda s: (s.put(".gitignore", "a\n# под одного владельца, х\nb\nc\n"), s.commit("x")), None, "короче 10"),
    }

    def check_violation(self, mutate, env, text, extra=None):
        for args in ((), ("--go",)):
            with self.subTest(args=args):
                s = self.stand()
                if mutate:
                    mutate(s)
                if extra:
                    extra(s)
                before = s.snapshot()
                p = s.script(*args, env=env)
                self.assertEqual(p.returncode, 1, p.stdout + p.stderr)
                self.assertIn(text, p.stderr)
                self.assertEqual(s.snapshot(), before)
                self.assertFalse(os.path.exists(s.log))

    def test_each_precondition_alone_fails(self):
        for name, (mutate, env, text) in self.CASES.items():
            with self.subTest(case=name):
                self.check_violation(mutate, env, text)

    def test_two_violations_both_named(self):
        def both(s):
            s.git("checkout", "-q", "-b", "other")
            s.git("tag", "v0.1.0")
        self.check_violation(both, {"GH_VIEW": "exists"}, "текущая ветка не main")
        self.check_violation(both, {"GH_VIEW": "exists"}, "v0.1.0 уже есть")
        self.check_violation(both, {"GH_VIEW": "exists"}, "уже существует")

    # --- хук
    def published(self, **kw):
        s = self.stand(**kw)
        s.git("branch", "change/old")
        s.git("tag", "old-tag", "HEAD")
        s.publish()
        return s

    def assert_rejected(self, s, *refspecs):
        before = s.bare_refs()
        p = s.git("push", "origin", *refspecs, check=False)
        self.assertNotEqual(p.returncode, 0, refspecs)
        self.assertIn("pre-push: отказ", p.stderr)
        self.assertEqual(s.bare_refs(), before)

    def test_hook_rejects_old_history(self):
        s = self.published(extra_commits=3)
        old = s.git("rev-list", "--reverse", "history-local").stdout.split()
        self.assert_rejected(s, "history-local")
        self.assert_rejected(s, "history-local:refs/heads/x")
        self.assert_rejected(s, f"{old[1]}:refs/heads/x")
        self.assert_rejected(s, "change/old")
        self.assert_rejected(s, "refs/tags/old-tag")

    def test_hook_rejects_openspec_descendant_of_main(self):
        s = self.published()
        s.git("checkout", "-q", "-b", "bad")
        s.put("openspec/x", "x\n")
        s.commit("bad", "openspec/x")
        self.assert_rejected(s, "bad")

    def test_hook_rejects_tag_on_old_tree(self):
        """Тег на дерево минует проверки коммитов, а дерево несёт openspec/."""
        s = self.published()
        tree = s.git("rev-parse", "history-local^{tree}").stdout.strip()
        s.git("tag", "leak-tree", tree)
        self.assert_rejected(s, "refs/tags/leak-tree")

    def test_hook_allows_new_history_and_deletion(self):
        s = self.published()
        s.git("checkout", "-q", "-b", "good")
        s.put("README.md", "new\n")
        s.commit("good")
        p = s.git("push", "origin", "good", check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("refs/heads/good", s.bare_refs())
        p = s.git("push", "origin", ":refs/heads/good", check=False)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertNotIn("refs/heads/good", s.bare_refs())

    # --- существующий хук
    def old_hook(self, s, out):
        hook = pathlib.Path(s.root, ".git", "hooks", "pre-push")
        hook.write_text(f'#!/bin/sh\necho "$@" >> {out}\ncat | tee -a {out} > /dev/null\n'
                        f'grep -q refs/heads/blocked {out} && exit 1\nexit 0\n')
        hook.chmod(0o755)

    def test_existing_pre_push_kept_and_called_with_same_input(self):
        s = self.stand()
        out = os.path.join(s.tmp, "old-hook.log")
        self.old_hook(s, out)
        s.publish()
        saved = pathlib.Path(s.root, ".git", "hooks", "pre-push.before-publish")
        self.assertTrue(saved.exists())
        text = pathlib.Path(out).read_text()
        self.assertIn(f"origin {s.bare}", text)
        self.assertIn("refs/heads/main", text)
        self.assertIn("refs/tags/v0.1.0", text)
        s.git("checkout", "-q", "-b", "blocked")
        s.put("README.md", "b\n")
        s.commit("b")
        before = s.bare_refs()
        p = s.git("push", "origin", "blocked", check=False)
        self.assertNotEqual(p.returncode, 0)
        self.assertEqual(s.bare_refs(), before)
        self.assertIn("refs/heads/blocked", pathlib.Path(out).read_text())

    def test_new_hook_checked_before_old_hook(self):
        s = self.stand()
        out = os.path.join(s.tmp, "old-hook.log")
        self.old_hook(s, out)
        s.publish()
        n = len(pathlib.Path(out).read_text())
        self.assert_rejected(s, "history-local")
        self.assertEqual(len(pathlib.Path(out).read_text()), n)

    # --- сбой на шаге
    def test_failure_after_rename_names_history_local(self):
        s = self.stand()
        p = s.script("--go", env={"GH_CREATE_FAIL": "1"})
        self.assertNotEqual(p.returncode, 0)
        self.assertIn("Не выполнено: gh repo create", p.stderr)
        self.assertIn("history-local", p.stderr)
        self.assertIn("history-local", s.git("branch").stdout)
        again = s.script("--go", env={"GH_CREATE_FAIL": "1"})
        self.assertEqual(again.returncode, 1)
        self.assertIn("history-local уже есть", again.stderr)


class TestProperty(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = Stand(cls.addClassCleanup, extra_commits=5)
        cls.s.git("branch", "change/old")
        cls.s.publish()
        cls.old = cls.s.git("rev-list", "--reverse", "history-local").stdout.split()
        cls.main = cls.s.git("rev-parse", "main").stdout.strip()
        cls.main_tree = cls.s.git("rev-parse", "main^{tree}").stdout.strip()

    def child(self, parent, tree):
        return self.s.git("commit-tree", tree, "-p", parent, "-m", "child").stdout.strip()

    def push(self, sha, kind, name):
        return self.s.git("push", "origin", f"{sha}:{kind}{name}", check=False)

    names = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8).filter(lambda n: n != "main")
    kinds = st.sampled_from(["refs/heads/", "refs/tags/"])

    @settings(max_examples=25, deadline=None)
    @given(idx=st.integers(min_value=0, max_value=5), name=names, kind=kinds, descendant=st.booleans())
    def test_first_publication_without_history_any_old_commit_rejected(self, idx, name, kind, descendant):
        before = self.s.bare_refs()
        sha = self.old[idx]
        if descendant:
            tree = self.s.git("rev-parse", f"{sha}^{{tree}}").stdout.strip()
            sha = self.child(sha, tree)
        p = self.push(sha, kind, name)
        self.assertNotEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.s.bare_refs(), before)

    @settings(max_examples=25, deadline=None)
    @given(name=names, kind=kinds)
    def test_descendant_of_new_main_without_openspec_passes(self, name, kind):
        sha = self.child(self.main, self.main_tree)
        p = self.push(sha, kind, name)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn(f"{kind}{name}", self.s.bare_refs())
        self.assertEqual(self.s.git("push", "origin", f":{kind}{name}", check=False).returncode, 0)


if __name__ == "__main__":
    unittest.main()
