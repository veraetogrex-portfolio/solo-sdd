"""tests/stands/map-stand/check.py: map statements without an existing path and bad stamps give exit 1."""
import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests" / "stands" / "map-stand"))
import check  # noqa: E402

FILES = ("STACK.md", "ARCHITECTURE.md", "CONVENTIONS.md", "CONCERNS.md")


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=cwd, check=True,
                          capture_output=True, text=True, stdin=subprocess.DEVNULL).stdout.strip()


class MapCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = pathlib.Path(self.tmp.name)
        git(self.repo, "init", "-q")
        (self.repo / "src").mkdir()
        (self.repo / "src" / "app.py").write_text("print(1)\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "init")
        self.head = git(self.repo, "rev-parse", "HEAD")
        self.date = git(self.repo, "log", "-1", "--format=%cs")
        (self.repo / "docs" / "codebase").mkdir(parents=True)
        for name in FILES:
            self.write(name, "## Items\n\n- Entry point: `src/app.py:1`\n- Code lives in `src/`\n")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, body, stamp=None):
        stamp = stamp or "Commit: %s %s" % (self.head, self.date)
        (self.repo / "docs" / "codebase" / name).write_text(stamp + "\n\n" + body)

    def run_check(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = check.check(self.repo)
        return code, out.getvalue()

    def test_fresh_map_passes(self):
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertIn("map ok: 4 files, 8 statements, 0 findings", out)

    def test_invented_path_fails(self):
        self.write("ARCHITECTURE.md", "- Errors are logged in `src/logger.py`\n- Real: `src/app.py`\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("docs/codebase/ARCHITECTURE.md:3: no existing path: Errors are logged in `src/logger.py`", out)
        self.assertNotIn("Real:", out)

    def test_statement_without_path_fails(self):
        self.write("CONCERNS.md", "* Errors are logged centrally\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("CONCERNS.md:3: no existing path", out)

    def test_path_added_after_stamp_fails(self):
        (self.repo / "src" / "new.py").write_text("x = 1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "new")
        self.write("STACK.md", "- New module `src/new.py`\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("STACK.md:3: no existing path", out)

    def test_prose_statement_fails(self):
        self.write("ARCHITECTURE.md", "- Real: `src/app.py`\n\nErrors are logged centrally.\n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("ARCHITECTURE.md:5: not a list item: Errors are logged centrally.", out)

    def test_stamp_only_file_fails(self):
        self.write("CONVENTIONS.md", "")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("docs/codebase/CONVENTIONS.md: no statements", out)

    def test_stamp_with_wrong_date_or_tail_fails(self):
        for stamp in ("Commit: %s 2099-12-31" % self.head, "Commit: %s %s junk" % (self.head, self.date)):
            self.write("STACK.md", "- `src/app.py`\n", stamp=stamp)
            code, out = self.run_check()
            self.assertEqual(code, 1, stamp)
            self.assertIn("STACK.md:1: stamp is not", out)

    def test_stamp_not_a_commit_fails(self):
        self.write("STACK.md", "- `src/app.py`\n", stamp="Commit: %s %s" % ("0" * 40, self.date))
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("STACK.md:1: stamp is not `Commit: <hash> <date>` of a commit of the repository", out)

    def test_short_hash_stamp_fails(self):
        self.write("STACK.md", "- `src/app.py`\n", stamp="Commit: %s %s" % (self.head[:7], self.date))
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("STACK.md:1: stamp is not", out)

    def test_missing_and_empty_files_fail(self):
        (self.repo / "docs" / "codebase" / "CONVENTIONS.md").unlink()
        (self.repo / "docs" / "codebase" / "CONCERNS.md").write_text("  \n")
        code, out = self.run_check()
        self.assertEqual(code, 1)
        self.assertIn("docs/codebase/CONVENTIONS.md: missing or empty", out)
        self.assertIn("docs/codebase/CONCERNS.md: missing or empty", out)

    def test_cli_exit_code(self):
        self.write("STACK.md", "- `nowhere.py`\n")
        p = subprocess.run([sys.executable, str(REPO / "tests" / "stands" / "map-stand" / "check.py"), str(self.repo)],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 1)
        self.assertIn("map FAIL:", p.stdout)


if __name__ == "__main__":
    unittest.main()
