"""solo_sdd/settings_ui.py: the settings screen model driven by key names.

The stand tests/stands/settings-tui.py proves the scenarios a person walks through on a real terminal; the rows here
are the cases it does not reach.
"""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from hypothesis import example, given, settings as hsettings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import init, settings, settings_ui  # noqa: E402
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
    plain = sorted(k for k in settings.REGISTRY if k not in ("integrations", "integrations.off"))  # through their section
    keys = draw(st.lists(st.sampled_from(plain), unique=True, max_size=5))
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



def integration(base, name, about="a check", rules=True, broken=False):
    """An integration folder <base>/<name> with a description, a material file and a rules.md; broken: no points."""
    d = os.path.join(base, name)
    os.makedirs(d)
    with open(os.path.join(d, "integration"), "w", encoding="utf-8") as f:
        f.write("name: %s\nabout: %s\n%smaterial: m.md\n" % (name, about, "" if broken else "points: review\n"))
    with open(os.path.join(d, "m.md"), "w", encoding="utf-8") as f:
        f.write("# material\n")
    if rules:
        with open(os.path.join(d, "rules.md"), "w", encoding="utf-8") as f:
            f.write("- Rule of %s.\n" % name)


def with_block(d):
    """The project AGENTS.md with the solo-sdd rules block, as init writes it."""
    with contextlib.redirect_stdout(io.StringIO()):
        assert init.project_rules(d, "project", (), create=True) == 0


class Lists(unittest.TestCase):
    """Requirements: Integrations section; Integration keys through the section; Checklists section: the cases the
    stand does not walk."""

    def setUp(self):
        self.home = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.home, True)
        self.owner = os.path.join(self.home, ".local", "share", "solo-sdd", "integrations")

    def open(self, text=""):
        d = project(text)
        self.addCleanup(shutil.rmtree, d, True)
        with_block(d)
        return settings_ui.Screen.load(d, home=self.home)

    def row(self, s, name):
        s.ipos = [e["name"] for e in s.integration_rows()].index(name)

    def test_broken_enabled_switches_off(self):
        """Scenario A broken enabled one off."""
        integration(self.owner, "bad", broken=True)
        s = self.open("integrations: bad\n")
        press(s, "i")
        self.row(s, "bad")
        press(s, "space")
        self.assertEqual(s.toggles, {"bad": False})
        press(s, "space")
        self.assertEqual(s.toggles, {}, "a second press undoes it")
        press(s, "space", "esc", "s", "y")
        self.assertNotIn("integrations", settings.parse_settings(config(s.root)))
        press(s, "i")
        press(s, "space")
        self.assertEqual(s.toggles, {}, "broken and off: it does not switch on")

    def test_shadowed(self):
        integration(self.owner, "twin")
        s = self.open()
        integration(os.path.join(s.root, "solo-sdd", "integrations"), "twin")
        s = settings_ui.Screen.load(s.root, home=self.home)
        press(s, "i")
        s.ipos = next(i for i, e in enumerate(s.integration_rows()) if e["shadowed"])
        press(s, "space")
        self.assertEqual(s.toggles, {})
        self.assertIn("shadowed by the project copy", s.message)

    def test_raw_keys_open_the_section(self):
        s = self.open("integrations.off: antislop\n")
        for key in ("integrations", "integrations.off"):
            select(s, key)
            press(s, "enter")
            self.assertEqual(s.mode, "integrations", key)
            press(s, "esc", "r")
            self.assertEqual(s.edits, {}, "r does not reset %s as text" % key)
            self.assertIn("Integrations section", s.message)

    def test_checklist_refusals(self):
        s = self.open()
        rows = [
            (["a", *"docs", "enter", *"../up/**", "enter"], "relative paths"),
            (["a", *"docs", "enter", "enter"], "takes a value"),
            (["a", *"docs", "enter", *"docs/**", "enter", "esc"], ""),
        ]
        for keys, message in rows:
            press(s, "c", *keys)
            self.assertIn(message, s.message, keys)
            self.assertEqual(s.mode, "checklists", keys)
            press(s, "esc")
        self.assertEqual(s.edits, {}, "Esc at the file step drops the checklist whole")
        for file_keys in (["enter"], [*"../x.md", "enter"]):  # a refused file drops it whole too
            press(s, "c", "a", *"money", "enter", *"billing/**", "enter", *file_keys)
            self.assertEqual((s.edits, s.mode), ({}, "checklists"), file_keys)
            self.assertIn("nothing changed", s.message, file_keys)
            press(s, "esc")
        press(s, "c", "a", *"docs", "enter", *"docs/**", "enter", *"docs/list.md", "enter")
        press(s, "a", *"docs", "enter")
        self.assertIn("checklist docs exists", s.message)
        press(s, "enter", "backspace", "esc")
        self.assertEqual(s.edits["checklist.docs.paths"], "docs/**", "Esc in an edit keeps what was there before")

    def test_listed_name_without_a_folder(self):
        s = self.open("integrations: ghost\n")
        press(s, "i")
        self.row(s, "ghost")
        self.assertIn("no folder", "\n".join(s.draw(120, 40)[0]))
        press(s, "space", "esc", "s", "y")
        self.assertNotIn("integrations", settings.parse_settings(config(s.root)), s.message)

    def test_marks_at_the_smallest_size(self):
        integration(self.owner, "bad", broken=True)
        s = self.open("checklist.docs.paths: docs/**\n")
        press(s, "i")
        self.row(s, "bad")
        self.assertIn("points is required", " ".join(" ".join(s.draw(40, 12)[0]).split()), "the reason of the selected row")
        press(s, "esc", "c")
        self.assertIn("incomplete: no file", " ".join(" ".join(s.draw(40, 12)[0]).split()))


def same_result(save, owner_names, project_names, broken, start, pick):
    """The screen save and the command leave equal bytes of solo-sdd/config and AGENTS.md."""
    home, base = tempfile.mkdtemp(), tempfile.mkdtemp()
    try:
        owner = os.path.join(home, ".local", "share", "solo-sdd", "integrations")
        os.makedirs(owner)
        for n in owner_names:
            integration(owner, n, broken=n in broken)
        copies = []
        for side in ("screen", "command"):
            d = os.path.join(base, side)
            os.makedirs(os.path.join(d, "solo-sdd", "changes"))
            for n in project_names:
                integration(os.path.join(d, "solo-sdd", "integrations"), n, broken=n in broken)
            with open(os.path.join(d, settings.SETTINGS_FILE), "w", encoding="utf-8") as f:
                f.write(start)
            with_block(d)
            copies.append(d)
        s = settings_ui.Screen.load(copies[0], home=home)
        rows = [i for i, e in enumerate(s.integration_rows()) if not e["shadowed"]]  # a shadowed row names its twin
        s.ipos = rows[pick % len(rows)]
        name = s.integration_rows()[s.ipos]["name"]
        action = "disable" if name in s.enabled else "enable"
        press(s, "i", "space", "esc")
        save(s)
        subprocess.run([sys.executable, "-m", "solo_sdd", "integrations", action, name], cwd=copies[1],
                       env=dict(os.environ, PYTHONPATH=REPO, HOME=home), capture_output=True,
                       stdin=subprocess.DEVNULL, timeout=60)
        for f in (settings.SETTINGS_FILE, "AGENTS.md"):
            with open(os.path.join(copies[0], f), "rb") as a, open(os.path.join(copies[1], f), "rb") as b:
                assert a.read() == b.read(), (f, name, action, start)
    finally:
        shutil.rmtree(home, True)
        shutil.rmtree(base, True)


def screen_save(s):
    if s.unsaved:
        press(s, "s", "y")


def space_does_nothing(s):
    """A mutant screen that never switches. The property must reject it."""
    s.toggles.clear()
    screen_save(s)


def save_without_rules(s):
    """A mutant save: switches the integration, then puts the old AGENTS.md back. The property must reject it."""
    with open(os.path.join(s.root, "AGENTS.md"), "rb") as f:
        old = f.read()
    screen_save(s)
    with open(os.path.join(s.root, "AGENTS.md"), "wb") as f:
        f.write(old)


NAMES = st.lists(st.sampled_from(["alpha", "beta", "gamma"]), unique=True, max_size=2)


@st.composite
def setups(draw):
    owner, project = draw(NAMES), draw(NAMES)
    broken = draw(st.lists(st.sampled_from(sorted(set(owner) | set(project)) or ["none"]), unique=True, max_size=1))
    listed = draw(st.lists(st.sampled_from(sorted(set(owner) - set(project)) or ["alpha"]), unique=True, max_size=2))
    off = draw(st.lists(st.sampled_from(["antislop", "security-audit"]), unique=True, max_size=2))
    start = "".join("%s: %s\n" % (k, ", ".join(v)) for k, v in (("integrations", listed), ("integrations.off", off)) if v)
    return owner, project, broken, start, draw(st.integers(0, 6))


class SameResultProperty(unittest.TestCase):
    """Requirement: Same result as the command (property)."""

    @hsettings(max_examples=40, deadline=None)
    @given(setups())
    @example(([], [], [], "", 0))  # no integration besides the bundled ones
    @example((["alpha"], ["beta"], ["beta"], "integrations: alpha\n", 2))  # every one enabled, a broken one
    def test_same_result_as_the_command(self, setup):
        same_result(screen_save, *setup)

    def test_a_screen_that_never_switches_fails_the_property(self):
        @hsettings(max_examples=40, deadline=None, database=None)
        @given(setups())
        def mutant(setup):
            same_result(space_does_nothing, *setup)
        with self.assertRaises(AssertionError):
            mutant()

    def test_save_without_rules_fails_the_property(self):
        @hsettings(max_examples=40, deadline=None, database=None)
        @given(setups())
        @example((["alpha"], [], [], "", 0))
        def mutant(setup):
            same_result(save_without_rules, *setup)
        with self.assertRaises(AssertionError):
            mutant()


if __name__ == "__main__":
    unittest.main()
