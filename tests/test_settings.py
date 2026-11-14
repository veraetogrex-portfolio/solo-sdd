"""solo_sdd/settings.py and `solo-sdd config`: the settings file, defaults by mode, the command, the copies in the scripts."""
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from hypothesis import given, settings as hsettings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import settings  # noqa: E402

# a test registry entry: no registered key takes a list yet
LISTS = dict(settings.REGISTRY, **{"delivery.branches": ("list", None, "main", None)})


class SettingsFile(unittest.TestCase):
    """Requirements: Settings file; Defaults by mode."""

    def test_list_value(self):
        found = settings.parse_settings("delivery.branches: staging,  main\n", LISTS)
        self.assertEqual(settings.effective(found, LISTS)["delivery.branches"], ("staging, main", "file"))

    def test_comments_and_blank_lines(self):
        text = "# a comment\n\n   # indented comment\ndispatch.limit: 3\n"
        self.assertEqual(settings.parse_settings(text), {"dispatch.limit": "3"})

    def test_broken_line(self):
        text = "# c\n\nmode: solo\ndelivery.mode pr\n"
        with self.assertRaisesRegex(settings.SettingsError, r"^solo-sdd/config:4: not \"key: value\""):
            settings.parse_settings(text)

    def test_unknown_key_and_value(self):
        with self.assertRaisesRegex(settings.SettingsError, r"^solo-sdd/config:1: unknown key colour; known: mode, "):
            settings.parse_settings("colour: red\n")
        with self.assertRaisesRegex(settings.SettingsError, r"^solo-sdd/config:2: delivery.mode takes local, pr"):
            settings.parse_settings("mode: team\ndelivery.mode: cloud\n")
        for bad in ("0", "-1", "two", "", "\u00b2", "\u0663"):
            with self.assertRaises(settings.SettingsError, msg=bad):
                settings.parse_settings("dispatch.limit: %s\n" % bad)
        with self.assertRaisesRegex(settings.SettingsError, "set twice"):
            settings.parse_settings("mode: solo\nmode: team\n")

    def test_mode_defaults(self):
        values = settings.effective({})
        self.assertEqual({k: v for k, (v, src) in values.items() if src != "default"}, {})
        self.assertEqual(values["delivery.mode"], ("local", "default"))
        team = settings.effective(settings.parse_settings("mode: team\n"))
        self.assertEqual(team["delivery.mode"], ("pr", "mode"))
        self.assertEqual(team["delivery.merge"], ("squash", "default"))

    def test_file_wins(self):
        values = settings.effective(settings.parse_settings("mode: team\ndelivery.mode: local\n"))
        self.assertEqual(values["delivery.mode"], ("local", "file"))

    def test_registry_shape(self):
        for key, (kind, allowed, default, team) in settings.REGISTRY.items():
            self.assertIn(kind, ("choice", "int", "list", "names"), key)
            self.assertEqual(settings.check_value(key, default), default, key)
            if team is not None:
                self.assertEqual(settings.check_value(key, team), team, key)

    def test_integrations_names(self):
        """Requirement: Explicit enablement: the integrations key takes integration names."""
        self.assertEqual(settings.effective({})["integrations"], ("", "default"))
        self.assertEqual(settings.parse_settings("integrations: dup-scan,marker-check \n"),
                         {"integrations": "dup-scan, marker-check"})
        self.assertEqual(settings.parse_settings("integrations:\n"), {"integrations": ""})
        for bad in ("Marker", "-x", "a_b", "a b", "../x", "x, x"):
            with self.assertRaisesRegex(settings.SettingsError, "integrations takes", msg=bad):
                settings.check_value("integrations", bad)

    def test_delivery_branches(self):
        """Requirement: Base branch from settings: delivery.base and delivery.promote."""
        self.assertEqual(settings.effective({})["delivery.base"], ("", "default"))
        self.assertEqual(settings.effective({})["delivery.promote"], ("", "default"))
        found = settings.parse_settings("delivery.base: dev\ndelivery.promote: staging,release/* , main\n")
        self.assertEqual(found, {"delivery.base": "dev", "delivery.promote": "staging, release/*, main"})
        self.assertEqual(settings.parse_settings("delivery.base:\n"), {"delivery.base": ""})
        self.assertEqual(settings.check_value("delivery.base", "feature/x-1.2_y"), "feature/x-1.2_y")
        for key, bad in (("delivery.base", "-c x"), ("delivery.base", "--upload-pack=x"), ("delivery.base", "a b"),
                         ("delivery.base", "+dev"), ("delivery.base", "a:b"), ("delivery.base", "dev..x"),
                         ("delivery.base", "dev~1"), ("delivery.base", "d\\x"),
                         ("delivery.promote", "staging, -main"), ("delivery.promote", "a b, main")):
            with self.assertRaisesRegex(settings.SettingsError, r"branch names \(no spaces", msg=bad):
                settings.check_value(key, bad)
        with self.assertRaisesRegex(settings.SettingsError, r"^mode takes solo, team, not ''"):
            settings.check_value("mode", "")

    def test_merge_by(self):
        """Requirement: Human merge mode: delivery.merge-by is agent alone, human in a team, the file wins."""
        self.assertEqual(settings.effective({})["delivery.merge-by"], ("agent", "default"))
        self.assertEqual(settings.effective(settings.parse_settings("mode: team\n"))["delivery.merge-by"], ("human", "mode"))
        found = settings.parse_settings("mode: team\ndelivery.merge-by: agent\n")
        self.assertEqual(settings.effective(found)["delivery.merge-by"], ("agent", "file"))
        with self.assertRaisesRegex(settings.SettingsError, r"delivery.merge-by takes agent, human, not 'bot'"):
            settings.check_value("delivery.merge-by", "bot")

    def test_light_path(self):
        """Requirement: Light path bounds: on and 3 files by default, off and the file limit from the file."""
        values = settings.effective({})
        self.assertEqual(values["process.light-path"], ("on", "default"))
        self.assertEqual(values["process.light-path.max-files"], ("3", "default"))
        found = settings.parse_settings("process.light-path: off\nprocess.light-path.max-files: 5\n")
        self.assertEqual(found, {"process.light-path": "off", "process.light-path.max-files": "5"})
        with self.assertRaisesRegex(settings.SettingsError, r"process.light-path takes on, off, not 'maybe'"):
            settings.check_value("process.light-path", "maybe")
        with self.assertRaises(settings.SettingsError):
            settings.check_value("process.light-path.max-files", "0")
        text = settings.set_text("process.light-path.max-files: 2\n", "process.light-path", "off")
        self.assertEqual(settings.parse_settings(text), {"process.light-path.max-files": "2", "process.light-path": "off"})

    def test_checklist_pattern_keys(self):
        """Requirement: Path checklists: checklist.<name>.paths (globs) and checklist.<name>.file as pattern keys."""
        found = settings.parse_settings("checklist.money-safety.paths: billing/**, src/pay/*.py\n"
                                        "checklist.money-safety.file: docs/checklists/money-safety.md\n")
        self.assertEqual(found, {"checklist.money-safety.paths": "billing/**, src/pay/*.py",
                                 "checklist.money-safety.file": "docs/checklists/money-safety.md"})
        values = settings.effective(found)
        self.assertEqual(values["checklist.money-safety.paths"], ("billing/**, src/pay/*.py", "file"))
        self.assertNotIn("checklist.money-safety.paths", settings.effective({}), "an unset pattern key is not listed")
        # a missing file key is not a parse error: config set writes one key at a time (sdd-pr.py refuses the half)
        self.assertEqual(settings.parse_settings("checklist.a.paths: x/**\n"), {"checklist.a.paths": "x/**"})
        for bad in ("/etc/**", "../x", "a/../b", "a b", "a\\b", "-x"):
            with self.assertRaisesRegex(settings.SettingsError, r"relative paths \(no spaces", msg=bad):
                settings.check_value("checklist.a.paths", "billing/**, " + bad)
        with self.assertRaisesRegex(settings.SettingsError, r"checklist.a.file takes relative paths"):
            settings.check_value("checklist.a.file", "/abs.md")
        for key in ("checklist.Money.paths", "checklist.a_b.paths", "checklist.-a.paths", "checklist..paths",
                    "checklist.a.b.paths", "checklist.paths", "checklist.a.items", "checklists.a.paths"):
            with self.assertRaisesRegex(settings.SettingsError, r"unknown key .*checklist.<name>.paths", msg=key):
                settings.parse_settings(key + ": x\n")

    def test_copies_match(self):
        # Requirement: Tests use the block check (shared-blocks)
        r = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "sync_blocks.py"), "--check"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class KeyDescriptions(unittest.TestCase):
    """Requirement: Key descriptions."""

    def test_every_key_described(self):
        keys = list(settings.REGISTRY) + list(settings.PATTERNS)
        self.assertEqual([k for k in keys if k not in settings.ABOUT], [], "a key without a group and description")
        self.assertEqual([k for k in settings.ABOUT if k not in keys], [], "a description of no key")
        for key, (group, about) in settings.ABOUT.items():
            self.assertIn(group, settings.GROUPS, key)
            self.assertTrue(about[:1].isupper() and about.endswith(".") and about.count(". ") == 0
                            and "\n" not in about, key)


class Readme(unittest.TestCase):
    """docs/settings.md: one table row per registered key, with its values and defaults."""

    def test_rows_match_the_registry(self):
        with open(os.path.join(REPO, "docs", "settings.md"), encoding="utf-8") as f:
            body = f.read().split("\n## Checklists\n", 1)[0]
        rows = {}
        for line in body.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if line.startswith("| `") and len(cells) >= 4:
                rows[cells[0].strip("`")] = tuple(re.findall(r"`([^`]+)`", c) for c in cells[1:4])
        want = {key: (list(allowed or ()), [default] if default else [], [team] if team else [])
                for key, (_, allowed, default, team) in settings.REGISTRY.items()}
        want["agents"] = (want["agents"][0], [], [])  # the default is the detected agents, not a fixed value
        self.assertEqual(rows, want)
        self.assertIn("| `agents` | `claude`, `codex`, `cursor`, `other` | the detected agents |", body)

    def test_checklist_example_parses(self):
        """Requirement: Path checklists: the docs/settings.md example config is valid settings."""
        with open(os.path.join(REPO, "docs", "settings.md"), encoding="utf-8") as f:
            body = f.read().split("\n## Checklists\n", 1)[1]
        example = body.split("```\n")[1]
        found = settings.parse_settings(example)
        self.assertEqual(sorted(found), ["checklist.money-safety.file", "checklist.money-safety.paths"])


class Command(unittest.TestCase):
    """Requirement: Config command."""

    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir, True)
        os.makedirs(os.path.join(self.dir, "solo-sdd", "changes"))
        self.cfg = os.path.join(self.dir, "solo-sdd", "config")

    def cli(self, *args):
        r = subprocess.run([sys.executable, "-m", "solo_sdd", "config", *args], cwd=self.dir, capture_output=True,
                           text=True, env=dict(os.environ, PYTHONPATH=REPO), stdin=subprocess.DEVNULL, timeout=60)
        return r.returncode, r.stdout

    def write(self, text):
        with open(self.cfg, "w", encoding="utf-8", newline="") as f:
            f.write(text)

    def read(self):
        with open(self.cfg, encoding="utf-8", newline="") as f:
            return f.read()

    def test_list_sources(self):
        code, out = self.cli("list")
        self.assertEqual(code, 0)
        self.assertEqual(out.splitlines(), ["%s %s default" % (k, v[2]) for k, v in settings.REGISTRY.items()])
        self.assertFalse(os.path.exists(self.cfg), "list writes nothing")
        self.write("mode: team\ndispatch.limit: 4\n")
        lines = self.cli("list")[1].splitlines()
        self.assertIn("mode team file", lines)
        self.assertIn("delivery.mode pr mode", lines)
        self.assertIn("dispatch.limit 4 file", lines)
        self.assertIn("delivery.merge squash default", lines)
        self.assertEqual(self.cli("get", "delivery.mode"), (0, "pr\n"))

    def test_delivery_section_kept(self):
        """Requirement: Defaults by mode, scenario Delivery section kept; Config command, scenario Get names the source."""
        with open(os.path.join(self.dir, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("# p\n\n- Mode: local\n\n## Delivery\n\n- Mode: `PR`.\n- Mode: local\n- Merge: cloud\n\n## Next\n\n- Merge: rebase\n")
        lines = self.cli("list")[1].splitlines()
        self.assertIn("delivery.mode pr AGENTS.md", lines)
        self.assertIn("delivery.merge squash default", lines, "a value outside the allowed ones and other sections are skipped")
        r = subprocess.run([sys.executable, "-m", "solo_sdd", "config", "get", "delivery.mode"], cwd=self.dir,
                           capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=REPO),
                           stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "pr\n", "source: AGENTS.md\n"))
        self.write("mode: team\ndelivery.mode: local\n")
        self.assertIn("delivery.mode local file", self.cli("list")[1].splitlines(), "the file wins")
        self.write("mode: team\n")
        with open(os.path.join(self.dir, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("## Delivery\n\n- Mode: local\n")
        self.assertIn("delivery.mode local AGENTS.md", self.cli("list")[1].splitlines(), "before the team default")
        self.assertEqual(self.cli("unset", "mode"), (0, "mode: removed, in effect solo\n"))
        self.write("delivery.mode: pr\n")
        self.assertEqual(self.cli("unset", "delivery.mode"), (0, "delivery.mode: removed, in effect local\n"))
        with open(os.path.join(self.dir, "AGENTS.md"), "wb") as f:
            f.write(b"\xff\xfe\n## Delivery\n\n- Mode: pr \x80\n")
        self.assertIn("delivery.mode pr AGENTS.md", self.cli("list")[1].splitlines(), "bytes that are not UTF-8")

    def test_set_keeps_other_bytes(self):
        self.write("# my settings\r\nmode: solo   \r\ndispatch.limit: 2\r\n")
        self.assertEqual(self.cli("set", "dispatch.limit", "3")[0], 0)
        self.assertEqual(self.read(), "# my settings\r\nmode: solo   \r\ndispatch.limit: 3\r\n")
        self.assertEqual(self.cli("set", "delivery.merge", "rebase")[0], 0)
        self.assertEqual(self.read(), "# my settings\r\nmode: solo   \r\ndispatch.limit: 3\r\ndelivery.merge: rebase\r\n")
        self.assertEqual(self.cli("unset", "dispatch.limit"), (0, "dispatch.limit: removed, in effect 2\n"))
        self.assertEqual(self.read(), "# my settings\r\nmode: solo   \r\ndelivery.merge: rebase\r\n")

    def test_set_creates_the_file(self):
        self.assertEqual(self.cli("set", "mode", "team"), (0, "mode: team\n"))
        self.assertEqual(self.read(), "mode: team\n")

    def test_wrong_key_or_value_refused(self):
        self.write("# keep\nmode: solo\n")
        code, out = self.cli("set", "delivery.mode", "cloud")
        self.assertEqual(code, 1)
        self.assertIn("local, pr", out)
        code, out = self.cli("set", "colour", "red")
        self.assertEqual(code, 1)
        self.assertIn("known: mode, delivery.mode", out)
        self.assertEqual(self.cli("get", "colour")[0], 1)
        self.assertEqual(self.cli("unset", "colour")[0], 1)
        self.assertEqual(self.read(), "# keep\nmode: solo\n")

    def test_broken_file_named(self):
        self.write("# c\n\nmode: solo\ndelivery.mode pr\n")
        for args in (("list",), ("get", "mode"), ("set", "mode", "team")):
            code, out = self.cli(*args)
            self.assertEqual(code, 1, args)
            self.assertIn("solo-sdd/config:4", out, args)
        self.assertEqual(self.read(), "# c\n\nmode: solo\ndelivery.mode pr\n")

    def test_list_value_through_the_command(self):
        self.write("delivery.branches: staging,main\n")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = settings.run(["get", "delivery.branches"], self.dir, LISTS)
        self.assertEqual((code, buf.getvalue()), (0, "staging, main\n"))

    def test_checklist_keys_through_the_command(self):
        """Requirement: Path checklists: set, get, list and unset of a pattern key."""
        self.assertEqual(self.cli("get", "checklist.money.paths"), (0, "\n"))
        self.assertEqual(self.cli("set", "checklist.money.paths", "billing/**"), (0, "checklist.money.paths: billing/**\n"))
        self.assertEqual(self.cli("set", "checklist.money.file", "docs/money.md")[0], 0)
        lines = self.cli("list")[1].splitlines()
        self.assertEqual(lines[-2:], ["checklist.money.paths billing/** file", "checklist.money.file docs/money.md file"])
        self.assertEqual(self.cli("get", "checklist.money.paths"), (0, "billing/**\n"))
        self.assertEqual(self.cli("unset", "checklist.money.paths"), (0, "checklist.money.paths: removed, in effect \n"))
        code, out = self.cli("set", "checklist.Money.paths", "x")
        self.assertEqual(code, 1)
        self.assertIn("unknown key checklist.Money.paths", out)

    def test_non_ascii_digits_refused(self):
        code, out = self.cli("set", "dispatch.limit", "\u00b2")
        self.assertEqual((code, out), (1, "dispatch.limit takes a whole number from 1, not '\u00b2'\n"))
        self.write("dispatch.limit: \u00b2\n")
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertIn("solo-sdd/config:1: dispatch.limit takes a whole number", out)

    def test_outside_a_tree(self):
        shutil.rmtree(os.path.join(self.dir, "solo-sdd"))
        self.assertEqual(self.cli("list"), (1, "no solo-sdd/ tree\n"))

    def describe(self, *args):
        """The blocks of `config describe` as {key: {field: value}}; a block is the key line, then `  field: value`."""
        code, out = self.cli("describe", *args)
        blocks, key = {}, None
        for ln in out.splitlines():
            if ln and not ln.startswith(" "):
                key = ln
                blocks[key] = {}
            elif ln.strip():
                field, _, value = ln.strip().partition(": ")
                blocks[key][field] = value
        return code, blocks

    def test_describe_one_key(self):
        """Requirement: Describe a setting, scenario One key."""
        code, blocks = self.describe("delivery.mode")
        self.assertEqual(code, 0)
        self.assertEqual(blocks, {"delivery.mode": {
            "group": "delivery", "about": settings.ABOUT["delivery.mode"][1], "type": "choice: local, pr",
            "default": "local", "team default": "pr", "value": "local (default)"}})
        self.assertEqual(self.describe("delivery.base")[1]["delivery.base"]["value"], "(none) (default)")

    def test_describe_all_keys_then_patterns(self):
        """Requirement: Describe a setting, scenario Pattern keys."""
        self.write("checklist.money.paths: billing/**\n")
        code, blocks = self.describe()
        self.assertEqual(code, 0)
        want = list(settings.REGISTRY) + list(settings.PATTERNS) + ["checklist.money.paths"]
        self.assertEqual(list(blocks), want)
        self.assertEqual(blocks["checklist.<name>.paths"]["about"], settings.ABOUT["checklist.<name>.paths"][1])
        self.assertNotIn("value", blocks["checklist.<name>.paths"], "a pattern has no value of its own")
        self.assertEqual(blocks["checklist.money.paths"]["value"], "billing/** (file)")
        self.assertEqual(self.describe("checklist.money.file")[1]["checklist.money.file"]["value"], "(none) (default)")
        code, blocks = self.describe("checklist.<name>.paths")
        self.assertEqual((code, list(blocks)), (0, ["checklist.<name>.paths"]))
        self.assertNotIn("value", blocks["checklist.<name>.paths"])

    def test_list_json(self):
        """Requirement: Describe a setting, scenario JSON list; plain `config list` keeps its output."""
        import json
        plain = self.cli("list")
        code, out = self.cli("list", "--json")
        self.assertEqual(code, 0)
        rows = json.loads(out)
        self.assertEqual([r["key"] for r in rows], list(settings.REGISTRY))
        fields = ["key", "group", "about", "type", "allowed", "default", "team_default", "value", "source"]
        self.assertTrue(all(set(r) == set(fields) for r in rows))
        mode = rows[list(settings.REGISTRY).index("delivery.mode")]
        self.assertEqual((mode["allowed"], mode["default"], mode["team_default"], mode["value"], mode["source"]),
                         (["local", "pr"], "local", "pr", "local", "default"))
        self.assertIsNone(rows[list(settings.REGISTRY).index("dispatch.limit")]["allowed"])
        self.assertEqual(self.cli("list"), plain)
        for args in (["list", "--json"], ["describe"], ["describe", "delivery.branches"]):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(settings.run(args, self.dir, LISTS), 0, args)
            self.assertIn("delivery.branches", out.getvalue(), "a registry passed to run: %s" % args)

    def test_describe_refusals(self):
        """Requirement: Describe a setting, scenarios Unknown key and A broken file."""
        code, out = self.cli("describe", "delivery.color")
        self.assertEqual(code, 1)
        self.assertIn("unknown key delivery.color; known: mode, ", out)
        self.write("mode: solo\n\n# c\ndelivery.mode pr\n")
        for args in (("describe",), ("describe", "mode"), ("list", "--json")):
            code, out = self.cli(*args)
            self.assertEqual(code, 1, args)
            self.assertIn("solo-sdd/config:4", out, args)

    def test_bad_arguments_print_usage(self):
        r = subprocess.run([sys.executable, "-m", "solo_sdd", "config", "get"], cwd=self.dir, capture_output=True,
                           text=True, env=dict(os.environ, PYTHONPATH=REPO), stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(r.returncode, 2)
        self.assertIn("config list|get", r.stdout)


VALUES = {k: st.sampled_from(v[1]) if v[1] else st.integers(1, 99).map(str) for k, v in settings.REGISTRY.items()}
COMMENT = st.text(st.characters(blacklist_categories=("Cs", "Cc", "Zl", "Zp")), max_size=12).map(lambda s: "# " + s)


@st.composite
def files(draw):
    """A file of comments, blank lines and some registered keys in any order; each line ends with \\n or \\r\\n."""
    keys = draw(st.lists(st.sampled_from(sorted(settings.REGISTRY)), unique=True))
    lines = ["%s: %s" % (k, draw(VALUES[k])) for k in keys]
    lines += draw(st.lists(COMMENT | st.just(""), max_size=4))
    lines = draw(st.permutations(lines))
    return "".join(ln + draw(st.sampled_from(["\n", "\r\n"])) for ln in lines)


def sorted_rewrite(text, key, value):
    """A mutant of set_text: rewrites the whole file sorted. The property must reject it."""
    lines = [ln for ln in text.splitlines() if not (ln.strip() and ln.partition(":")[0].strip() == key)]
    return "".join(ln + "\n" for ln in sorted(lines + ([] if value is None else ["%s: %s" % (key, value)])))


def check_config_command(set_text, text, key, value):
    """set then get returns the value; every other line keeps its bytes and order; unset of a new key restores the file."""
    new = set_text(text, key, value)
    assert settings.effective(settings.parse_settings(new))[key] == (value, "file"), new
    others = [ln for ln in text.splitlines(True) if ln.partition(":")[0].strip() != key]
    assert [ln for ln in new.splitlines(True) if ln.partition(":")[0].strip() != key] == others, (text, new)
    if key not in settings.parse_settings(text):
        assert set_text(new, key, None) == text, (text, new)


class ConfigCommandProperty(unittest.TestCase):
    """Requirement: Config command (property)."""

    @hsettings(max_examples=300, deadline=None)
    @given(files(), st.sampled_from(sorted(settings.REGISTRY)), st.data())
    def test_config_command_property(self, text, key, data):
        check_config_command(settings.set_text, text, key, data.draw(VALUES[key]))

    def test_sorted_rewrite_fails_the_property(self):
        @hsettings(max_examples=300, deadline=None, database=None)
        @given(files(), st.sampled_from(sorted(settings.REGISTRY)), st.data())
        def mutant(text, key, data):
            check_config_command(sorted_rewrite, text, key, data.draw(VALUES[key]))
        with self.assertRaises(AssertionError):
            mutant()


if __name__ == "__main__":
    unittest.main()
