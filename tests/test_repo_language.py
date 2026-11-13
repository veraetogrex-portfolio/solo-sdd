"""No tracked file contains a Cyrillic letter (U+0400-U+04FF). No allowlist."""
import pathlib
import re
import subprocess
import sys
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]
CYRILLIC = re.compile("[\u0400-\u04ff]")


def cyrillic_lines(root=REPO):
    """Return 'path:line' for every line of a tracked file that holds a Cyrillic letter."""
    files = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True, stdin=subprocess.DEVNULL
    ).stdout.decode("utf-8").split("\0")
    hits = []
    for name in filter(None, files):
        path = root / name
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for n, line in enumerate(text.splitlines(), 1):
            if CYRILLIC.search(line):
                hits.append(f"{name}:{n}")
    return hits


class RepoLanguageTest(unittest.TestCase):
    def test_no_cyrillic_in_tracked_files(self):
        hits = cyrillic_lines()
        self.assertEqual(hits, [], f"{len(hits)} lines with Cyrillic:\n" + "\n".join(hits))

    def test_detects_new_russian_line(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            run = lambda *a: subprocess.run(a, cwd=root, check=True, capture_output=True, stdin=subprocess.DEVNULL)
            run("git", "init", "-q")
            (root / "skills" / "spec-next").mkdir(parents=True)
            (root / "vendor").mkdir()
            (root / "skills" / "spec-next" / "SKILL.md").write_text("# spec-next\n\u041f\u0440\u0438\u0432\u0435\u0442\n")
            (root / "vendor" / "a.md").write_text("ok\n\u0451\n")
            (root / "escapes.py").write_text('OLD = "\\u0414\\u0430"\ncafé Ångström\n')
            run("git", "add", "-A")
            self.assertEqual(cyrillic_lines(root), ["skills/spec-next/SKILL.md:2", "vendor/a.md:2"])


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
