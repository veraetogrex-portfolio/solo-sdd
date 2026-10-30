"""Проверка sdd_worktree.py: игнорируемые артефакты между основной папкой и worktree."""
import importlib.util
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

from hypothesis import assume, example, given, settings, strategies as st

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "global/sdd_worktree.py"

_spec = importlib.util.spec_from_file_location("sdd_worktree", SCRIPT)
sw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sw)

SPEC = "openspec/specs/cap/spec.md"
TASKS = "openspec/changes/x/tasks.md"
GITIGNORE = "openspec/\nAGENTS.md\nCLAUDE.md\nnode_modules/\n"
SECTION = "## Рабочая копия\n\n- Пути: `docs/a.md`\n"
ARTIFACTS = [SPEC, TASKS, "AGENTS.md", "CLAUDE.md", "docs/a.md"]


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout


def put(base, rel, text):
    p = pathlib.Path(base, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def tree(base):
    """Все файлы папки (кроме .git) с содержимым."""
    out = {}
    for d, dirs, fs in os.walk(base):
        dirs[:] = [x for x in dirs if x != ".git"]
        for f in fs:
            p = os.path.join(d, f)
            out[os.path.relpath(p, base)] = pathlib.Path(p).read_bytes()
    return out


def run(cmd, main, wt):
    return subprocess.run(["/usr/bin/python3", str(SCRIPT), cmd, str(main), str(wt)],
                          capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)


class Repo:
    """Временный репозиторий с worktree; чистится сам."""

    def __init__(self, ignore=GITIGNORE, tracked=()):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.main = self.root / "main"
        self.wt = self.root / "wt"
        self.main.mkdir()
        git(self.main, "init", "-q", "-b", "main")
        put(self.main, ".gitignore", ignore)
        put(self.main, "README.md", "r\n")
        for rel in tracked:
            put(self.main, rel, "tracked\n")
        git(self.main, "add", "-A", "-f")
        git(self.main, "commit", "-qm", "init")
        git(self.main, "worktree", "add", "-q", "-b", "feat", str(self.wt))

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


class SetupTests(unittest.TestCase):
    def test_copies_ignored_and_links(self):
        r = Repo(tracked=["apps/desktop/main.js"])
        self.addCleanup(r.close)
        put(r.main, "openspec/changes/x/tasks.md", "t\n")
        put(r.main, "AGENTS.md", "a\n")
        put(r.main, "node_modules/p/i.js", "1\n")
        put(r.main, "apps/desktop/node_modules/q/i.js", "2\n")
        res = run("setup", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("скопировано файлов 2, папок ссылок 2", res.stdout)
        self.assertEqual((r.wt / "AGENTS.md").read_text(), "a\n")
        self.assertEqual((r.wt / TASKS).read_text(), "t\n")
        self.assertEqual((pathlib.Path(str(r.wt) + ".base") / "AGENTS.md").read_text(), "a\n")
        for rel in ("node_modules", "apps/desktop/node_modules"):
            d = r.wt / rel
            self.assertTrue(d.is_dir() and not d.is_symlink(), rel)
            self.assertTrue((d / ".sdd-worktree").exists())
            pkg = d / ("p" if rel == "node_modules" else "q")
            self.assertTrue(pkg.is_symlink(), rel)
            self.assertEqual(os.path.realpath(pkg), os.path.realpath(r.main / rel / pkg.name))
        self.assertEqual(git(r.wt, "status", "--short"), "")

    def test_links_excluded_without_gitignore(self):
        r = Repo(ignore="openspec/\nAGENTS.md\n")
        self.addCleanup(r.close)
        put(r.main, "AGENTS.md", "a\n")
        put(r.main, "node_modules/p/i.js", "1\n")
        put(r.main, ".venv/bin/python", "x\n")
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        self.assertTrue((r.wt / ".venv").is_symlink())
        self.assertEqual(git(r.wt, "status", "--short"), "")

    def test_workspace_package(self):
        r = Repo(tracked=["packages/core/index.js"])
        self.addCleanup(r.close)
        put(r.main, "node_modules/left-pad/index.js", "lp\n")
        put(r.main, "node_modules/.vite/c.json", "{}")
        (r.main / "node_modules/@scope").mkdir()
        os.symlink("../../packages/core", r.main / "node_modules/@scope/core")
        (r.main / "node_modules/.bin").mkdir()
        os.symlink("../left-pad/index.js", r.main / "node_modules/.bin/x")
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        put(r.wt, "packages/core/index.js", "изменено\n")
        nm = r.wt / "node_modules"
        self.assertEqual(os.path.realpath(nm / "@scope/core"), os.path.realpath(r.wt / "packages/core"))
        self.assertEqual((nm / "@scope/core/index.js").read_text(encoding="utf-8"), "изменено\n")
        self.assertEqual(os.path.realpath(nm / "left-pad"), os.path.realpath(r.main / "node_modules/left-pad"))
        self.assertEqual(os.path.realpath(nm / ".bin/x"), os.path.realpath(r.main / "node_modules/left-pad/index.js"))
        self.assertFalse(os.path.lexists(nm / ".vite"))
        self.assertEqual(git(r.wt, "status", "--short").strip(), "M packages/core/index.js")
        git(r.wt, "checkout", "packages/core/index.js")
        self.assertEqual(run("remove", r.main, r.wt).returncode, 0)
        self.assertTrue((r.main / "node_modules/left-pad/index.js").exists())
        self.assertTrue(os.path.islink(r.main / "node_modules/@scope/core"))
        self.assertFalse(r.wt.exists())

    def test_foreign_node_modules_kept(self):
        r = Repo()
        self.addCleanup(r.close)
        put(r.main, "node_modules/p/i.js", "1\n")
        (r.wt / "node_modules").mkdir()
        put(r.wt, "node_modules/own/f.js", "x\n")
        run("setup", r.main, r.wt)
        self.assertFalse((r.wt / "node_modules/.sdd-worktree").exists())
        # git подменён: status чистый, worktree remove — отказ; до него скрипт не должен был трогать чужую папку
        real, sw.git = sw.git, lambda repo, *a, **k: subprocess.CompletedProcess(a, int(a[0] != "status"), b"", b"stop")
        try:
            with self.assertRaises(RuntimeError):
                sw.remove(str(r.main), str(r.wt))
        finally:
            sw.git = real
        self.assertEqual((r.wt / "node_modules/own/f.js").read_text(), "x\n")

    def test_tracked_not_copied(self):
        r = Repo(ignore="node_modules/\n", tracked=["openspec/a.md", "AGENTS.md"])
        self.addCleanup(r.close)
        res = run("setup", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("скопировано файлов 0, папок ссылок 0, команда: нет", res.stdout)
        self.assertEqual(os.listdir(str(r.wt) + ".base"), [])

    def test_all_tracked_setup_refresh_transport(self):
        r = Repo(ignore="node_modules/\n", tracked=["openspec/a.md", "AGENTS.md"])
        self.addCleanup(r.close)
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        base = str(r.wt) + ".base"
        self.assertTrue(os.path.isdir(base))
        self.assertEqual(os.listdir(base), [])
        before = tree(r.main), tree(r.wt)
        for cmd in ("refresh", "transport"):
            res = run(cmd, r.main, r.wt)
            self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((tree(r.main), tree(r.wt)), before)

    def test_section_paths_and_command(self):
        r = Repo(ignore=GITIGNORE + "docs/\n")
        self.addCleanup(r.close)
        put(r.main, "AGENTS.md", "# P\n\n## Рабочая копия\n\n- Пути: `docs/a.md`\n- Подготовка: `touch ready`\n\n## Дальше\n")
        put(r.main, "docs/a.md", "d\n")
        put(r.main, "docs/b.md", "no\n")
        res = run("setup", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((r.wt / "docs/a.md").exists())
        self.assertFalse((r.wt / "docs/b.md").exists())
        self.assertTrue((r.wt / "ready").exists())
        self.assertIn("команда: touch ready", res.stdout)

    def test_command_failure(self):
        r = Repo()
        self.addCleanup(r.close)
        put(r.main, "AGENTS.md", "## Рабочая копия\n- Подготовка: `exit 7`\n")
        res = run("setup", r.main, r.wt)
        self.assertEqual(res.returncode, 1)
        self.assertIn("exit 7", res.stderr)


class TransportTests(unittest.TestCase):
    def make(self):
        r = Repo()
        self.addCleanup(r.close)
        put(r.main, "AGENTS.md", "a\nb\nc\nd\n")
        put(r.main, SPEC, "s\n")
        put(r.main, TASKS, "t\n")
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        return r

    def test_two_lines(self):
        r = self.make()
        put(r.main, "AGENTS.md", "N\nb\nc\nd\n")
        put(r.wt, "AGENTS.md", "a\nb\nc\nW\n")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((r.main / "AGENTS.md").read_text(), "N\nb\nc\nW\n")

    def test_archive(self):
        r = self.make()
        (r.wt / TASKS).unlink()
        (r.wt / "openspec/changes/x").rmdir()
        put(r.wt, "openspec/changes/archive/2026-10-21-x/tasks.md", "t\n")
        put(r.wt, SPEC, "s2\n")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertTrue((r.main / "openspec/changes/archive/2026-10-21-x/tasks.md").exists())
        self.assertFalse((r.main / "openspec/changes/x").exists())
        self.assertEqual((r.main / SPEC).read_text(), "s2\n")

    def test_conflict(self):
        r = self.make()
        put(r.main, "AGENTS.md", "M\nb\nc\nd\n")
        put(r.wt, "AGENTS.md", "W\nb\nc\nd\n")
        put(r.wt, SPEC, "s2\n")
        before = tree(r.main)
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 3)
        self.assertIn("AGENTS.md", res.stdout)
        self.assertEqual(tree(r.main), before)
        self.assertFalse(os.path.exists(str(r.wt) + ".undo"))

    def test_undo_and_repeat(self):
        r = self.make()
        before = tree(r.main)
        (r.wt / TASKS).unlink()
        put(r.wt, "openspec/changes/archive/2026-10-21-x/tasks.md", "t\n")
        put(r.wt, SPEC, "s2\n")
        self.assertEqual(run("transport", r.main, r.wt).returncode, 0)
        self.assertNotEqual(tree(r.main), before)
        res = run("undo", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(tree(r.main), before)
        self.assertEqual(run("transport", r.main, r.wt).returncode, 0)
        self.assertEqual((r.main / SPEC).read_text(), "s2\n")

    def test_undo_nothing(self):
        r = self.make()
        res = run("undo", r.main, r.wt)
        self.assertEqual(res.returncode, 0)
        self.assertIn("нечего отменять", res.stdout)

    def test_conflict_keeps_undo(self):
        r = self.make()
        put(r.wt, SPEC, "s2\n")
        self.assertEqual(run("transport", r.main, r.wt).returncode, 0)
        first = tree(str(r.wt) + ".undo")
        self.assertIn(os.path.join("files", SPEC), first)
        put(r.wt, "openspec/changes/archive/2026-10-21-y/tasks.md", "t\n")
        self.assertEqual(run("transport", r.main, r.wt).returncode, 0)
        undo = tree(str(r.wt) + ".undo")
        self.assertNotIn(os.path.join("files", SPEC), undo)
        self.assertEqual(undo[".created"], b"openspec/changes/archive/2026-10-21-y/tasks.md\n")
        put(r.main, "AGENTS.md", "M\nb\nc\nd\n")
        put(r.wt, "AGENTS.md", "W\nb\nc\nd\n")
        self.assertEqual(run("transport", r.main, r.wt).returncode, 3)
        self.assertEqual(tree(str(r.wt) + ".undo"), undo)


class RefreshTests(unittest.TestCase):
    def make(self):
        r = Repo()
        self.addCleanup(r.close)
        put(r.main, "AGENTS.md", "a\nb\nc\nd\n")
        put(r.main, SPEC, "s\n")
        put(r.main, TASKS, "t\n")
        put(r.main, "openspec/changes/sosed/tasks.md", "z\n")
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        return r

    def test_neighbour_appended_agents(self):
        r = self.make()
        put(r.main, "AGENTS.md", "N\na\nb\nc\nd\n")
        put(r.wt, "AGENTS.md", "a\nb\nc\nd\nW\n")
        res = run("refresh", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((r.wt / "AGENTS.md").read_text(), "N\na\nb\nc\nd\nW\n")
        self.assertEqual((pathlib.Path(str(r.wt) + ".base") / "AGENTS.md").read_text(), "N\na\nb\nc\nd\n")

    def test_conflict_markers(self):
        r = self.make()
        put(r.main, SPEC, "M\n")
        put(r.wt, SPEC, "W\n")
        res = run("refresh", r.main, r.wt)
        self.assertEqual(res.returncode, 3)
        self.assertIn(SPEC, res.stdout)
        self.assertIn("<<<<<<<", (r.wt / SPEC).read_text())

    def test_neighbour_archived(self):
        r = self.make()
        (r.main / "openspec/changes/sosed/tasks.md").rename(r.main / "openspec/changes/sosed-tasks.tmp")
        shutil.rmtree(r.main / "openspec/changes/sosed")
        put(r.main, "openspec/changes/archive/2026-10-21-sosed/tasks.md", "z\n")
        (r.main / "openspec/changes/sosed-tasks.tmp").unlink()
        res = run("refresh", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertFalse((r.wt / "openspec/changes/sosed").exists())
        self.assertTrue((r.wt / "openspec/changes/archive/2026-10-21-sosed/tasks.md").exists())

    def test_deleted_in_main_changed_in_wt_not_resurrected(self):
        r = self.make()
        shutil.rmtree(r.main / "openspec/changes/sosed")
        put(r.wt, "openspec/changes/sosed/tasks.md", "w\n")
        self.assertEqual(run("refresh", r.main, r.wt).returncode, 3)
        self.assertEqual(run("transport", r.main, r.wt).returncode, 3)
        self.assertFalse((r.main / "openspec/changes/sosed").exists())
        (r.wt / "openspec/changes/sosed/tasks.md").unlink()
        self.assertEqual(run("transport", r.main, r.wt).returncode, 0)
        self.assertFalse((r.main / "openspec/changes/sosed").exists())

    def test_changed_in_main_deleted_in_wt_kept(self):
        r = self.make()
        put(r.main, SPEC, "M\n")
        (r.wt / SPEC).unlink()
        self.assertEqual(run("refresh", r.main, r.wt).returncode, 3)
        self.assertEqual(run("transport", r.main, r.wt).returncode, 3)
        self.assertEqual((r.main / SPEC).read_text(), "M\n")

    def test_resolution_is_transported(self):
        r = self.make()
        put(r.main, SPEC, "M\n")
        put(r.wt, SPEC, "W\n")
        self.assertEqual(run("refresh", r.main, r.wt).returncode, 3)
        put(r.wt, SPEC, "решение\n")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((r.main / SPEC).read_text(), "решение\n")

    def test_new_file_copied(self):
        r = self.make()
        put(r.main, "openspec/changes/new/tasks.md", "n\n")
        res = run("refresh", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("скопировано 1", res.stdout)
        self.assertEqual((r.wt / "openspec/changes/new/tasks.md").read_text(), "n\n")

    def test_no_snapshot(self):
        r = Repo()
        self.addCleanup(r.close)
        res = run("refresh", r.main, r.wt)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("снимка", res.stderr)


class RemoveTests(unittest.TestCase):
    def test_cleanup(self):
        r = Repo()
        self.addCleanup(r.close)
        put(r.main, "AGENTS.md", "a\n")
        put(r.main, "node_modules/p/i.js", "1\n")
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        put(r.wt, SPEC, "s\n")
        run("transport", r.main, r.wt)
        res = run("remove", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn(str(r.wt), git(r.main, "worktree", "list"))
        for suffix in (".base", ".undo", ".start", ""):
            self.assertFalse(os.path.exists(str(r.wt) + suffix))
        self.assertTrue((r.main / "node_modules/p/i.js").exists())

    def test_dispatcher_temp_parent_removed(self):
        r = Repo()
        self.addCleanup(r.close)
        wt = r.root / "sdd-x1" / "wt-c2"
        git(r.main, "worktree", "add", "-q", "-b", "c2", str(wt))
        self.assertEqual(run("remove", r.main, wt).returncode, 0)
        self.assertFalse(wt.parent.exists())
        self.assertTrue(r.root.exists())

    def test_uncommitted_work_is_kept(self):
        r = Repo()
        self.addCleanup(r.close)
        put(r.main, "AGENTS.md", "a\n")
        put(r.main, "node_modules/p/i.js", "1\n")
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        put(r.wt, "README.md", "правка без коммита\n")
        res = run("remove", r.main, r.wt)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("worktree remove", res.stderr)
        self.assertEqual((r.wt / "README.md").read_text(encoding="utf-8"), "правка без коммита\n")
        self.assertTrue(os.path.isdir(str(r.wt) + ".base"))
        self.assertTrue((r.wt / "node_modules/p").is_symlink())


class DiscardTests(unittest.TestCase):
    def prepared(self, agents=None):
        r = Repo()
        self.addCleanup(r.close)
        if agents:
            put(r.main, "AGENTS.md", agents)
        return r

    def assertKept(self, r, res):
        self.assertEqual(res.returncode, 1, res.stdout)
        self.assertIn(str(r.wt), git(r.main, "worktree", "list"))
        self.assertIn("feat", git(r.main, "branch", "--list", "feat"))
        for suffix in (".base", ".start"):
            self.assertTrue(os.path.exists(str(r.wt) + suffix))

    def test_failed_setup_is_discarded(self):
        r = self.prepared("## Рабочая копия\n- Подготовка: `echo x > junk.txt; exit 1`\n")
        put(r.main, "node_modules/p/i.js", "1\n")
        before = tree(r.main)
        self.assertEqual(run("setup", r.main, r.wt).returncode, 1)
        self.assertEqual((r.wt.parent / "wt.start").read_text().strip(), git(r.wt, "rev-parse", "HEAD").strip())
        self.assertNotEqual(run("remove", r.main, r.wt).returncode, 0)
        self.assertIn(str(r.wt), git(r.main, "worktree", "list"))
        res = run("discard", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("worktree отброшен: feat", res.stdout)
        self.assertNotIn(str(r.wt), git(r.main, "worktree", "list"))
        self.assertEqual(git(r.main, "branch", "--list", "feat"), "")
        for suffix in (".base", ".start", ""):
            self.assertFalse(os.path.exists(str(r.wt) + suffix))
        self.assertEqual(tree(r.main), before)
        self.assertTrue((r.main / "node_modules/p/i.js").exists())

    def test_commit_in_branch_refuses(self):
        r = self.prepared()
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        put(r.wt, "new.txt", "n\n")
        git(r.wt, "add", "-A")
        git(r.wt, "commit", "-qm", "work")
        self.assertKept(r, run("discard", r.main, r.wt))

    def test_no_start_record_refuses(self):
        r = self.prepared()
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        os.unlink(str(r.wt) + ".start")
        res = run("discard", r.main, r.wt)
        self.assertEqual(res.returncode, 1)
        self.assertIn("нет записи начала", res.stderr)
        self.assertIn(str(r.wt), git(r.main, "worktree", "list"))
        self.assertTrue(os.path.exists(str(r.wt) + ".base"))

    def test_start_commit_only_in_branch_refuses(self):
        r = self.prepared()
        put(r.wt, "new.txt", "n\n")
        git(r.wt, "add", "-A")
        git(r.wt, "commit", "-qm", "only here")
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        self.assertKept(r, run("discard", r.main, r.wt))

    def test_detached_head_keeps_branch(self):
        r = self.prepared()
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        git(r.wt, "checkout", "-q", "--detach")
        res = run("discard", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("worktree отброшен: без ветки", res.stdout)
        self.assertNotIn(str(r.wt), git(r.main, "worktree", "list"))
        self.assertIn("feat", git(r.main, "branch", "--list", "feat"))

    def test_git_failure_keeps_record(self):
        r = self.prepared()
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        git(r.main, "worktree", "lock", str(r.wt))
        res = run("discard", r.main, r.wt)
        self.assertEqual(res.returncode, 1)
        self.assertIn("git worktree remove", res.stderr)
        self.assertTrue(os.path.exists(str(r.wt) + ".start"))
        git(r.main, "worktree", "unlock", str(r.wt))
        lock = r.main / ".git/refs/heads/feat.lock"
        lock.write_text("")
        res = run("discard", r.main, r.wt)
        self.assertEqual(res.returncode, 1)
        self.assertIn("git branch -D", res.stderr)
        self.assertTrue(os.path.exists(str(r.wt) + ".start"))
        lock.unlink()

    def test_unreadable_head_refuses(self):
        r = self.prepared()
        self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
        (r.wt / ".git").rename(r.wt / ".git-off")
        res = run("discard", r.main, r.wt)
        self.assertEqual(res.returncode, 1)
        self.assertIn("ничего не удалено", res.stderr)
        self.assertNotIn("свои коммиты", res.stderr)
        self.assertTrue(os.path.exists(str(r.wt) + ".start"))

    def test_dispatcher_temp_parent_removed(self):
        r = self.prepared()
        wt = r.root / "sdd-x1" / "wt-c2"
        git(r.main, "worktree", "add", "-q", "-b", "c2", str(wt))
        self.assertEqual(run("setup", r.main, wt).returncode, 0)
        self.assertEqual(run("discard", r.main, wt).returncode, 0)
        self.assertFalse(wt.parent.exists())
        self.assertTrue(r.root.exists())


MIB = 1024 * 1024
DOC = "docs/architecture.md"
IGNORED = "\n".join([GITIGNORE.rstrip(), DOC, "out/", ".stand-data/", "docs/dump.md", "tsconfig.tsbuildinfo", ".env"]) + "\n"


class IndividuallyIgnoredTests(unittest.TestCase):
    def make(self, doc="a\nb\nc\nd\n"):
        r = Repo(ignore=IGNORED, tracked=["docs/notes.md"])
        self.addCleanup(r.close)
        put(r.main, DOC, doc)
        return r

    def setup_ok(self, r):
        res = run("setup", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)

    def test_both_sides_merged(self):
        r = self.make()
        self.setup_ok(r)
        self.assertEqual((r.wt / DOC).read_text(), "a\nb\nc\nd\n")
        self.assertEqual((pathlib.Path(str(r.wt) + ".base") / DOC).read_text(), "a\nb\nc\nd\n")
        put(r.main, DOC, "M\na\nb\nc\nd\n")
        put(r.wt, DOC, "a\nb\nc\nd\nW\n")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((r.main / DOC).read_text(), "M\na\nb\nc\nd\nW\n")
        self.assertNotIn("не перенесены", res.stdout)

    def test_cyrillic_name(self):
        name = "docs/архитектура.md"
        r = Repo(ignore=GITIGNORE + name + "\n", tracked=["docs/notes.md"])
        self.addCleanup(r.close)
        put(r.main, name, "a\n")
        self.setup_ok(r)
        put(r.wt, name, "a\nb\n")
        self.assertEqual(run("transport", r.main, r.wt).returncode, 0)
        self.assertEqual((r.main / name).read_text(), "a\nb\n")

    def test_ignored_folder_not_in_set(self):
        r = self.make()
        put(r.main, "out/app.md", "o\n")
        put(r.main, ".stand-data/s.md", "c\n")
        self.setup_ok(r)
        self.assertFalse((r.wt / "out").exists())
        self.assertFalse((r.wt / ".stand-data").exists())
        put(r.wt, "out/app.md", "changed\n")
        put(r.wt, ".stand-data/s.md", "changed\n")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((r.main / "out/app.md").read_text(), "o\n")
        self.assertNotIn("не перенесены", res.stdout)

    def test_generated_and_env_named(self):
        r = self.make()
        put(r.main, "tsconfig.tsbuildinfo", "t\n")
        put(r.main, ".env", "e\n")
        self.setup_ok(r)
        self.assertFalse((r.wt / "tsconfig.tsbuildinfo").exists())
        self.assertFalse((r.wt / ".env").exists())
        put(r.wt, "tsconfig.tsbuildinfo", "t2\n")
        put(r.wt, ".env", "e2\n")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("не перенесены: .env, tsconfig.tsbuildinfo", res.stdout)
        self.assertEqual((r.main / "tsconfig.tsbuildinfo").read_text(), "t\n")
        self.assertEqual((r.main / ".env").read_text(), "e\n")

    def test_big_document_named(self):
        r = self.make()
        put(r.main, "docs/dump.md", "x\n" * (3 * MIB))
        self.setup_ok(r)
        self.assertFalse((r.wt / "docs/dump.md").exists())
        put(r.wt, "docs/dump.md", "y\n" * (3 * MIB))
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertIn("не перенесены: docs/dump.md", res.stdout)
        self.assertEqual((r.main / "docs/dump.md").read_text(), "x\n" * (3 * MIB))

    def test_equal_or_wt_only_not_named(self):
        r = self.make()
        put(r.main, "tsconfig.tsbuildinfo", "t\n")
        self.setup_ok(r)
        put(r.wt, "tsconfig.tsbuildinfo", "t\n")
        put(r.wt, ".env", "только в worktree\n")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("не перенесены", res.stdout)
        self.assertFalse((r.main / ".env").exists())

    def test_links_skipped(self):
        r = self.make()
        (r.main / "docs/target.md").write_text("t\n")
        os.symlink("target.md", r.main / "docs/dump.md")
        os.symlink("docs", r.main / ".env")
        self.setup_ok(r)
        self.assertFalse(os.path.lexists(r.wt / "docs/dump.md"))
        (r.wt / "docs/dump.md").write_text("w\n")
        os.symlink("elsewhere", r.wt / ".env")
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertNotIn("не перенесены", res.stdout)

    def test_conflict(self):
        r = self.make()
        self.setup_ok(r)
        put(r.main, DOC, "M\nb\nc\nd\n")
        put(r.wt, DOC, "W\nb\nc\nd\n")
        before = tree(r.main)
        res = run("transport", r.main, r.wt)
        self.assertEqual(res.returncode, 3)
        self.assertIn(DOC, res.stdout)
        self.assertEqual(tree(r.main), before)

    def test_refresh_brings_main_edit(self):
        r = self.make()
        self.setup_ok(r)
        put(r.main, DOC, "M\na\nb\nc\nd\n")
        put(r.wt, DOC, "a\nb\nc\nd\nW\n")
        res = run("refresh", r.main, r.wt)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual((r.wt / DOC).read_text(), "M\na\nb\nc\nd\nW\n")
        self.assertEqual((pathlib.Path(str(r.wt) + ".base") / DOC).read_text(), "M\na\nb\nc\nd\n")

    def test_undo_returns_document(self):
        r = self.make()
        self.setup_ok(r)
        put(r.main, DOC, "M\na\nb\nc\nd\n")
        before = tree(r.main)
        put(r.wt, DOC, "a\nb\nc\nd\nW\n")
        self.assertEqual(run("transport", r.main, r.wt).returncode, 0)
        self.assertNotEqual(tree(r.main), before)
        self.assertEqual(run("undo", r.main, r.wt).returncode, 0)
        self.assertEqual(tree(r.main), before)

    def test_remove_cleans_list(self):
        r = self.make()
        self.setup_ok(r)
        self.assertEqual(run("remove", r.main, r.wt).returncode, 0)
        self.assertFalse(os.path.exists(str(r.wt) + ".base"))


class IndividuallyIgnoredPropertyTests(unittest.TestCase):
    @settings(max_examples=60, deadline=None)
    @example(1, ".md", "docs/x", True, True, 0)
    @example(1, ".md", "docs/x", True, True, 1)
    @example(0, ".md", "out/x", True, False, 0)
    @example(0, ".log", "docs/x", True, False, 0)
    @given(st.sampled_from([0, 1]), st.sampled_from([".md", ".txt", ".rst", ".adoc", ".MD", ".log", ".json", ""]),
           st.sampled_from(["docs/x", "out/x", "docs/.env", "docs/.env.local"]),
           st.booleans(), st.booleans(), st.sampled_from([-1, 0, 1]))
    def test_individually_ignored_round_trip(self, big, ext, stem, edit_main, edit_wt, delta):
        rel = stem + ext
        r = Repo(ignore=GITIGNORE + "out/\n" + rel + "\n", tracked=["docs/notes.md"])
        try:
            pad = (MIB + delta - 6) if big else 0
            body = "a\nb\nc\n" + "p" * pad + ("\n" if not big else "")
            put(r.main, rel, body)
            self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
            carried = (not rel.startswith("out/") and rel.lower().endswith((".md", ".txt", ".rst", ".adoc"))
                       and not os.path.basename(rel).startswith(".env")
                       and len(body.encode()) <= MIB)
            self.assertEqual(rel in tree(str(r.wt) + ".base"), carried, "снимок")
            if not carried and os.path.exists(r.wt / rel):
                self.fail("копия вне набора: " + rel)
            if edit_main:
                put(r.main, rel, "M\n" + body)
            if edit_wt:
                put(r.wt, rel, body + "W\n")
            before = tree(r.main)
            res = run("transport", r.main, r.wt)
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            got = (r.main / rel).read_bytes()
            if carried and edit_wt:
                want = ("M\n" if edit_main else "") + body + "W\n"
                self.assertEqual(got, want.encode())
            else:
                self.assertEqual(tree(r.main), before)
            named = edit_wt and not carried and not rel.startswith("out/")
            self.assertEqual("не перенесены: " + rel in res.stdout, named, res.stdout)
            self.assertEqual(run("undo", r.main, r.wt).returncode, 0)
            self.assertEqual(tree(r.main), before, "undo не вернул MAIN")
        finally:
            r.close()


@st.composite
def scenario(draw):
    base = ["l%d" % i for i in range(draw(st.integers(0, 7)))]
    m = draw(st.none() | st.integers(0, max(len(base) - 1, 0)))
    w = draw(st.none() | st.integers(0, max(len(base) - 1, 0)))
    if not base:
        m = w = None
    if m is not None and w is not None:
        assume(m == w or abs(m - w) > 1)
    return dict(base=base, m=m, w=w, wt_new=draw(st.booleans()), drop=draw(st.booleans()),
                main_tasks=draw(st.booleans()), agents_wt=draw(st.booleans()))


OPS = ["file", "edit", "delete", "add", "commit", "branch", "back", "detach"]


class PropertyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = Repo()

    @classmethod
    def tearDownClass(cls):
        cls.r.close()

    def reset(self, base):
        r = self.r
        shutil.rmtree(r.main / "openspec", ignore_errors=True)
        shutil.rmtree(r.wt / "openspec", ignore_errors=True)
        for p in (r.main / "AGENTS.md", r.wt / "AGENTS.md"):
            if p.exists():
                p.unlink()
        shutil.rmtree(str(r.wt) + ".base", ignore_errors=True)
        shutil.rmtree(str(r.wt) + ".undo", ignore_errors=True)
        put(r.main, SPEC, "".join(x + "\n" for x in base))
        put(r.main, TASKS, "t\n")
        put(r.main, "AGENTS.md", "a\n")
        self.assertEqual(sw.setup(str(r.main), str(r.wt)), 0)

    @settings(max_examples=150, deadline=None)
    @given(scenario())
    def test_ignored_artifacts_transport_property(self, sc):
        r = self.r
        base = sc["base"]
        self.reset(base)
        main_lines, wt_lines = list(base), list(base)
        if sc["m"] is not None:
            main_lines[sc["m"]] = "MAIN"
            put(r.main, SPEC, "".join(x + "\n" for x in main_lines))
        if sc["w"] is not None:
            wt_lines[sc["w"]] = "WT"
        if not base and sc["wt_new"]:
            wt_lines = ["WT"]
        put(r.wt, SPEC, "".join(x + "\n" for x in wt_lines))
        if sc["agents_wt"]:
            put(r.wt, "AGENTS.md", "a\nwt\n")
        if sc["main_tasks"]:
            put(r.main, TASKS, "t-main\n")
        if sc["drop"]:
            shutil.rmtree(r.wt / "openspec/changes/x")
        conflict = (sc["m"] is not None and sc["m"] == sc["w"]) or (sc["drop"] and sc["main_tasks"])
        before = tree(r.main)
        code = sw.transport(str(r.main), str(r.wt))
        if conflict:
            self.assertEqual(code, 3)
            self.assertEqual(tree(r.main), before, "при конфликте MAIN изменён")
            return
        self.assertEqual(code, 0)
        got = (r.main / SPEC).read_text().splitlines()
        if sc["m"] is not None:
            self.assertEqual(got[sc["m"]], "MAIN")
        if sc["w"] is not None:
            self.assertEqual(got[sc["w"]], "WT")
        if sc["m"] is None:
            self.assertEqual(got, (r.wt / SPEC).read_text().splitlines())
        if sc["agents_wt"]:
            self.assertEqual((r.main / "AGENTS.md").read_text(), "a\nwt\n")
        self.assertEqual((r.main / "openspec/changes/x").exists(), not sc["drop"])
        if tree(r.main) != before:
            self.assertEqual(sw.undo(str(r.main), str(r.wt)), 0)
            self.assertEqual(tree(r.main), before, "undo не вернул MAIN")

    @settings(max_examples=40, deadline=None)
    @example(frozenset())
    @example(frozenset(ARTIFACTS))
    @given(st.frozensets(st.sampled_from(ARTIFACTS)))
    def test_worktree_setup_property(self, tracked):
        r = Repo(ignore="".join(x + "\n" for x in ARTIFACTS if x not in tracked))
        try:
            for rel in ARTIFACTS:
                put(r.main, rel, SECTION if rel == "AGENTS.md" else "t\n")
            if tracked:
                git(r.main, "add", "-f", *tracked)
                git(r.main, "commit", "-qm", "artifacts")
                git(r.wt, "merge", "-q", "--ff-only", "main")
            self.assertEqual(sw.setup(str(r.main), str(r.wt)), 0)
            base = str(r.wt) + ".base"
            self.assertTrue(os.path.isdir(base), "нет снимка")
            self.assertEqual(set(tree(base)), set(ARTIFACTS) - tracked)
            before = tree(r.main), tree(r.wt)
            self.assertEqual(sw.refresh(str(r.main), str(r.wt)), 0)
            self.assertEqual(sw.transport(str(r.main), str(r.wt)), 0)
            self.assertEqual((tree(r.main), tree(r.wt)), before)
        finally:
            r.close()

    @settings(max_examples=40, deadline=None)
    @given(st.lists(st.sampled_from(OPS), max_size=7))
    @example([])
    @example(["commit", "branch"])
    @example(["commit", "back"])
    @example(["commit", "detach"])
    def test_discard_unused_worktree_property(self, ops):
        r = Repo()
        try:
            self.assertEqual(run("setup", r.main, r.wt).returncode, 0)
            start = git(r.wt, "rev-parse", "HEAD").strip()
            for n, op in enumerate(ops):
                if op == "file":
                    put(r.wt, "f%d.txt" % n, "x\n")
                elif op == "edit":
                    put(r.wt, "README.md", "e%d\n" % n)
                elif op == "delete":
                    if (r.wt / "README.md").exists():
                        (r.wt / "README.md").unlink()
                elif op == "add":
                    git(r.wt, "add", "-A")
                elif op == "commit":
                    git(r.wt, "add", "-A")
                    git(r.wt, "commit", "--allow-empty", "-qm", "x")
                elif op == "branch":
                    git(r.wt, "checkout", "-q", "-b", "b%d" % n)
                elif op == "back":
                    git(r.wt, "checkout", "-q", "-f", "-b", "b%d" % n, start)
                else:
                    git(r.wt, "checkout", "-q", "-f", "--detach", start)
            want = git(r.wt, "rev-parse", "HEAD").strip() == start
            refs = ("rev-list", "--branches", "--tags", "--remotes")
            before = set(git(r.main, *refs).split())
            res = run("discard", r.main, r.wt)
            self.assertEqual(res.returncode == 0, want, res.stderr)
            self.assertLessEqual(before, set(git(r.main, *refs).split()))
            if want:
                self.assertFalse(r.wt.exists())
            else:
                for suffix in ("", ".base", ".start"):
                    self.assertTrue(os.path.exists(str(r.wt) + suffix))
        finally:
            r.close()


if __name__ == "__main__":
    unittest.main()
