"""Публичное дерево: нет следов владельца, только устанавливаемый код, лицензия и входной README."""
import json
import os
import pathlib
import re
import subprocess
import tempfile
import unittest

from hypothesis import given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]

# заполнители <user>, <имя> под класс символов не попадают; you исключён явно
HOME_RE = re.compile(r"/(?:Users|home)/(?!you/)[A-Za-z0-9_.-]+/")
SESSION_RE = re.compile(r"(?:session=|session |сесси[а-я]* )[0-9a-f]{8,}", re.I)
SKIP_PREFIXES = ("openspec/",)
SKIP_FILES = ("docs/waiting.md", "tests/test_public_tree.py")


def git(root, *args):
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout


def find_in_line(line, deny_regexes):
    """Найденные фрагменты одной строки (не вся строка: строки бывают по 100 КБ)."""
    return [m.group() for rx in [HOME_RE, SESSION_RE, *deny_regexes] for m in rx.finditer(line)]


def load_denylist(root):
    common = git(root, "rev-parse", "--git-common-dir").strip()
    path = os.path.join(root, common, "info", "public-denylist.txt")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8", errors="ignore") as f:
        words = [w.strip() for w in f.read().splitlines() if w.strip()]
    return [re.compile(r"(?<!\w)" + re.escape(w) + r"(?!\w)", re.I) for w in words]


def scan(root):
    root = str(root)
    deny = load_denylist(root)
    found = []
    for rel in git(root, "ls-files", "-z").split("\0"):
        if not rel or rel.startswith(SKIP_PREFIXES) or rel in SKIP_FILES:
            continue
        full = os.path.join(root, rel)
        if not os.path.isfile(full):
            continue
        with open(full, "rb") as f:
            text = f.read().decode("utf-8", errors="ignore")
        for n, line in enumerate(text.splitlines(), 1):
            for frag in find_in_line(line, deny):
                found.append(f"{rel}:{n}: {frag}")
    return found


class TempRepo(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = self._tmp.name
        git(self.root, "init", "-q")

    def put(self, rel, text):
        p = pathlib.Path(self.root, rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        git(self.root, "add", "-f", rel)

    def deny(self, *words):
        p = pathlib.Path(self.root, ".git", "info")
        p.mkdir(parents=True, exist_ok=True)
        (p / "public-denylist.txt").write_text("\n".join(words) + "\n", encoding="utf-8")


class TestScan(TempRepo):
    def test_clean_tree_is_empty(self):
        self.put("README.md", "cd /Users/<user>/x и /home/you/y\n")
        self.deny("Zeta")
        self.assertEqual(scan(self.root), [])

    def test_forgotten_path_found(self):
        self.put("README.md", "первая\ncd /Users/realname/x\n")
        res = scan(self.root)
        self.assertEqual(len(res), 1)
        self.assertIn("README.md:2", res[0])
        self.assertIn("/Users/realname/", res[0])

    def test_session_id_found(self):
        self.put("a.md", "session=abcdef12\n")
        self.put("b.md", "сессии ABCDEF12 тут\n")
        res = scan(self.root)
        self.assertTrue(any(r.startswith("a.md:1") for r in res), res)
        self.assertTrue(any(r.startswith("b.md:1") for r in res), res)

    def test_no_denylist_still_finds_path(self):
        self.put("README.md", "ok\n/home/bob/x\n")
        self.assertFalse(os.path.exists(os.path.join(self.root, ".git", "info", "public-denylist.txt")))
        self.assertEqual(len(scan(self.root)), 1)

    def test_denylist_case_insensitive(self):
        self.deny("Secret")
        self.put("a.md", "тут SECRET слово\n")
        res = scan(self.root)
        self.assertEqual(len(res), 1)
        self.assertIn("a.md:1", res[0])

    def test_unpublished_paths_skipped(self):
        self.deny("secret")
        self.put("openspec/x.md", "secret /Users/real/\n")
        self.put("docs/waiting.md", "secret\n")
        self.assertEqual(scan(self.root), [])

    def test_word_inside_word(self):
        self.deny("Rok")
        self.put("a.md", "the broken one\n")
        self.assertEqual(scan(self.root), [])
        self.put("b.md", "тут Rok\n")
        self.put("c.md", ".rok-notes\n")
        res = scan(self.root)
        self.assertEqual(len(res), 2, res)

    def test_empty_denylist_line_no_findings(self):
        self.deny("", "  ")
        self.put("a.md", "любой текст\n")
        self.assertEqual(scan(self.root), [])

    def test_missing_file_skipped(self):
        self.put("a.md", "x\n")
        os.remove(os.path.join(self.root, "a.md"))
        self.assertEqual(scan(self.root), [])


class TestProperty(unittest.TestCase):
    @settings(max_examples=200, deadline=None)
    @given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789_.-", min_size=1).filter(lambda n: n != "you"))
    def test_no_owner_traces_home_path_found_for_any_name(self, name):
        bad = f"cd /Users/{name}/p; ls /home/{name}/q"
        self.assertGreaterEqual(len(find_in_line(bad, [])), 2)
        self.assertEqual(find_in_line("cd /Users/<user>/p; ls /home/<user>/q", []), [])


class TestRealTree(unittest.TestCase):
    def test_tree_clean(self):
        self.assertEqual(scan(REPO), [], "\n".join(scan(REPO)))

    def test_only_installable_code(self):
        targets = json.loads((REPO / "targets.json").read_text(encoding="utf-8"))
        readme = (REPO / "README.md").read_text(encoding="utf-8")
        for rel in git(REPO, "ls-files", "global", "schema").split("\n"):
            if rel and not os.path.basename(rel).startswith("test_"):
                self.assertTrue(rel in targets["files"] or rel in readme, f"не устанавливается и не описан: {rel}")
        tracked = git(REPO, "ls-files", "skills").split("\n")
        names = {p.split("/")[1] for p in tracked if p.count("/") >= 2}
        for name in names:
            self.assertIn(name, targets["skills"], f"скилл вне targets.json: {name}")
        for name in targets["skills"]:
            self.assertIn(name, names, f"скилл из targets.json не отслеживается git: {name}")
        self.assertEqual(subprocess.run(["git", "grep", "-n", "mcp__", "--", "skills"], cwd=REPO, capture_output=True, text=True).stdout, "")

    def test_owner_files_not_tracked(self):
        """Файл под одного владельца: в .gitignore и не в индексе; docs/waiting.md выходит в github-publish."""
        text = (REPO / ".gitignore").read_text(encoding="utf-8")
        paths = [p for p in text.split("# под одного владельца", 1)[1].splitlines()[1:] if p]
        self.assertGreaterEqual(len(paths), 10)
        for path in paths:
            if path != "docs/waiting.md":
                self.assertEqual(git(REPO, "ls-files", "--", path), "", f"отслеживается: {path}")

    def test_license(self):
        text = (REPO / "LICENSE").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("MIT License"))
        self.assertIn("Copyright (c) 2026 Вячеслав Ларионов", text)


if __name__ == "__main__":
    unittest.main()
