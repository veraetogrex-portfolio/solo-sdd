"""Проверка sdd_dispatch.py: accept (приёмка статуса) и land-local (merge в режиме local)."""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "global/sdd_dispatch.py"
WORKTREE = SCRIPT.parent / "sdd_worktree.py"


def dispatch(script, *args, env=None):
    return subprocess.run([sys.executable, str(script)] + [str(a) for a in args], capture_output=True, text=True,
                          timeout=120, stdin=subprocess.DEVNULL, env=env)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="dispatch-test-")
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class AcceptTest(Base):
    def status(self, text):
        p = os.path.join(self.tmp, "status.txt")
        pathlib.Path(p).write_text(text, encoding="utf-8")
        return p

    def block(self, validate="true", live="echo ok -> ok", wt=None, st="archived", fence=False, indent=""):
        lines = ["STATUS: " + st, "CHANGE: x", "WORKTREE: " + (wt if wt is not None else self.tmp),
                 "VALIDATE: " + validate, "TESTS: touch %s/tests-ran -> exit 0" % self.tmp, "LIVE: " + live]
        lines = [indent + l for l in lines]
        text = "\n".join(lines) + "\n"
        return self.status("```\n" + text + "```\n" if fence else "отчёт\n" + text)

    def test_converges(self):
        r = dispatch(SCRIPT, "accept", self.block())
        self.assertEqual((r.returncode, r.stdout.strip()), (0, "статус сходится"))

    def test_tests_never_run(self):
        dispatch(SCRIPT, "accept", self.block())
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "tests-ran")))

    def test_validate_exit1(self):
        r = dispatch(SCRIPT, "accept", self.block(validate="sh -c 'echo bad; exit 1'"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("VALIDATE", r.stdout)
        self.assertIn("exit 1", r.stdout)
        self.assertIn("bad", r.stdout)

    def test_live_exit1_with_text(self):
        r = dispatch(SCRIPT, "accept", self.block(live="sh -c 'echo ok; exit 1' -> ok"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("LIVE", r.stdout)
        self.assertIn("«ok»", r.stdout)
        self.assertIn("exit 1", r.stdout)

    def test_live_text_missing_and_tail3(self):
        r = dispatch(SCRIPT, "accept", self.block(live="seq 1 5 | sed 's/^/строка/' -> нужный текст"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("«нужный текст»", r.stdout)
        self.assertIn("текста нет", r.stdout)
        for l in ("строка3", "строка4", "строка5"):
            self.assertIn(l, r.stdout)
        self.assertNotIn("строка2", r.stdout)

    def test_long_output_only_three_lines(self):
        r = dispatch(SCRIPT, "accept", self.block(validate="seq 1 500; exit 1"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("500", r.stdout)
        self.assertIn("498", r.stdout)
        self.assertNotIn("497", r.stdout)

    def test_not_ready_commands_not_run(self):
        marker = os.path.join(self.tmp, "ran")
        r = dispatch(SCRIPT, "accept", self.block(st="not_ready", validate="touch " + marker, live="touch %s -> x" % marker))
        self.assertEqual(r.returncode, 2)
        self.assertIn("not_ready", r.stdout)
        self.assertFalse(os.path.exists(marker))

    def test_no_status_line(self):
        r = dispatch(SCRIPT, "accept", self.status("WORKTREE: /tmp\nVALIDATE: true\n"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("STATUS", r.stdout)

    def test_fenced_and_indented(self):
        r = dispatch(SCRIPT, "accept", self.block(fence=True, indent="  "))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_first_occurrence_counts(self):
        p = self.block()
        pathlib.Path(p).write_text(pathlib.Path(p).read_text() + "VALIDATE: false\n")
        self.assertEqual(dispatch(SCRIPT, "accept", p).returncode, 0)

    def test_hostile_inputs_exit2_no_commands(self):
        marker = os.path.join(self.tmp, "ran")
        cases = {
            "empty": (lambda: self.status(""), "пуст"),
            "missing": (lambda: os.path.join(self.tmp, "нет-такого"), "не читается"),
            "live no arrow": (lambda: self.block(live="touch %s" % marker), "' -> '"),
            "live empty text": (lambda: self.block(live="touch %s -> " % marker), "' -> '"),
            "no worktree dir": (lambda: self.block(validate="touch " + marker, wt=os.path.join(self.tmp, "нет")), "папки WORKTREE нет"),
            "empty validate": (lambda: self.block(validate="", live="touch %s -> x" % marker), "поле VALIDATE пусто"),
            "empty worktree": (lambda: self.block(wt="", validate="touch " + marker), "поле WORKTREE пусто"),
        }
        for name, (path, reason) in cases.items():
            with self.subTest(name):
                r = dispatch(SCRIPT, "accept", path())
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
                self.assertIn(reason, r.stdout)
                self.assertNotIn("Traceback", r.stderr)
                self.assertFalse(os.path.exists(marker))

    def test_live_exit_code_under_pipe(self):
        r = dispatch(SCRIPT, "accept", self.block(live="sh -c 'echo ok; exit 1' | cat -> ok"))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("LIVE", r.stdout)
        self.assertIn("exit 1", r.stdout)

    def test_non_utf8_output(self):
        r = dispatch(SCRIPT, "accept", self.block(live="printf '\\377\\376ok' -> ok"))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_usage(self):
        r = dispatch(SCRIPT, "accept")
        self.assertEqual(r.returncode, 2)
        self.assertIn("использование", r.stderr)


def g(repo, *args, check=True):
    p = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)] + list(args),
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check and p.returncode:
        raise AssertionError(p.stderr)
    return p.stdout.strip()


class LandTest(Base):
    def setUp(self):
        super().setUp()
        self.main = os.path.join(self.tmp, "main")
        self.wt = os.path.join(self.tmp, "wt")
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        fake = os.path.join(self.bin, "openspec")
        pathlib.Path(fake).write_text("#!/bin/sh\nexit 0\n")
        os.chmod(fake, 0o755)
        self.env = dict(os.environ, PATH=self.bin + os.pathsep + os.environ["PATH"])
        os.makedirs(self.main)
        g(self.main, "init", "-q", "-b", "main")
        self.put(self.main, "README.md", "base\n")
        self.put(self.main, "AGENTS.md", "rules\n")
        g(self.main, "add", "-A")
        g(self.main, "commit", "-q", "-m", "init")

    def put(self, base, rel, text):
        p = pathlib.Path(base, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def make_change(self, cid="c", rel="feature.txt", text="new\n"):
        g(self.main, "worktree", "add", "-q", "-b", "change/" + cid, self.wt)
        subprocess.run([sys.executable, str(WORKTREE), "setup", self.main, self.wt], capture_output=True,
                       stdin=subprocess.DEVNULL, check=True)
        self.put(self.wt, rel, text)
        g(self.wt, "add", "-A")
        g(self.wt, "commit", "-q", "-m", "change")

    def land(self, *extra, cid="c", script=SCRIPT):
        return dispatch(script, "land-local", self.main, self.wt, cid, *extra, env=self.env)

    def assert_rolled_back(self, head):
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)
        self.assertFalse(os.path.exists(os.path.join(self.main, ".git", "MERGE_HEAD")))
        self.assertTrue(os.path.isdir(self.wt))
        self.assertIn("change/c", g(self.main, "branch", "--list", "change/c"))

    def fake_worktree(self, body):
        d = os.path.join(self.tmp, "fake")
        os.makedirs(d, exist_ok=True)
        shutil.copy(SCRIPT, d)
        shutil.copy(WORKTREE, os.path.join(d, "real_wt.py"))
        pathlib.Path(d, "sdd-worktree.py").write_text(
            "import subprocess, sys, os\nsub = sys.argv[1]\n%s\n"
            "sys.exit(subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'real_wt.py')] + sys.argv[1:]).returncode)\n" % body)
        return os.path.join(d, "sdd_dispatch.py")

    def test_clean_merge(self):
        self.make_change()
        r = self.land()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        head = g(self.main, "rev-parse", "HEAD")
        self.assertIn("смёрджен " + head, r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.main, "feature.txt")))
        self.assertFalse(os.path.exists(self.wt))
        self.assertEqual(g(self.main, "branch", "--list", "change/c"), "")

    def test_merge_conflict(self):
        self.make_change(rel="README.md", text="change\n")
        self.put(self.main, "README.md", "other\n")
        g(self.main, "commit", "-q", "-am", "other")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assertEqual(r.returncode, 6, r.stdout)
        self.assertIn("README.md", r.stdout)
        self.assert_rolled_back(head)

    def test_transport_conflict(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        script = self.fake_worktree("if sub == 'transport':\n    print('конфликт, MAIN не изменён: openspec/x.md')\n    sys.exit(3)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 6, r.stdout)
        self.assertIn("openspec/x.md", r.stdout)
        self.assert_rolled_back(head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_transport_other_failure_rolls_back(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        script = self.fake_worktree("if sub == 'transport':\n    print('ошибка: сломано')\n    sys.exit(1)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("transport", r.stdout)
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)

    def test_not_transferred_passes_through(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'transport':\n    print('не перенесены: docs/a.md')\n    sys.exit(0)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("не перенесены: docs/a.md", r.stdout)

    def test_dirty_main(self):
        self.make_change()
        self.put(self.main, "AGENTS.md", "чужая правка\n")
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land()
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("AGENTS.md", r.stdout)
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_red_junction(self):
        self.make_change(rel="archive-c.txt")
        head = g(self.main, "rev-parse", "HEAD")
        check = "if [ -e archive-c.txt ]; then seq 1 30; exit 1; fi"
        r = self.land("--check", check)
        self.assertEqual(r.returncode, 3, r.stdout)
        lines = r.stdout.splitlines()
        i = lines.index("не смёрджен: проверка красная с change: " + check)
        self.assertEqual(lines[i + 1:], ["    %d" % n for n in range(11, 31)])
        self.assert_rolled_back(head)
        self.assertFalse(os.path.exists(os.path.join(self.main, "archive-c.txt")))

    def test_main_red(self):
        self.make_change()
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land("--check", "echo broken; exit 1")
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertIn("основная красная", r.stdout)
        self.assertIn("broken", r.stdout)
        self.assert_rolled_back(head)

    def test_check_runs_once_after_merge_and_once_on_main(self):
        self.make_change()
        cnt = os.path.join(self.tmp, "count")
        self.land("--check", "echo x >> %s; exit 1" % cnt)
        self.assertEqual(len(pathlib.Path(cnt).read_text().split()), 2)
        shutil.rmtree(self.wt, ignore_errors=True)

    def test_check_runs_once_when_green(self):
        self.make_change()
        cnt = os.path.join(self.tmp, "count")
        r = self.land("--check", "echo x >> " + cnt)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(len(pathlib.Path(cnt).read_text().split()), 1)

    def test_openspec_validate_failure_is_check(self):
        self.make_change()
        pathlib.Path(self.bin, "openspec").write_text("#!/bin/sh\necho invalid spec\nexit 1\n")
        r = self.land()
        self.assertEqual(r.returncode, 4, r.stdout)
        self.assertIn("основная красная: openspec validate --all --strict --no-interactive", r.stdout.splitlines())
        self.assertIn("    invalid spec", r.stdout.splitlines())

    def test_missing_branch(self):
        head = g(self.main, "rev-parse", "HEAD")
        r = self.land(cid="нет")
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("merge", r.stdout)
        self.assertEqual(g(self.main, "rev-parse", "HEAD"), head)

    def test_remove_failure_keeps_merge(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'remove':\n    print('ошибка: занято')\n    sys.exit(1)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        head = g(self.main, "rev-parse", "HEAD")
        self.assertIn("смёрджен %s, не убрано: remove" % head, r.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.main, "feature.txt")))

    def test_check_exit_code_under_pipe(self):
        self.make_change(rel="archive-c.txt")
        self.put(self.tmp, "check.sh", "[ -e archive-c.txt ] && exit 1\nexit 0\n")
        r = self.land("--check", "sh %s/check.sh | cat" % self.tmp)
        self.assertEqual(r.returncode, 3, r.stdout)

    def test_rollback_failure_reports_reason_and_stuck_merge(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'undo':\n    print('ошибка: undo сломан')\n    sys.exit(1)")
        check = "seq 1 25; exit 1"
        r = self.land("--check", check, script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        lines = r.stdout.splitlines()
        i = lines.index("проверка красная: " + check)
        self.assertEqual(lines[i + 1:i + 21], ["    %d" % n for n in range(6, 26)])
        head = g(self.main, "rev-parse", "HEAD")
        self.assertTrue(lines[-1].startswith("смёрджен %s, откат не удался: undo" % head), lines[-1])
        self.assertTrue(os.path.exists(self.wt))

    def test_transport_failure_rollback_failure(self):
        self.make_change()
        script = self.fake_worktree("if sub == 'transport':\n    print('ошибка: сломано')\n    sys.exit(1)\n"
                                    "if sub == 'undo':\n    print('ошибка: undo сломан')\n    sys.exit(1)")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("не смёрджен: transport", r.stdout)
        self.assertIn("откат не удался: undo", r.stdout)

    def test_branch_delete_failure_keeps_merge(self):
        self.make_change()
        script = self.fake_worktree(
            "if sub == 'remove':\n    subprocess.run(['git', '-C', sys.argv[3], '-c', 'user.name=t', '-c', 'user.email=t@t',"
            " 'commit', '-q', '--allow-empty', '-m', 'late'])")
        r = self.land(script=script)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        head = g(self.main, "rev-parse", "HEAD")
        self.assertIn("смёрджен %s, не убрано: branch -d" % head, r.stdout)
        self.assertEqual(len(g(self.main, "rev-list", "--parents", "-n", "1", "HEAD").split()), 3)

    def test_usage(self):
        r = dispatch(SCRIPT, "land-local", self.main)
        self.assertEqual(r.returncode, 2)
        self.assertIn("использование", r.stderr)
        r = dispatch(SCRIPT, "land-local", self.main, self.wt, "c", "--check")
        self.assertEqual(r.returncode, 2)


if __name__ == "__main__":
    unittest.main()
