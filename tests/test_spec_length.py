"""Длина текста требований в спеках: не больше MAX_LEN (счёт повторяет OpenSpec 1.14.3).

Без ключа проверяются дельты открытых change; с `--all` ещё и основные спеки."""
import contextlib
import io
import pathlib
import re
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[1]

# MAX_REQUIREMENT_TEXT_LENGTH из OpenSpec
MAX_LEN = 500

FENCE_OPEN = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")
H2 = re.compile(r"^##\s+(.+?)\s*$")
DELTA_REQ = re.compile(r"^###\s*Requirement:\s*(.+?)\s*$", re.I)
MAIN_REQ = re.compile(r"^###\s+(.+?)\s*$")
ANY_HEAD = re.compile(r"^#{1,6}\s")
META = re.compile(r"^\*\*[^*]+\*\*:")


def read_lines(path):
    text = path.read_text(encoding="utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def fence_mask(lines):
    """True для строк внутри блоков кода и самих ограждений."""
    mask, ch, n = [], None, 0
    for line in lines:
        if ch is None:
            m = FENCE_OPEN.match(line)
            if m:
                ch, n = m.group(1)[0], len(m.group(1))
            mask.append(bool(m))
        else:
            mask.append(True)
            m = FENCE_CLOSE.match(line)
            if m and m.group(1)[0] == ch and len(m.group(1)) >= n:
                ch = None
    return mask


def req_length(lines, mask, name):
    """Длина текста требования в единицах UTF-16."""
    captured, meta = [], []
    for line, masked in zip(lines, mask):
        if masked:
            continue
        if ANY_HEAD.match(line):
            break
        t = line.strip()
        if not t:
            continue
        (meta if META.match(t) else captured).append(t)
    text = "\n".join(captured) if captured else ("\n".join(meta) if meta else name)
    return len(text.encode("utf-16-le")) // 2


def delta_blocks(lines, mask):
    """(имя, начало тела, конец) требований из ADDED/MODIFIED."""
    out, in_sec, cur = [], False, None
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        sec = H2.match(line)
        req = DELTA_REQ.match(line)
        if sec or req:
            if cur:
                out.append((cur[0], cur[1], i))
                cur = None
        if sec:
            in_sec = sec.group(1).lower() in ("added requirements", "modified requirements")
        elif req and in_sec:
            cur = (req.group(1), i + 1)
    if cur:
        out.append((cur[0], cur[1], len(lines)))
    return out


def main_blocks(lines, mask):
    """(имя, начало тела, конец) требований основной спеки."""
    out, in_sec, cur = [], False, None
    for i, line in enumerate(lines):
        if mask[i]:
            continue
        if re.match(r"^#{1,3}\s", line) and cur:
            out.append((cur[0], cur[1], i))
            cur = None
        if re.match(r"^#{1,2}\s", line):
            in_sec = bool(re.match(r"^##\s+requirements\s*$", line, re.I))
        elif in_sec:
            m = MAIN_REQ.match(line)
            if m:
                name = re.sub(r"^Requirement:\s*", "", m.group(1), flags=re.I)
                cur = (name, i + 1)
    if cur:
        out.append((cur[0], cur[1], len(lines)))
    return out


def scan(path, root, finder, label):
    try:
        lines = read_lines(path)
    except (OSError, UnicodeDecodeError) as e:
        return ["%s: не читается (%s)" % (path.relative_to(root).as_posix(), e)]
    mask = fence_mask(lines)
    res = []
    for name, a, b in finder(lines, mask):
        n = req_length(lines[a:b], mask[a:b], name)
        if n > MAX_LEN:
            res.append("%s %s: %d > %d" % (label, name, n, MAX_LEN))
    return res


def check(root, main_specs=False):
    root = pathlib.Path(root)
    base = root / "openspec"
    if not base.is_dir():
        print("openspec/ нет — проверять нечего")
        return []
    problems = []
    # архив лежит на уровень глубже (archive/<дата-имя>/specs/) и в этот шаблон не попадает
    for p in sorted((base / "changes").glob("*/specs/*/spec.md")):
        change = p.parents[2].name
        problems += scan(p, root, delta_blocks, "%s specs/%s" % (change, p.parent.name))
    if main_specs:
        for p in sorted((base / "specs").glob("*/spec.md")):
            problems += scan(p, root, main_blocks, "specs/%s" % p.parent.name)
    return problems


def write(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(text, bytes):
        p.write_bytes(text)
    else:
        p.write_text(text, encoding="utf-8")
    return p


def delta(body, kind="ADDED", name="X"):
    return "## %s Requirements\n\n### Requirement: %s\n%s\n" % (kind, name, body)


class TestToy(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.root = self._t.name

    def put(self, body, **kw):
        write(self.root, "openspec/changes/demo/specs/foo/spec.md", delta(body, **kw))
        return check(self.root)

    def test_612(self):
        self.assertEqual(self.put("a" * 612), ["demo specs/foo X: 612 > 500"])

    def test_boundary(self):
        self.assertEqual(self.put("a" * 500), [])
        self.assertEqual(self.put("a" * 501), ["demo specs/foo X: 501 > 500"])

    def test_blank_line_not_counted(self):
        self.assertEqual(self.put("a" * 250 + "\n\n\n" + "b" * 249), [])

    def test_fence_not_counted(self):
        body = "short\n```\n" + "x" * 900 + "\n#### Scenario: Q\n```\n" + "tail"
        self.assertEqual(self.put(body), [])

    def test_scenario_stops_text(self):
        self.assertEqual(self.put("short\n#### Scenario: S\n" + "z" * 900), [])

    def test_metadata(self):
        self.assertEqual(self.put("**ID**: " + "x" * 700 + "\nshort"), [])
        self.assertEqual(len(self.put("**Constraint**: " + "x" * 700)), 1)

    def test_empty_body_is_heading(self):
        self.assertEqual(self.put("", name="Y" * 600), ["demo specs/foo " + "Y" * 600 + ": 600 > 500"])

    def test_emoji_utf16(self):
        self.assertEqual(self.put("\U0001F600" * 300), ["demo specs/foo X: 600 > 500"])

    def test_removed_skipped(self):
        self.assertEqual(self.put("a" * 900, kind="REMOVED"), [])

    def test_archive_skipped(self):
        write(self.root, "openspec/changes/archive/2026-01-01-x/specs/foo/spec.md", delta("a" * 900))
        self.assertEqual(check(self.root), [])

    def test_no_openspec(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(check(self.root), [])
        self.assertIn("openspec/ нет — проверять нечего", buf.getvalue())

    def test_unreadable(self):
        write(self.root, "openspec/changes/demo/specs/foo/spec.md", b"\xff\xfe\xfa bad \x80")
        problems = check(self.root)
        self.assertEqual(len(problems), 1)
        self.assertIn("openspec/changes/demo/specs/foo/spec.md", problems[0])

    def test_main_spec(self):
        write(self.root, "openspec/specs/foo/spec.md",
              "# foo\n\n## Requirements\n\n### Requirement: Y\n" + "a" * 900 + "\n")
        self.assertEqual(check(self.root), [])
        self.assertEqual(check(self.root, main_specs=True), ["specs/foo Y: 900 > 500"])

    def test_main_spec_no_prefix_and_fence(self):
        write(self.root, "openspec/specs/foo/spec.md",
              "# foo\n\n## REQUIREMENTS\n\n### Без префикса\n" + "a" * 501
              + "\n\n### Requirement: Ok\nshort\n```\n### Fake\n" + "b" * 900 + "\n```\n")
        self.assertEqual(check(self.root, main_specs=True), ["specs/foo Без префикса: 501 > 500"])


class TestRepo(unittest.TestCase):
    def test_open_changes(self):
        problems = check(REPO)
        if problems:
            self.fail("\n".join(problems))


if __name__ == "__main__":
    if "--all" in sys.argv:
        problems = check(REPO, main_specs=True)
        for p in problems:
            print(p)
        sys.exit(1 if problems else 0)
    unittest.main()
