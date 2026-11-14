"""solo_sdd/settings_ui.py: the settings screen model driven by key names.

The stand tests/stands/settings-tui.py proves the scenarios a person walks through on a real terminal; the rows here
are the cases it does not reach.
"""
import os
import shutil
import sys
import tempfile
import unittest

from hypothesis import example, given, settings as hsettings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import settings, settings_ui  # noqa: E402
from test_settings import VALUES, files  # noqa: E402


def project(text="", agents_md=None, ci=False):
    d = tempfile.mkdtemp()
    os.makedirs(os.path.join(d, "solo-sdd", "changes"))
    with open(os.path.join(d, settings.SETTINGS_FILE), "w", encoding="utf-8", newline="") as f:
        f.write(text)
    if agents_md is not None:
        with open(os.path.join(d, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write(agents_md)
    if ci:
        os.makedirs(os.path.join(d, ".github", "workflows"))
        open(os.path.join(d, ".github", "workflows", "test.yml"), "w").close()
    return d


def config(d):
    with open(os.path.join(d, settings.SETTINGS_FILE), encoding="utf-8", newline="") as f:
        return f.read()


def press(s, *keys):
    out = None
    for k in keys:
        out = s.handle(k)
    return out


def select(s, key):
    while s.key != key:
        s.handle("down")


def columns(line):
    return sum(2 if settings_ui.unicodedata.east_asian_width(c) in "WF" else 1 for c in line)


class Base(unittest.TestCase):
    def open(self, *args, **kw):
        d = project(*args, **kw)
        self.addCleanup(shutil.rmtree, d, True)
        return settings_ui.Screen.load(d)


class EditByType(Base):
    """Requirement: Edit by type: the cases the stand does not walk."""

    def test_rows(self):
        rows = [  # key, file text, keys after selecting it, value in effect, edited, message part
            ("agents", "agents: claude\n", ["enter", "space", "enter"], ("claude", "file"), False, "agents takes"),
            ("delivery.base", "", ["enter", *"release/1.0", "enter"], ("release/1.0", "file"), True, ""),
            ("delivery.base", "", ["enter", *"my", "space", *"branch", "enter"], ("", "default"), False, "branch names"),
            ("delivery.base", "", ["enter", "a", "\x0c", " ", "\x85", "b", "enter"], ("ab", "file"), True, ""),
            ("delivery.promote", "", ["enter", *"staging,", "space", *"main", "enter"], ("staging, main", "file"),
             True, ""),
            ("dispatch.limit", "dispatch.limit: 4\n", ["enter", "backspace", "enter"], ("2", "default"), True, ""),
            ("delivery.merge", "", ["enter", "down", "esc"], ("squash", "default"), False, ""),
            ("dispatch.limit", "", ["r"], ("2", "default"), False, ""),  # a reset of a key not in the file
            ("delivery.mode", "delivery.mode: local\n", ["enter", "enter"], ("local", "file"), False, ""),
        ]
        for key, text, keys, want, edited, message in rows:
            s = self.open(text)
            select(s, key)
            press(s, *keys)
            self.assertEqual((s.mode, s.values()[key]), ("list", want), (key, keys))
            self.assertIn(message, s.message, (key, keys))
            self.assertEqual(key in s.edits, edited, (key, keys))
            self.assertEqual("*unsaved" in "\n".join(s.draw(120, 40)[0]), edited, (key, keys))
            self.assertEqual(config(s.root), text, "an edit writes nothing before save")

    def test_value_the_file_cannot_hold(self):
        s = self.open("")
        select(s, "delivery.base")
        s.set("a b")
        self.assertEqual(s.edits, {})
        self.assertIn("solo-sdd/config", s.message)
        s.draw(120, 40)  # the screen still draws


class SaveOnlyEditedLines(Base):
    """Requirement: Save only edited lines: the cases the stand does not walk."""

    def test_no_writes_nothing(self):
        s = self.open("dispatch.limit: 2\n")
        select(s, "dispatch.limit")
        press(s, "enter", "backspace", "5", "enter", "s", "n")
        self.assertEqual((s.mode, config(s.root)), ("list", "dispatch.limit: 2\n"))

    def test_long_confirmation_scrolls(self):
        keys = [k for k in settings_ui.KEYS if settings.REGISTRY[k][1] is None and settings.REGISTRY[k][0] == "int"]
        text = "".join("%s: 7\n" % k for k in keys) + "mode: team\nreply.language: en\nrules.scope: global\n"
        text += "delivery.mode: pr\ndelivery.merge: rebase\ndelivery.merge-by: human\nprocess.light-path: off\n"
        s = self.open(text)
        for k in settings_ui.KEYS:
            select(s, k)
            s.handle("r")
        edited = list(s.edits)
        self.assertGreater(len(edited), 6)
        press(s, "s")
        seen = set()
        for _ in edited:
            lines = s.draw(40, 12)[0]
            seen |= {k for k in edited if any(ln.startswith(k + ":") for ln in lines)}
            self.assertIn("Write these %d keys" % len(edited), "\n".join(lines))
            s.handle("down")
        self.assertEqual(seen, set(edited), "every edited key is listed")

    def test_quit_discard_and_save(self):
        s = self.open("")
        select(s, "dispatch.limit")
        press(s, "enter", "backspace", "4", "enter")
        self.assertEqual(press(s, "q", "d"), "exit")
        self.assertEqual(config(s.root), "", "discard writes nothing")
        s = self.open("")
        select(s, "delivery.merge")
        press(s, "enter", "down", "enter")
        self.assertEqual(press(s, "q", "s"), "exit")
        self.assertEqual(config(s.root), "delivery.merge: merge\n", "save and quit")


def sorted_save(screen):
    """A mutant save: rewrites the whole file sorted. The property must reject it."""
    text = screen.edited_text()
    with open(os.path.join(screen.root, settings.SETTINGS_FILE), "w", encoding="utf-8", newline="") as f:
        f.write("".join(ln + "\n" for ln in sorted(text.splitlines())))
    return True


def check_save(save, text, edits):
    """After save every line that is not an edited key keeps its bytes and order; the file parses to the edits."""
    d = project(text)
    try:
        s = settings_ui.Screen.load(d)
        for key, value in edits.items():
            select(s, key)
            if value is None:
                s.handle("r")
            else:
                s.set(value)
        save(s)
        new = config(d)
        keep = [ln for ln in text.splitlines(True) if ln.partition(":")[0].strip() not in edits]
        assert [ln for ln in new.splitlines(True) if ln.partition(":")[0].strip() not in edits] == keep, (text, new)
        found = settings.parse_settings(new)
        assert all(found.get(k) == v for k, v in edits.items()), (edits, new)
    finally:
        shutil.rmtree(d, True)


@st.composite
def edit_sets(draw):
    keys = draw(st.lists(st.sampled_from(sorted(settings.REGISTRY)), unique=True, max_size=5))
    return {k: draw(st.none() | VALUES[k]) for k in keys}


class SaveProperty(unittest.TestCase):
    """Requirement: Save only edited lines (property)."""

    @hsettings(max_examples=200, deadline=None)
    @given(files(), edit_sets())
    @example("", {"dispatch.limit": "3"})
    @example("# only\r\n# comments\n", {"mode": None, "delivery.mode": "pr"})
    def test_save_only_edited_lines(self, text, edits):
        check_save(settings_ui.Screen.save, text, edits)

    def test_sorted_save_fails_the_property(self):
        @hsettings(max_examples=200, deadline=None, database=None)
        @given(files(), edit_sets())
        def mutant(text, edits):
            check_save(sorted_save, text, edits)
        with self.assertRaises(AssertionError):
            mutant()


class Guidance(Base):
    """Requirement: Guidance on the screen: the cases the stand does not walk."""

    def test_same_value_overrides_nothing(self):
        s = self.open("delivery.mode: local\n", agents_md="## Delivery\n\n- Mode: local\n")
        self.assertFalse(any("overrides" in ln for ln in s.draw(160, 40)[0]))

    def test_pr_with_ci_warns_nothing(self):
        s = self.open("", ci=True)
        select(s, "delivery.mode")
        press(s, "enter", "down", "enter")
        self.assertEqual((s.values()["delivery.mode"][0], s.message), ("pr", ""))


class BrokenAndSafeDisplay(Base):
    """Requirements: Broken config read-only; Safe display: the cases the stand does not walk."""

    def test_not_utf8(self):
        d = project()
        self.addCleanup(shutil.rmtree, d, True)
        with open(os.path.join(d, settings.SETTINGS_FILE), "wb") as f:
            f.write(b"mode: \xff\n")
        s = settings_ui.Screen.load(d)
        self.assertEqual((s.mode, s.handle("enter"), s.handle("q")), ("broken", None, "exit"))

    def test_bell_escaped(self):
        s = self.open("delivery.base: main\x07\n")
        text = "\n".join(s.draw(160, 40)[0])
        self.assertIn("main\\x07", text)
        self.assertFalse(any(ord(c) < 32 and c != "\n" for c in text))

    def test_sizes_and_wide_characters(self):
        s = self.open("delivery.base: %s\ndelivery.promote: %s\n" % (
            "中" * 30, ", ".join("branch-%d" % i for i in range(40))))
        for w, h in ((40, 12), (80, 24), (120, 40)):
            select(s, "delivery.base")
            lines, marked = s.draw(w, h)
            self.assertEqual(len(lines), h, (w, h))
            self.assertTrue(all(columns(ln) < w for ln in lines), (w, h))
            select(s, "delivery.promote")
            lines, marked = s.draw(w, h)
            self.assertEqual([lines[i].split()[1] for i in marked], ["delivery.promote"], (w, h))
            self.assertIn("q quit", " ".join(" ".join(lines).split()), "the footer keeps every key at %dx%d" % (w, h))

    def test_long_message_keeps_the_selected_row(self):
        s = self.open("")
        select(s, "delivery.mode")
        press(s, "enter", "down", "enter")  # the CI warning, three lines at 40 columns
        for w, h in ((40, 12), (60, 14)):
            lines, marked = s.draw(w, h)
            self.assertEqual([lines[i].split()[1] for i in marked], ["delivery.mode"], (w, h))
            self.assertTrue(any(ln.endswith(" ...") or "checks" in ln for ln in lines), "the cut is marked")


if __name__ == "__main__":
    unittest.main()
