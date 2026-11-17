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
            self.assertIn(kind, ("choice", "exts", "int", "ints", "lang", "list", "model", "names", "paths", "text"), key)
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

    def test_ci_wait_merge_gate_pr_shape_keys(self):
        """Requirement: CI wait settings, Merge gate settings, PR shape settings: the seven delivery keys."""
        want = {"delivery.ci-timeout": ("int", None, "1200"), "delivery.ci-stuck": ("int", None, "300"),
                "delivery.ci-no-checks": ("int", None, "180"), "delivery.require-ci": ("choice", ("on", "off"), "on"),
                "delivery.code-scanning": ("choice", ("gate", "warn", "off"), "gate"),
                "delivery.delete-branch": ("choice", ("on", "off"), "on"), "delivery.draft": ("choice", ("on", "off"), "off")}
        for key, (kind, allowed, default) in want.items():
            self.assertEqual(settings.REGISTRY.get(key), (kind, allowed, default, None), key)
            self.assertEqual(settings.describe(key, {})["group"], "delivery", key)
            self.assertEqual(settings.effective({})[key], (default, "default"), key)
        found = settings.parse_settings("delivery.ci-timeout: 3600\ndelivery.code-scanning: warn\n")
        self.assertEqual(settings.effective(found)["delivery.ci-timeout"], ("3600", "file"))
        with self.assertRaisesRegex(settings.SettingsError, r"delivery.code-scanning takes gate, warn, off, not 'on'"):
            settings.check_value("delivery.code-scanning", "on")
        with self.assertRaisesRegex(settings.SettingsError, r"delivery.ci-stuck takes a whole number from 1"):
            settings.check_value("delivery.ci-stuck", "0")

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


class SubagentModelSettings(unittest.TestCase):
    """Requirements: Subagent model settings and Executor setting from the owner: the six keys of group agents."""
    KEYS = {"agents.orchestrator-model": ("model", None, "opus"), "agents.review-model": ("model", None, ""),
            "agents.lookup-model": ("model", None, "haiku"), "agents.test-model": ("model", None, "haiku"),
            "agents.dispatcher-effort": ("choice", ("low", "medium", "high"), "low"),
            "agents.executor": ("choice", ("self", "codex"), "self")}

    def test_the_six_keys(self):
        for key, (kind, allowed, default) in self.KEYS.items():
            self.assertEqual(settings.REGISTRY.get(key), (kind, allowed, default, None), key)
            self.assertEqual(settings.describe(key, {})["group"], "agents", key)
            self.assertEqual(settings.effective({})[key], (default, "default"), key)
        with self.assertRaisesRegex(settings.SettingsError, r"agents.executor takes self, codex, not 'claude'"):
            settings.check_value("agents.executor", "claude")

    def test_model_names(self):
        for name in ("fable", "claude-opus-4.5", "opus[1m]", "gpt_5.1-mini"):
            self.assertEqual(settings.check_value("agents.lookup-model", " %s " % name), name)
        for bad in ("haiku 4", "a:b", "opus,haiku", "x/y", "caf\u00e9", ""):
            with self.assertRaisesRegex(settings.SettingsError, r"^agents.lookup-model takes one model name of ASCII "
                                        r"letters, digits, \., -, _, \[ and \], not ", msg=bad):
                settings.check_value("agents.lookup-model", bad)
        self.assertEqual(settings.check_value("agents.review-model", ""), "", "empty: the session's main model")


class ChangeLimitSettings(unittest.TestCase):
    """Requirements: Change size limits and Process cadence settings: the five keys of group process."""
    KEYS = {"process.max-tasks": ("int", None, "10"), "process.bugfix-max-tasks": ("int", None, "5"),
            "process.requirement-max-chars": ("int", None, "500"), "process.audit-every": ("int", None, "5"),
            "process.analyze": ("choice", ("on", "off"), "on")}

    def test_the_five_keys(self):
        for key, (kind, allowed, default) in self.KEYS.items():
            self.assertEqual(settings.REGISTRY.get(key), (kind, allowed, default, None), key)
            self.assertEqual(settings.describe(key, {})["group"], "process", key)
            self.assertEqual(settings.effective({})[key], (default, "default"), key)

    def test_lower_bounds(self):
        # the command refuses process.max-tasks 2 and process.requirement-max-chars 99 (ChangeLimitCommand)
        for key, low in (("process.bugfix-max-tasks", 3), ("process.audit-every", 1)):
            self.assertEqual(settings.check_value(key, str(low)), str(low), key)
            with self.assertRaisesRegex(settings.SettingsError, r"^%s takes a whole number from %d, not '%d'"
                                        % (re.escape(key), low, low - 1), msg=key):
                settings.check_value(key, str(low - 1))
        for key, low in (("process.max-tasks", 3), ("process.bugfix-max-tasks", 3),
                         ("process.requirement-max-chars", 100), ("process.audit-every", 1)):
            self.assertIn("a whole number from %d" % low, settings.describe(key, {})["type"], key)


class StopGateSwitchesAndInterfaceSettings(unittest.TestCase):
    """Requirements: Stop gate switches and Interface settings: the seven keys of groups hooks and ui."""
    UI_DEFAULT = ".html, .htm, .css, .scss, .sass, .less, .tsx, .jsx, .vue, .svelte"
    KEYS = dict({k: ("choice", ("on", "off"), "on", "hooks") for k in (
        "hooks.stop.uncommitted", "hooks.stop.unarchived", "hooks.stop.open-pr", "hooks.stop.ui-check",
        "hooks.auto-claim")}, **{"ui.extensions": ("exts", None, UI_DEFAULT, "ui"), "ui.widths": ("ints", None, "1280, 390", "ui")})

    def test_the_seven_keys(self):
        for key, (kind, allowed, default, group) in self.KEYS.items():
            self.assertEqual(settings.REGISTRY.get(key), (kind, allowed, default, None), key)
            self.assertEqual(settings.describe(key, {})["group"], group, key)
            self.assertEqual(settings.effective({})[key], (default, "default"), key)
        self.assertIn("extensions", settings.describe("ui.extensions", {})["type"])
        self.assertIn("whole numbers from 1", settings.describe("ui.widths", {})["type"])

    def test_values(self):
        self.assertEqual(settings.check_value("ui.extensions", " .html,.Jinja2 "), ".html, .Jinja2")
        self.assertEqual(settings.check_value("ui.widths", "1440, 0390"), "1440, 390")
        # html, .a b and 1280, wide: InterfaceSettingsCommand
        for key, bad, why in (("ui.extensions", ".a.b", "extensions"), ("ui.extensions", ".", "extensions"),
                              ("ui.extensions", "", "extensions"),
                              ("ui.widths", "0", "whole numbers"), ("ui.widths", "²", "whole numbers"),
                              ("ui.widths", "", "whole numbers"), ("hooks.auto-claim", "no", "on, off")):
            with self.assertRaisesRegex(settings.SettingsError, "^%s takes .*%s" % (re.escape(key), why), msg=bad):
                settings.check_value(key, bad)


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
        self.assertIn("process.review-rounds 5 default", lines, "Requirement: Review rounds: default 5")

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

    def test_model_name_refused(self):
        """Requirement: Subagent model settings: a model name with a space, and the defaults in config list."""
        self.write("# keep\nagents.orchestrator-model: fable\n")
        code, out = self.cli("set", "agents.lookup-model", "haiku 4")
        self.assertEqual(code, 1)
        self.assertIn("one model name of ASCII letters, digits, ., -, _, [ and ]", out)
        self.assertEqual(self.read(), "# keep\nagents.orchestrator-model: fable\n")
        os.remove(self.cfg)
        lines = self.cli("list")[1].splitlines()
        self.assertIn("agents.orchestrator-model opus default", lines)
        self.assertIn("agents.dispatcher-effort low default", lines)

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

    def test_local_merge_method(self):
        """Requirement: Local merge method, scenario The default keeps today."""
        r = subprocess.run([sys.executable, "-m", "solo_sdd", "config", "get", "delivery.local-merge"], cwd=self.dir,
                           capture_output=True, text=True, env=dict(os.environ, PYTHONPATH=REPO),
                           stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "merge\n", "source: default\n"))
        self.assertEqual(self.describe("delivery.local-merge")[1]["delivery.local-merge"]["type"], "choice: merge, squash, rebase")
        about = self.describe("delivery.merge")[1]["delivery.merge"]["about"]
        self.assertIn("delivery.local-merge", about)
        self.assertNotIn("local change", about)

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


class ConfigDir(unittest.TestCase):
    """A project folder and the command helpers of Command, without its tests."""
    setUp, cli, write, read, describe = Command.setUp, Command.cli, Command.write, Command.read, Command.describe

    def get(self, key):
        """(code, stdout, stderr) of `config get <key>` run in this process."""
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = settings.run(["get", key], self.dir)
        return code, out.getvalue(), err.getvalue()


class TextSettings(ConfigDir):
    """Requirement: Text settings."""

    def test_ends_trimmed(self):
        # the stand proves A title rule with spaces and the describe line; here only the trimmed ends
        self.assertEqual(self.cli("set", "delivery.pr-title", "  <id>: <summary>  "),
                         (0, "delivery.pr-title: <id>: <summary>\n"))
        self.assertEqual(self.read(), "delivery.pr-title: <id>: <summary>\n")

    def test_refusals_keep_the_file(self):
        self.write("# keep\ndelivery.deploy: no\n")
        for bad, why in (("x" * 201, "at most 200 characters"), ("a\nb", "one line"), ("a\x07b", "one line"),
                         ("a\tb", "one line"), ("", "one line")):
            code, out = self.cli("set", "delivery.deploy", bad)
            self.assertEqual(code, 1, repr(bad))
            self.assertIn(why, out, repr(bad))
        self.assertEqual(self.read(), "# keep\ndelivery.deploy: no\n")
        self.assertEqual(self.cli("set", "delivery.deploy", "y" * 200)[0], 0, "200 characters fit")
        self.write("delivery.deploy: %s\n" % ("z" * 201))
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertIn("solo-sdd/config:1: delivery.deploy takes", out)


class ChangeLimitCommand(ConfigDir):
    """Requirement: Change size limits, scenario A limit no change can meet."""

    def test_a_limit_no_change_can_meet(self):
        self.write("# keep\nprocess.max-tasks: 12\n")
        for key, value, low in (("process.max-tasks", "2", "3"), ("process.requirement-max-chars", "99", "100")):
            code, out = self.cli("set", key, value)
            self.assertEqual(code, 1, key)
            self.assertIn("from %s" % low, out, key)
        self.assertEqual(self.read(), "# keep\nprocess.max-tasks: 12\n")


class InterfaceSettingsCommand(ConfigDir):
    """Requirement: Interface settings, scenario A width that is not a number; the describe lines of both keys."""

    def test_refused_values_keep_the_file(self):
        self.write("# keep\nui.widths: 1440\n")
        for key, bad, why in (("ui.widths", "1280, wide", "whole numbers"), ("ui.extensions", "html", "extensions"),
                              ("ui.extensions", ".a b", "extensions")):
            code, out = self.cli("set", key, bad)
            self.assertEqual(code, 1, bad)
            self.assertIn(why, out, bad)
            self.assertIn(repr(bad), out, bad)
        self.assertEqual(self.read(), "# keep\nui.widths: 1440\n")
        code, blocks = self.describe("ui.extensions")
        self.assertEqual((code, blocks["ui.extensions"]["group"]), (0, "ui"))
        self.assertIn("extensions", blocks["ui.extensions"]["type"])
        self.assertIn("whole numbers", self.describe("ui.widths")[1]["ui.widths"]["type"])
        self.assertEqual(self.cli("set", "ui.extensions", ".html, .jinja"), (0, "ui.extensions: .html, .jinja\n"))


class DeliveryItemsInConfig(ConfigDir):
    """Requirements: Delivery items in config; Defaults by mode (the key's old source)."""

    def agents(self, *items):
        with open(os.path.join(self.dir, "AGENTS.md"), "w", encoding="utf-8") as f:
            f.write("# p\n\n- Deploy: outside\n\n## Delivery\n\n" + "".join("- %s\n" % x for x in items)
                    + "\n## Other\n\n- Owner only: `x/**`\n- PR title: other\n")

    def test_the_old_items(self):
        self.agents("Mode: pr", "PR title:   <id>: <what>  ", "Deploy: no", "Owner only: `global/work_hooks.py`, `docs/**`",
                    "Owner only: `deploy/`")
        self.assertEqual(self.get("delivery.owner-only"),
                         (0, "global/work_hooks.py, docs/**, deploy/\n", "source: AGENTS.md\n"))
        self.assertEqual(self.get("delivery.pr-title"), (0, "<id>: <what>\n", "source: AGENTS.md\n"))
        self.assertEqual(self.get("delivery.deploy"), (0, "no\n", "source: AGENTS.md\n"))
        self.assertIn("delivery.mode pr AGENTS.md", self.cli("list")[1].splitlines())

    def test_defaults_without_items(self):
        self.agents("Mode: pr", "Owner only: no paths here")
        lines = self.cli("list")[1].splitlines()
        for want in ("delivery.pr-title the change name default", "delivery.deploy no default",
                     "delivery.owner-only  default"):
            self.assertIn(want, lines)

    def test_the_file_wins(self):
        self.agents("Deploy: no", "Owner only: `docs/**`")
        self.write("delivery.deploy: on merge into main, Cloudflare Pages\ndelivery.owner-only: deploy/**\n")
        self.assertEqual(self.get("delivery.deploy"), (0, "on merge into main, Cloudflare Pages\n", "source: file\n"))
        self.assertEqual(self.get("delivery.owner-only"), (0, "deploy/**\n", "source: file\n"))

    def test_a_long_old_item(self):
        item = "on merge `main` -> Pages " + "x" * 215
        self.assertEqual(len(item), 240)
        self.agents("Deploy: " + item)
        self.assertEqual(self.get("delivery.deploy"), (0, item + "\n", "source: AGENTS.md\n"))


class ProjectRulesInConfig(ConfigDir):
    """Requirements: Project rules in config; Project lines as the old source; Config command (source project.md)."""
    KEYS = {"project.stage": ("choice", ("demo", "prod"), ""), "artifacts.language": ("lang", None, "en"),
            "lessons.write": ("choice", ("on", "off"), "on"), "lessons.max-lines": ("int", None, "20")}

    def project(self, *lines):
        with open(os.path.join(self.dir, "solo-sdd", "project.md"), "w", encoding="utf-8") as f:
            f.write("# Project\n\n" + "".join(ln + "\n" for ln in lines) + "\nIntent: a tool. Mode: prose, no line.\n")

    def run_err(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = settings.run(list(args), self.dir)
        return code, err.getvalue()

    def test_the_four_keys(self):
        for key, (kind, allowed, default) in self.KEYS.items():
            self.assertEqual(settings.REGISTRY.get(key), (kind, allowed, default, None), key)
            self.assertEqual(settings.describe(key, {})["group"], "process", key)
            self.assertEqual(settings.effective({})[key], (default, "default"), key)
        for good in ("en", "ru", "deu", " ru "):
            self.assertEqual(settings.check_value("artifacts.language", good), good.strip())
        for bad in ("Russian language", "EN", "e", "engl", "pt-br", "\u0440\u0443", ""):
            with self.assertRaisesRegex(settings.SettingsError, "2 or 3 lowercase letters", msg=bad):
                settings.check_value("artifacts.language", bad)
        self.cli("set", "artifacts.language", "Russian language")  # the stand checks the code and the message
        self.assertFalse(os.path.exists(self.cfg), "a refused value writes nothing")

    def test_the_project_lines(self):
        # the stand proves the old line, list and the file winning; here the final dot and the first line of two
        self.project("Language: ru.", "Mode: demo", "Mode: prod")
        self.assertEqual(self.get("project.stage"), (0, "demo\n", "source: project.md\n"))
        self.assertEqual(self.get("artifacts.language"), (0, "ru\n", "source: project.md\n"))

    def test_a_line_value_outside_the_list(self):
        self.project("Mode: staging", "Language: Russian")
        code, out, err = self.get("project.stage")
        self.assertEqual((code, out), (0, "\n"))
        self.assertIn("Mode: staging", err)
        self.assertTrue(err.endswith("source: default\n"), err)
        code, out, err = self.get("artifacts.language")
        self.assertEqual(out, "en\n")
        self.assertIn("Language: Russian", err)
        for args in (["list"], ["list", "--json"], ["describe"], ["describe", "project.stage"]):
            code, err = self.run_err(*args)
            self.assertEqual(code, 0, args)
            self.assertIn("Mode: staging", err, args)


class IgnoreListSetting(ConfigDir):
    """Requirements: Ignore list setting; Process paths stay tracked."""
    HINT = "run: solo-sdd ignore --write\n"

    def test_default_group_and_hint(self):
        self.assertEqual(settings.effective({})["git.ignore"], (".claude/worktrees/, .env, .env.*, !.env.example", "default"))
        self.assertEqual(self.describe("git.ignore")[1]["git.ignore"]["group"], "git")
        value = ".claude/worktrees/, .env, solo-sdd/changes/archive/"
        self.assertEqual(self.cli("set", "git.ignore", value), (0, "git.ignore: %s\n%s" % (value, self.HINT)))
        code, out = self.cli("unset", "git.ignore")
        self.assertEqual((code, out.endswith(self.HINT)), (0, True), out)
        self.assertEqual(self.cli("set", "dispatch.limit", "3"), (0, "dispatch.limit: 3\n"), "only git.ignore hints")

    def test_process_paths_refused(self):
        self.write("# keep\n")
        for value, item, path in (("solo-sdd/", "solo-sdd/", "solo-sdd/"), ("*.md", "*.md", "AGENTS.md"),
                                  (".env, CLAUDE.md", "CLAUDE.md", "CLAUDE.md"), ("project.md", "project.md", "solo-sdd/project.md"),
                                  ("solo-sdd/changes/", "solo-sdd/changes/", "solo-sdd/changes/"),
                                  ("solo-sdd/changes/*/", "solo-sdd/changes/*/", "solo-sdd/changes/<change>/"),
                                  ("solo-sdd/specs/settings/", "solo-sdd/specs/settings/", "solo-sdd/specs/<capability>/"),
                                  ("*/**/spec.md", "*/**/spec.md", "solo-sdd/specs/<capability>/"), ("s*", "s*", "solo-sdd/"),
                                  ("solo-sdd/ch[a]nges/", "solo-sdd/ch[a]nges/", "solo-sdd/changes/"),
                                  ("agents.md", "agents.md", "AGENTS.md"), ("SOLO-SDD/", "SOLO-SDD/", "solo-sdd/"),
                                  ("solo-sdd/README.md", "solo-sdd/README.md", "solo-sdd/<top>/"),
                                  ("solo-sdd/changes/*/notes.md", "solo-sdd/changes/*/notes.md", "solo-sdd/changes/<change>/<...>/"),
                                  ("#x", "#x", "starts with #")):
            code, out = self.cli("set", "git.ignore", value)
            self.assertEqual(code, 1, value)
            self.assertIn("git.ignore item %s" % item, out, value)
            self.assertIn(path, out, value)
        self.assertEqual(self.read(), "# keep\n")
        for value in ("solo-sdd/changes/archive/", "solo-sdd/changes/archive/**", "**/archive/", "node_modules",
                      "solo-sdd/changes/Archive/", "docs/waiting.md", "!AGENTS.md", "settings", "foo"):
            self.assertEqual(self.cli("set", "git.ignore", value)[0], 0, value)

    def test_the_names_of_the_tree_refused(self):
        for rel in ("solo-sdd/specs/settings", "solo-sdd/changes/foo", "solo-sdd/integrations/x"):
            os.makedirs(os.path.join(self.dir, rel))
        self.write("# keep\n")
        for value, path in (("settings", "solo-sdd/specs/settings/"), ("foo", "solo-sdd/changes/foo/"),
                            ("**/foo/", "solo-sdd/changes/foo/"), ("x", "solo-sdd/integrations/x/")):
            code, out = self.cli("set", "git.ignore", value)
            self.assertEqual(code, 1, value)
            self.assertIn("git.ignore item %s hides %s" % (value, path), out, value)
        self.assertEqual(self.read(), "# keep\n")
        locked = os.path.join(self.dir, "solo-sdd", "specs")
        os.chmod(locked, 0)
        self.addCleanup(os.chmod, locked, 0o755)
        code, out = self.cli("set", "git.ignore", "node_modules")
        self.assertEqual((code, "cannot list" in out), (1, True), out)
        self.assertEqual(self.read(), "# keep\n")

    def test_a_broken_file_line(self):
        self.write("# c\ngit.ignore: .env, *.md\n")
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertIn("solo-sdd/config:2: git.ignore item *.md hides AGENTS.md", out)


GIT = ("git", "-c", "init.defaultBranch=main", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false")


class BranchAndCommitPrefixes(ConfigDir):
    """Requirements: Branch and commit prefixes; Prefix change guard."""

    def repo(self, *branches, archived=(), opened=()):
        """self.dir as a git repository with one commit, the branches, archived and open change folders."""
        for cid in opened:
            os.makedirs(os.path.join(self.dir, "solo-sdd", "changes", cid))
        for cid in archived:
            os.makedirs(os.path.join(self.dir, "solo-sdd", "changes", "archive", "2026-01-01-" + cid))
        for args in (("init", "-q"), ("commit", "-q", "--allow-empty", "-m", "x")) + tuple(("branch", b) for b in branches):
            subprocess.run(GIT + ("-C", self.dir) + args, check=True, capture_output=True, stdin=subprocess.DEVNULL)

    def test_defaults_and_describe(self):
        values = settings.effective({})
        self.assertEqual([values[k] for k in ("delivery.branch-prefix", "delivery.plan-prefix", "commit.light-prefix")],
                         [("change/", "default"), ("plan/", "default"), ("light:", "default")])
        code, blocks = self.describe("delivery.branch-prefix")
        self.assertEqual((code, blocks["delivery.branch-prefix"]["group"], blocks["delivery.branch-prefix"]["default"]),
                         (0, "delivery", "change/"))
        self.assertEqual(self.describe("commit.light-prefix")[1]["commit.light-prefix"]["group"], "process")
        self.assertEqual(self.cli("set", "commit.light-prefix", "[quick]"), (0, "commit.light-prefix: [quick]\n"))

    def test_a_leftover_change_branch(self):
        self.repo("change/a", opened=["a"])
        self.write("# keep\n")
        code, out = self.cli("set", "delivery.branch-prefix", "feat/")
        self.assertEqual(code, 1)
        self.assertIn("change/a", out)
        self.assertEqual((self.read(), self.get("delivery.branch-prefix")[1]), ("# keep\n", "change/\n"))

    def test_unset_guarded_too(self):
        self.repo("feat/a", opened=["a"])
        self.write("delivery.branch-prefix: feat/\n")
        code, out = self.cli("unset", "delivery.branch-prefix")
        self.assertEqual(code, 1)
        self.assertIn("feat/a", out)
        self.assertEqual(self.read(), "delivery.branch-prefix: feat/\n")

    def test_a_branch_of_an_archived_change(self):
        self.repo("change/old", "change/b", archived=["old"])  # b: a branch of no change at all
        self.assertEqual(self.cli("set", "delivery.branch-prefix", "feat/")[0], 0)
        self.assertEqual(self.get("delivery.branch-prefix")[1], "feat/\n")

    def test_equal_prefixes_and_a_prefix_git_refuses(self):
        for key, value, why in (("delivery.plan-prefix", "change/", "delivery.branch-prefix"),
                                ("delivery.branch-prefix", "plan/", "delivery.plan-prefix"),
                                ("delivery.branch-prefix", "feat/*", "valid branch name"),
                                ("delivery.plan-prefix", "p.lock/", "valid branch name")):
            code, out = self.cli("set", key, value)
            self.assertEqual(code, 1, value)
            self.assertIn(why, out, value)
            self.assertFalse(os.path.exists(self.cfg), value)

    def test_outside_git_passes_a_failed_listing_refuses(self):
        self.assertEqual(self.cli("set", "delivery.branch-prefix", "feat/")[0], 0, "no repository: no branches to keep")
        fake = os.path.join(self.dir, "bin")  # a git whose branch listing fails: the external program's double
        os.makedirs(fake)
        with open(os.path.join(fake, "git"), "w") as f:
            f.write('#!/bin/sh\ncase "$*" in *for-each-ref*) echo "fatal: bad object HEAD" >&2; exit 128;; esac\n'
                    'exec %s "$@"\n' % shutil.which("git"))
        os.chmod(os.path.join(fake, "git"), 0o755)
        from unittest import mock
        out = io.StringIO()
        with mock.patch.dict(os.environ, {"PATH": fake + os.pathsep + os.environ["PATH"]}), \
                contextlib.redirect_stdout(out):
            code = settings.run(["set", "delivery.branch-prefix", "team/"], self.dir)
        self.assertEqual(code, 1)
        self.assertIn("cannot list the branches: fatal: bad object HEAD", out.getvalue())
        self.assertEqual(self.read(), "delivery.branch-prefix: feat/\n")


PREFIXES = st.text(st.sampled_from("ab/.-*~@{}:?[\\ ^_"), min_size=1, max_size=8) | st.sampled_from(
    ["feat/", "x/", "a//", "a/.b/", "a.lock/", "@{", "a/", "feat/*", "/a", "a.", "-a/", "plan/", "change/"])


def no_ref_check(root, old, new):
    """A mutant of prefix_refusal without the ref check. The property must reject it."""
    now = [new.get(k, ("",))[0] for k in settings.BRANCH_KEYS]
    return "equal" if now[0] == now[1] else None


def check_prefix_guard(d, prefix):
    """config set of the branch prefix exits 1 with the file unchanged, or git takes <prefix>a as a branch name."""
    with open(os.path.join(d, settings.SETTINGS_FILE), "w", encoding="utf-8") as f:
        f.write("# keep\n")
    with contextlib.redirect_stdout(io.StringIO()):
        code = settings.run(["set", "delivery.branch-prefix", prefix], d)
    with open(os.path.join(d, settings.SETTINGS_FILE), encoding="utf-8") as f:
        text = f.read()
    if code:
        assert text == "# keep\n", (prefix, text)
    else:
        r = subprocess.run(["git", "check-ref-format", "--branch", settings.check_value("delivery.branch-prefix", prefix)
                            + "a"], capture_output=True, stdin=subprocess.DEVNULL)
        assert r.returncode == 0, prefix


class PrefixChangeGuardProperty(ConfigDir):
    """Requirement: Prefix change guard (property)."""

    @hsettings(max_examples=150, deadline=None)
    @given(PREFIXES)
    def test_prefix_change_guard_property(self, prefix):
        check_prefix_guard(self.dir, prefix)

    def test_no_ref_check_fails_the_property(self):
        from unittest import mock

        @hsettings(max_examples=150, deadline=None, database=None)
        @given(PREFIXES)
        def mutant(prefix):
            check_prefix_guard(self.dir, prefix)
        with mock.patch.object(settings, "prefix_refusal", no_ref_check), self.assertRaises(AssertionError):
            mutant()


MODELS = st.sampled_from(["claude-opus-4.5", "opus[1m]", "gpt_5.1-mini"]) | st.text(st.sampled_from(settings.MODEL_CHARS),
                                                                                    min_size=1, max_size=12)
VALUES = {k: st.sampled_from(v[1]) if v[1] else MODELS if v[0] == "model" else
          st.integers(settings.INT_MIN.get(k, 1), settings.INT_MIN.get(k, 1) + 98).map(str)
          for k, v in settings.REGISTRY.items()}
VALUES.update({"delivery.branch-prefix": st.sampled_from(["change/", "feat/", "team-1/"]),
               "delivery.plan-prefix": st.sampled_from(["plan/", "plans/"]),
               "commit.light-prefix": st.sampled_from(["light:", "[quick]", "q: x"]),
               "artifacts.language": st.sampled_from(["en", "ru", "deu"]),
               "ui.extensions": st.sampled_from([".html", ".html, .jinja", ".vue, .tsx, .J2"]),
               "ui.widths": st.sampled_from(["1280, 390", "1440", "1920, 768, 360"])})
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
