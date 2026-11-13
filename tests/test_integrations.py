"""solo_sdd/integrations.py and `solo-sdd integrations`: the description, defaults, sources, enablement and the command."""
import contextlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from hypothesis import given, settings as hsettings, strategies as st

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import cli, doctor, integration_run, integrations, settings  # noqa: E402

I = integrations
OWNER = os.path.join(".local", "share", "solo-sdd", "integrations")
MARKER = ('name: marker-check\nabout: refuses a marker line\npoints: checks, ship\n'
          'command: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"\n')
DUP = "name: dup-scan\nabout: finds copied code\npoints: checks\ncommand: dup-scan .\n"
SHIPPED = os.path.join(REPO, "integrations")  # the bundled integrations of this repository


def make(base, name, text):
    """The folder base/name with its integration file of text (str or bytes); the folder path."""
    path = os.path.join(base, name)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, I.INTEGRATION_FILE), "wb") as f:
        f.write(text.encode() if isinstance(text, str) else text)
    return path


def call(args, cwd, home):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = I.run(args, cwd, home)
    return code, out.getvalue()


class Project(unittest.TestCase):
    """A temporary project with a solo-sdd/ tree and a temporary home."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="integrations-")
        self.root, self.home = os.path.join(self.tmp, "proj"), os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.root, "solo-sdd", "changes"))
        os.makedirs(self.home)
        self.proj_dir = os.path.join(self.root, "solo-sdd", "integrations")
        self.owner_dir = os.path.join(self.home, OWNER)
        self.cfg = os.path.join(self.root, settings.SETTINGS_FILE)
        bundled = mock.patch.object(I, "BUNDLED", os.path.join(self.tmp, "bundled"))  # the shipped ones in their tests
        bundled.start()
        self.addCleanup(bundled.stop)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def cli(self, *args):
        return call(list(args), self.root, self.home)

    def config(self, text=None):
        if text is not None:
            with open(self.cfg, "w", newline="") as f:
                f.write(text)
        with open(self.cfg, "rb") as f:
            return f.read()

    def refused(self, text, folder="marker-check"):
        with self.assertRaises(I.IntegrationError) as e:
            I.parse_integration(text, folder, "solo-sdd/integrations/%s/integration" % folder)
        return str(e.exception)


class IntegrationDescription(Project):
    """Requirement: Integration description."""

    def test_integration_description_a_complete_description(self):
        make(self.proj_dir, "marker-check", MARKER)
        code, out = self.cli("list")
        self.assertEqual((code, out), (0, "marker-check project disabled checks, ship: refuses a marker line\n"))

    def test_integration_description_name_differs_from_the_folder(self):
        msg = self.refused(MARKER.replace("name: marker-check", "name: other-check"))
        self.assertTrue(msg.startswith("solo-sdd/integrations/marker-check/integration:1: name takes"), msg)

    def test_integration_description_a_point_without_its_command(self):
        msg = self.refused(MARKER.replace('command: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"\n', ""))
        self.assertEqual(msg, "solo-sdd/integrations/marker-check/integration: command is required for the point checks")
        msg = self.refused("name: marker-check\nabout: a\npoints: audit\n")
        self.assertIn("material is required for the point audit", msg)

    def test_required_keys(self):
        for key in ("name", "about", "points"):
            text = "".join(ln + "\n" for ln in MARKER.splitlines() if not ln.startswith(key + ":"))
            self.assertEqual(self.refused(text), "solo-sdd/integrations/marker-check/integration: %s is required" % key)


class FieldDefaults(Project):
    """Requirement: Field defaults."""

    def test_field_defaults_defaults_applied(self):
        got = I.parse_integration("name: t\nabout: a\npoints: checks\ncommand: run\n", "t", "x")
        self.assertEqual(got, {"name": "t", "about": "a", "points": ["checks"], "command": "run", "material": "",
                               "applies": [], "requires": "", "mode": "advice", "missing": "warn", "timeout": 120,
                               "output": 20, "tags": []})  # tags: MODIFIED Integration description

    def test_field_defaults_material_outside_the_folder(self):
        text = "name: marker-check\nabout: a\npoints: review\nmaterial: ../secret.md\n"
        msg = self.refused(text)
        self.assertTrue(msg.startswith("solo-sdd/integrations/marker-check/integration:4: material takes"), msg)

    def test_values(self):
        base = "name: marker-check\nabout: a\npoints: checks\ncommand: c\n"
        for line, word in (("timeout: 0", "timeout takes a whole number"), ("output: two", "output takes"),
                           ("timeout: ٣", "timeout takes"), ("missing: maybe", "missing takes warn, fail"),
                           ("requires: a b", "requires takes"), ("requires: x;rm$(id)", "requires takes"),
                           ("applies: /etc/*", "applies takes"),
                           ("applies: ../*", "applies takes")):
            self.assertIn("integration:5: " + word, self.refused(base + line + "\n"), line)
        self.assertIn("points takes", self.refused(base.replace("checks", "checks, checks")))
        self.assertIn("points takes", self.refused(base.replace("checks", "deploy")))
        got = I.parse_integration(base + "applies: *.py, src/**\ntimeout: 007\nmode: gate\n", "marker-check", "x")
        self.assertEqual((got["applies"], got["timeout"], got["mode"]), (["*.py", "src/**"], 7, "gate"))


class IntegrationSources(Project):
    """Requirement: Integration sources."""

    def test_integration_sources_same_name_in_both(self):
        make(self.proj_dir, "marker-check", MARKER)
        make(self.owner_dir, "marker-check", "broken, never read\n")
        code, out = self.cli("list")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), ["marker-check project disabled checks, ship: refuses a marker line",
                                            "marker-check owner shadowed by the project copy"])

    def test_home_only_from_the_passed_home(self):
        other = os.path.join(self.tmp, "other-home")
        make(os.path.join(other, OWNER), "dup-scan", DUP)
        old = os.environ.get("HOME")
        os.environ["HOME"] = other
        try:
            self.assertEqual(self.cli("list"), (0, ""))
            self.assertEqual(call(["list"], self.root, None)[1], "dup-scan owner disabled checks: finds copied code\n")
        finally:
            os.environ["HOME"] = old

    def test_a_plain_file_beside_the_folders(self):
        os.makedirs(self.proj_dir)
        with open(os.path.join(self.proj_dir, "README.md"), "w") as f:
            f.write("notes\n")
        os.makedirs(os.path.join(self.proj_dir, "empty"))
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("empty project broken: solo-sdd/integrations/empty/integration: "), out)
        self.assertNotIn("README", out)


class ExplicitEnablement(Project):
    """Requirement: Explicit enablement."""

    def test_explicit_enablement_owner_integration_not_enabled_by_itself(self):
        make(self.owner_dir, "dup-scan", DUP)
        self.assertEqual(self.cli("list"), (0, "dup-scan owner disabled checks: finds copied code\n"))
        self.config("integrations:\n")
        self.assertEqual(self.cli("list"), (0, "dup-scan owner disabled checks: finds copied code\n"))

    def test_explicit_enablement_a_listed_name_without_a_folder(self):
        make(self.owner_dir, "dup-scan", DUP)
        self.config("integrations: no-such\n")
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertEqual(out.splitlines()[0], "dup-scan owner disabled checks: finds copied code")
        self.assertTrue(out.splitlines()[1].startswith("no-such: listed in integrations of solo-sdd/config"), out)

    def test_explicit_enablement_a_stale_name_removed(self):
        self.config("# keep\nintegrations: no-such\ndispatch.limit: 3\n")
        self.assertEqual(self.cli("disable", "no-such"), (0, "integrations: none\n"))
        self.assertEqual(self.config(), b"# keep\ndispatch.limit: 3\n")


class ExplicitEnablementBundled(Project):
    """Requirement: Explicit enablement (the bundled exception)."""

    def test_explicit_enablement_a_bundled_integration_by_default(self):
        I.BUNDLED = SHIPPED
        self.config("integrations:\nintegrations.off:\n")
        code, out = self.cli("list")
        self.assertEqual(code, 0, out)
        self.assertTrue(out.startswith("antislop bundled enabled review: "), out)


class BundledSource(Project):
    """Requirement: Bundled source."""

    def test_bundled_source_a_project_folder_shadows_a_bundled_one(self):
        I.BUNDLED = SHIPPED
        make(self.proj_dir, "antislop", "name: antislop\nabout: own rules\npoints: review\nmaterial: r.md\n")
        make(self.owner_dir, "security-audit", "name: security-audit\nabout: mine\npoints: audit\nmaterial: m.md\n")
        code, out = self.cli("list")
        self.assertEqual(code, 0, out)
        self.assertEqual(out.splitlines(), ["antislop project disabled review: own rules",
                                            "antislop bundled shadowed by the project copy",
                                            "security-audit owner disabled audit: mine",
                                            "security-audit bundled shadowed by the owner copy"])
        self.assertEqual(self.cli("disable", "antislop"), (0, "integrations: none\n"))  # the project one: its own line
        self.assertFalse(os.path.exists(self.cfg))


class BundledDefaultState(Project):
    """Requirement: Bundled default state."""

    def test_doctor_shows_the_bundled_ones_on_by_default(self):
        I.BUNDLED = SHIPPED
        rows = list(doctor._integrations(self.root, self.home))
        self.assertEqual([(r[0], r[1], r[2].split(",")[0]) for r in rows],
                         [("ok", "integration antislop", "bundled"), ("ok", "integration security-audit", "bundled")])

    def test_bundled_default_state_switched_off_in_one_project(self):
        I.BUNDLED = SHIPPED
        self.config("# keep\r\ndispatch.limit: 3\r\n")
        self.assertEqual(self.cli("disable", "antislop"), (0, "integrations.off: antislop\n"))
        self.assertEqual(self.config(), b"# keep\r\ndispatch.limit: 3\r\nintegrations.off: antislop\r\n")
        self.assertEqual(settings.read_settings(self.root)["integrations.off"], ("antislop", "file"))
        self.assertIn("antislop bundled disabled review: ", self.cli("list")[1])
        self.assertEqual(self.cli("disable", "antislop"), (0, "integrations.off: antislop\n"))
        self.assertEqual(self.cli("enable", "antislop"), (0, "integrations.off: none\n"))
        self.assertEqual(self.config(), b"# keep\r\ndispatch.limit: 3\r\n")

    def test_a_bundled_name_in_integrations_changes_nothing(self):
        I.BUNDLED = SHIPPED
        self.config("integrations: antislop\nintegrations.off: antislop, gone\n")
        code, out = self.cli("list")
        self.assertEqual(code, 0, out)  # a stale integrations.off name is not an error
        self.assertIn("antislop bundled disabled review: ", out)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = integration_run.run(["--point", "review"], self.root, self.home)
        self.assertEqual((code, out.getvalue()), (0, "no integrations enabled\n"))  # the untagged call agrees
        rows = list(doctor._integrations(self.root, self.home))
        self.assertEqual([r[1] for r in rows], ["integration security-audit"], rows)  # and doctor
        self.config("integrations: security-audit\n")
        self.assertIn("security-audit bundled enabled audit: ", self.cli("list")[1])


class MaterialByTag(Project):
    """Requirement: Material by tag."""

    def check(self, *args, cwd=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = integration_run.run(list(args), cwd or self.root, self.home)
        return code, out.getvalue()

    def test_material_by_tag_outside_a_project(self):
        I.BUNDLED = SHIPPED
        bare = os.path.join(self.tmp, "bare")
        os.makedirs(bare)
        self.assertEqual(self.check("--point", "audit", "--tag", "security", cwd=bare),
                         (0, "MATERIAL security-audit: %s\n" % os.path.join(SHIPPED, "security-audit", "skills",
                                                                            "security-audit", "SKILL.md")))
        self.assertEqual(self.check("--point", "review", cwd=bare), (1, "no solo-sdd/ tree\n"))
        make(self.owner_dir, "security-audit", "name: security-audit\nabout: mine\npoints: audit\nmaterial: m.md\n")
        self.assertEqual(self.check("--point", "audit", "--tag", "security", cwd=bare),
                         (0, "no integrations enabled with the point audit and the tag security\n"))  # shadowed, off
        if os.geteuid() == 0:
            return  # root lists a mode-0 folder; the refusal below needs an unreadable one
        os.chmod(self.owner_dir, 0)  # an owner source it cannot list may hold a shadowing copy: refused, not skipped
        try:
            for cwd in (bare, self.root):
                code, out = self.check("--point", "audit", "--tag", "security", cwd=cwd)
                self.assertEqual(code, 1, out)
                self.assertTrue(out.startswith("FAIL -: ~/.local/share/solo-sdd/integrations: "), out)
        finally:
            os.chmod(self.owner_dir, 0o755)

    def test_material_by_tag_an_untagged_call(self):
        I.BUNDLED = SHIPPED
        self.assertEqual(self.check("--point", "review"), (0, "no integrations enabled\n"))
        self.assertEqual(self.check("--point", "audit"), (0, "no integrations enabled\n"))

    def test_tag_off_owner_and_arguments(self):
        I.BUNDLED = SHIPPED
        self.config("integrations.off: antislop\n")
        self.assertEqual(self.check("--point", "review", "--tag", "ui"),
                         (0, "no integrations enabled with the point review and the tag ui\n"))
        style = make(self.owner_dir, "style-notes", "name: style-notes\nabout: s\npoints: review\nmaterial: m.md\n"
                                                    "tags: ui\n")
        with open(os.path.join(style, "m.md"), "w") as f:
            f.write("rules\n")
        self.assertEqual(self.check("--point", "review", "--tag", "ui")[1].startswith("no integrations enabled"), True)
        self.config("integrations: style-notes\n")
        self.assertEqual(self.check("--point", "review", "--tag", "ui"),
                         (0, "MATERIAL antislop: %s\nMATERIAL style-notes: %s\n"
                          % (os.path.join(SHIPPED, "antislop", "antislop.md"), os.path.join(style, "m.md"))))
        self.assertEqual(self.check("--point", "review", "--tag", "security")[1],
                         "no integrations enabled with the point review and the tag security\n")
        self.assertEqual(self.check("--point", "review", "--tag", "copy")[1].split(":")[0], "MATERIAL antislop")
        for bad in (["--point", "checks", "--tag", "ui"], ["--point", "review", "--tag"],
                    ["--point", "review", "--changed", "--tag", "ui"], ["--point", "review", "--tag", "ui", "--tag", "x"],
                    ["--point", "review", "--tag", "UI"], ["--point", "review", "--tag", ""],
                    ["--point", "review", "--tag", "--changed"]):
            self.assertIsNone(integration_run.run(bad, self.root, self.home), bad)
        self.assertIn("tags takes names", self.refused("name: marker-check\nabout: a\npoints: review\nmaterial: m\n"
                                                       "tags: UI\n"))
        self.assertIn("tags takes names", self.refused("name: marker-check\nabout: a\npoints: review\nmaterial: m\n"
                                                       "tags: ui, ui\n"))


class SkillsReadRulesByPointAndTag(unittest.TestCase):
    """Requirement: Skills read rules by point and tag."""

    def skill(self, name):
        with open(os.path.join(REPO, "skills", name, "SKILL.md"), encoding="utf-8") as f:
            return f.read()

    def test_skills_read_rules_by_point_and_tag_rules_off(self):
        """The call strings and the absence of copy paths are stand step 6; here the sentence for rules that are off,
        keyed on the bundled name's own MATERIAL line, so another integration of the tag does not keep them on."""
        for name, line in (("ui-check", "no `MATERIAL antislop:` line"), ("copy-check", "no `MATERIAL antislop:` line"),
                           ("spec-next", "no `MATERIAL antislop:` line"),
                           ("spec-audit", "no `MATERIAL security-audit:` line")):
            text = self.skill(name)
            found = [ln for ln in text.splitlines() if line in ln]
            self.assertEqual(len(found), 1, name)
            self.assertIn("off in this project", found[0], name)
            self.assertNotIn("No `MATERIAL` line", text, name)

    def test_skills_read_rules_by_point_and_tag_a_failed_call_keeps_the_rules_on(self):
        """Fail-closed: rules off only on exit 0 without the bundled name's line; every other exit is a refusal. The
        real outcomes of an older or misused solo-sdd (exit 2, usage) and of no solo-sdd on PATH (127) are neither."""
        for name, off in (("ui-check", "Exit 0 with no `MATERIAL antislop:` line"),
                          ("copy-check", "Exit 0 with no `MATERIAL antislop:` line"),
                          ("spec-next", "exits 0 with no `MATERIAL antislop:` line"),
                          ("spec-audit", "Exit 0 with no `MATERIAL security-audit:` line")):
            text = self.skill(name)
            self.assertIn(off, text, name)
            refusal = [ln for ln in text.splitlines() if "exit other than 0" in ln or "exits other than 0" in ln]
            self.assertEqual(len(refusal), 1, name)
            for part in ("2 with the usage text", "127 with no `solo-sdd`", "any other code", "rules stay on"):
                self.assertIn(part, refusal[0], (name, part))
        tmp = tempfile.mkdtemp(prefix="integrations-refusal-")
        try:
            empty = os.path.join(tmp, "bin")
            os.makedirs(empty)
            outcomes = [subprocess.run(args, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env)
                        for args, env in (([sys.executable, "-m", "solo_sdd", "check", "--point", "review", "--tag"],
                                           dict(os.environ, PYTHONPATH=REPO)),
                                          (["/bin/sh", "-c", "solo-sdd check --point review --tag ui"],
                                           {"PATH": empty}))]
            self.assertEqual([p.returncode for p in outcomes], [2, 127])
            for p in outcomes:
                rules_off = p.returncode == 0 and "MATERIAL antislop:" not in p.stdout  # the skills' only off reading
                self.assertFalse(rules_off, p.stdout + p.stderr)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class BrokenDescriptionRefused(Project):
    """Requirement: Broken description refused."""

    def test_broken_description_refused_an_unknown_key(self):
        make(self.proj_dir, "marker-check", MARKER.replace("points: checks, ship\n", "colour: red\npoints: checks\n"))
        make(self.owner_dir, "dup-scan", DUP)
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertIn("dup-scan owner disabled checks: finds copied code", out.splitlines())
        self.assertIn("marker-check project broken: solo-sdd/integrations/marker-check/integration:3: unknown key "
                      "colour; known: name, about, points", out)

    def test_broken_description_refused_a_wrong_mode(self):
        msg = self.refused(MARKER + "mode: strict\n")
        self.assertEqual(msg, "solo-sdd/integrations/marker-check/integration:5: mode takes gate, advice, not 'strict'")

    def test_lines(self):
        self.assertTrue(self.refused(MARKER[:19] + "just words\n").endswith('integration:2: not "key: value"'))
        self.assertIn("integration:5: about is set twice", self.refused(MARKER + "about: again\n"))
        self.assertIn("integration:2: about takes", self.refused(MARKER.replace("about: refuses a marker line",
                                                                                "about:")))
        crlf = I.parse_integration(MARKER.replace("\n", "\r\n") + "# c\r\n\r\n", "marker-check", "x")
        self.assertEqual(crlf["points"], ["checks", "ship"])


class HostileInput(Project):
    """Requirement: Broken description refused, on an outside file: size, encoding, file kind, characters, links."""

    def read(self, name="marker-check"):
        with self.assertRaises(I.IntegrationError) as e:
            I.read_integration(os.path.join(self.proj_dir, name), name, "f")
        return str(e.exception)

    def test_too_large(self):
        make(self.proj_dir, "marker-check", MARKER + "# " + "a" * I.INTEGRATION_MAX_BYTES + "\n")
        self.assertEqual(self.read(), "f: larger than 65536 bytes")

    def test_not_utf8(self):
        make(self.proj_dir, "marker-check", MARKER.encode() + b"about: \xff\n")
        self.assertEqual(self.read(), "f: not UTF-8 text at byte %d" % (len(MARKER) + 7))

    def test_fifo_and_folder_and_missing(self):
        path = os.path.join(self.proj_dir, "marker-check")
        os.makedirs(path)
        self.assertIn("No such file", self.read())
        os.mkfifo(os.path.join(path, I.INTEGRATION_FILE))
        self.assertEqual(self.read(), "f: not a regular file")
        os.remove(os.path.join(path, I.INTEGRATION_FILE))
        os.mkdir(os.path.join(path, I.INTEGRATION_FILE))
        self.assertEqual(self.read(), "f: not a regular file")

    def test_control_characters_never_printed(self):
        for ch in ("\x1b", "‮", "\x85", " ", "﻿", "\x00"):
            make(self.proj_dir, "marker-check", MARKER.replace("refuses", "re%sfuses" % ch))
            code, out = self.cli("list")
            self.assertEqual(code, 1, repr(ch))
            self.assertIn("integration:2: a control character U+%04X in the line" % ord(ch), out)
            self.assertNotIn(ch, out)

    def test_hostile_folder_names_never_printed(self):
        for raw in ("evil\x1b[31mred", "nl\nline", "bidi\u202eabc", "Upper"):
            os.makedirs(os.path.join(self.proj_dir, raw))
        make(self.owner_dir, "dup-scan", DUP)
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        for ch in ("\x1b", "\u202e"):
            self.assertNotIn(ch, out)
        self.assertEqual(len(out.splitlines()), 5, out)
        self.assertIn("'nl\\nline' project broken: solo-sdd/integrations/'nl\\nline'/integration: ", out)
        code, out = self.cli("enable", "zz")
        self.assertEqual(code, 1)
        self.assertNotIn("\x1b", out)
        self.assertEqual(self.cli("enable", "evil\x1b[31mred")[0], 1)

    def test_undecodable_folder_name_escaped(self):
        self.assertEqual(I.integration_shown("a\udcffb"), "'a\\udcffb'")
        self.assertEqual(I.integration_shown("dup-scan"), "dup-scan")

    def test_links_out_of_the_project(self):
        secret = os.path.join(self.home, ".env")
        with open(secret, "w") as f:
            f.write("API_TOKEN=s3cr3t-value\nmode: s3cr3t-mode\n")
        os.makedirs(os.path.join(self.proj_dir, "leak"))
        os.symlink(secret, os.path.join(self.proj_dir, "leak", I.INTEGRATION_FILE))
        os.makedirs(os.path.join(self.tmp, "elsewhere", "far"))
        make(os.path.join(self.tmp, "elsewhere"), "far", DUP.replace("dup-scan", "far"))
        os.symlink(os.path.join(self.tmp, "elsewhere", "far"), os.path.join(self.proj_dir, "far"))
        os.symlink(os.path.join(self.tmp, "no-such"), os.path.join(self.proj_dir, "gone"))
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertNotIn("s3cr3t", out)
        self.assertEqual(out.splitlines(), [
            "far project broken: solo-sdd/integrations/far: a link leading out of the project",
            "gone project broken: solo-sdd/integrations/gone: a link to no folder",
            "leak project broken: solo-sdd/integrations/leak/integration: a link, not the file itself"])
        linked = os.path.join(self.tmp, "elsewhere", "far")
        os.makedirs(self.owner_dir)
        os.symlink(linked, os.path.join(self.owner_dir, "far"))
        os.remove(os.path.join(self.proj_dir, "far"))
        self.assertIn("far owner disabled checks: finds copied code", self.cli("list")[1].splitlines())

    def test_material_leaving_the_folder(self):
        path = make(self.proj_dir, "rules", "name: rules\nabout: a\npoints: review\nmaterial: m/x.md\n")
        outside = os.path.join(self.tmp, "outside")
        os.makedirs(outside)
        os.symlink(outside, os.path.join(path, "m"))
        self.assertIn("f:4: material takes a path inside the integration folder", self.read("rules"))
        os.remove(os.path.join(path, "m"))
        os.makedirs(os.path.join(path, "m"))
        self.assertEqual(I.read_integration(path, "rules", "f")["material"], "m/x.md")
        for bad in ("/etc/passwd", "a/../../x", ".", "-x"):
            self.assertIn("material takes", self.refused("name: r\nabout: a\npoints: audit\nmaterial: %s\n" % bad, "r"))


class IntegrationsCommand(Project):
    """Requirement: Integrations command."""

    def test_integrations_command_enable_an_owner_integration(self):
        make(self.owner_dir, "dup-scan", DUP)
        self.config("# settings\r\ndispatch.limit: 3\r\n")
        self.assertEqual(self.cli("enable", "dup-scan"), (0, "integrations: dup-scan\n"))
        self.assertEqual(self.config(), b"# settings\r\ndispatch.limit: 3\r\nintegrations: dup-scan\r\n")
        self.assertEqual(settings.read_settings(self.root)["integrations"], ("dup-scan", "file"))
        self.assertEqual(self.cli("list"), (0, "dup-scan owner enabled checks: finds copied code\n"))

    def test_integrations_command_enable_twice_then_disable(self):
        make(self.proj_dir, "marker-check", MARKER)
        self.assertEqual(self.cli("enable", "marker-check")[0], 0)
        first = self.config()
        self.assertEqual(self.cli("enable", "marker-check"), (0, "integrations: marker-check\n"))
        self.assertEqual(self.config(), first)
        self.assertEqual(self.cli("disable", "marker-check"), (0, "integrations: none\n"))
        self.assertEqual(self.config(), b"")
        self.assertEqual(self.cli("disable", "marker-check"), (0, "integrations: none\n"))

    def test_integrations_command_enable_a_broken_one(self):
        make(self.proj_dir, "marker-check", MARKER + "colour: red\n")
        self.config("# c\n")
        code, out = self.cli("enable", "marker-check")
        self.assertEqual((code, out), (1, "solo-sdd/integrations/marker-check/integration:5: unknown key colour; "
                                          "known: %s\n" % ", ".join(I.INTEGRATION_FIELDS)))
        self.assertEqual(self.config(), b"# c\n")

    def test_unknown_names(self):
        code, out = self.cli("enable", "nope")
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("nope: no folder in solo-sdd/integrations/"), out)
        self.assertEqual(self.cli("disable", "nope")[0], 1)
        self.assertFalse(os.path.exists(self.cfg))

    def test_outside_a_tree_and_usage(self):
        shutil.rmtree(os.path.join(self.root, "solo-sdd"))
        self.assertEqual(self.cli("list"), (1, "no solo-sdd/ tree\n"))
        self.assertIsNone(I.run(["enable"], self.root, self.home))
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["integrations", "toggle", "x"]), 2)
        self.assertIn("wrong command", err.getvalue())

    def test_broken_config(self):
        self.config("integrations: Bad\n")
        code, out = self.cli("list")
        self.assertEqual(code, 1)
        self.assertIn("solo-sdd/config:1: integrations takes names", out)


# property tests

TEXT = st.text(st.characters(blacklist_categories=("Cc", "Cf", "Cs", "Zl", "Zp")), min_size=1, max_size=20).map(
    str.strip).filter(bool)
PATH = st.from_regex(r"[a-z][a-z0-9_.-]{0,6}(/[a-z][a-z0-9_-]{0,6}){0,2}", fullmatch=True)
GLOB = st.from_regex(r"[a-z*][a-z0-9*._-]{0,6}(/[a-z*][a-z0-9*._-]{0,6})?", fullmatch=True)


@st.composite
def descriptions(draw):
    """(lines, expected fields) of a valid description of folder `tool`: the keys in any order."""
    points = draw(st.lists(st.sampled_from(I.INTEGRATION_POINTS), min_size=1, unique=True))
    want = {"name": "tool", "about": draw(TEXT), "points": points}
    if {"checks", "ship"} & set(points) or draw(st.booleans()):
        want["command"] = draw(TEXT)
    if {"review", "audit"} & set(points) or draw(st.booleans()):
        want["material"] = draw(PATH)
    for key, values in (("mode", I.INTEGRATION_CHOICES["mode"]), ("missing", I.INTEGRATION_CHOICES["missing"])):
        if draw(st.booleans()):
            want[key] = draw(st.sampled_from(values))
    for key in ("timeout", "output"):
        if draw(st.booleans()):
            want[key] = draw(st.integers(1, 10 ** 6))
    if draw(st.booleans()):
        want["applies"] = draw(st.lists(GLOB, min_size=1, max_size=3))
    if draw(st.booleans()):
        want["requires"] = draw(st.from_regex(r"[a-z][a-z0-9_.+-]{0,8}", fullmatch=True))
    shown = {k: ", ".join(v) if isinstance(v, list) else str(v) for k, v in want.items()}
    lines = ["%s: %s" % kv for kv in shown.items()]
    lines += draw(st.lists(st.just("") | TEXT.map(lambda s: "# " + s), max_size=3))
    lines = draw(st.permutations(lines))
    full = {k: I._integration_value(k, d, "tool", None) for k, d in I.INTEGRATION_FIELDS.items() if d is not None}
    full.update(want)
    return lines, full


BROKEN = {"no colon": ["just words", "-- x"], "unknown key": ["colour: red", "Name: tool"],
          "bad value": ["mode: strict", "missing: maybe", "timeout: 0", "output: x", "points: deploy",
                        "name: Other", "about:", "material: ../x"]}


@st.composite
def broken_descriptions(draw):
    """(text, line number, key or None): a valid description with one broken line put in it."""
    lines, _ = draw(descriptions())
    kind = draw(st.sampled_from(sorted(BROKEN) + ["repeated key"]))
    keys = [ln.partition(":")[0] for ln in lines]
    if kind == "repeated key":
        i = draw(st.sampled_from([n for n, k in enumerate(keys) if k in I.INTEGRATION_FIELDS]))
        bad, at = lines[i], draw(st.integers(i + 1, len(lines)))
    else:
        bad = draw(st.sampled_from(BROKEN[kind]))
        lines = [ln for ln, k in zip(lines, keys) if k != bad.partition(":")[0]]
        at = draw(st.integers(0, len(lines)))
    lines = lines[:at] + [bad] + lines[at:]
    key = bad.partition(":")[0] if kind != "no colon" else None
    return "".join(ln + draw(st.sampled_from(["\n", "\r\n"])) for ln in lines), at + 1, key


def check_description(parse, lines, want, broken):
    """A valid description reads back every field; a broken line is refused naming its number and key."""
    text, at, key = broken
    assert parse("\n".join(lines) + "\n", "tool", "f") == want, (lines, want)
    try:
        got = parse(text, "tool", "f")
    except I.IntegrationError as e:
        msg = str(e)
        assert msg.startswith("f:%d: " % at), (text, at, msg)
        assert key is None or key in msg, (text, key, msg)
    else:
        raise AssertionError("not refused: %r -> %r" % (text, got))


def skipping_parse(text, folder, where, base=None):
    """A mutant reader: drops unknown keys. The property must reject it."""
    kept = "\n".join("" if ln.partition(":")[1] and ln.partition(":")[0].strip() not in I.INTEGRATION_FIELDS else ln
                     for ln in text.split("\n"))
    return I.parse_integration(kept, folder, where, base)


class BrokenDescriptionProperty(unittest.TestCase):
    """Requirement: Broken description refused (property)."""

    @hsettings(max_examples=400, deadline=None)
    @given(descriptions(), broken_descriptions())
    def test_broken_description_refused_property(self, valid, broken):
        check_description(I.parse_integration, valid[0], valid[1], broken)

    def test_the_property_rejects_a_reader_that_skips_unknown_keys(self):
        lines = ["name: tool", "about: a", "points: checks", "command: c"]
        want = I.parse_integration("\n".join(lines), "tool", "f")
        with self.assertRaises(AssertionError):
            check_description(skipping_parse, lines, want, ("\n".join(lines) + "\ncolour: red\n", 5, "colour"))


FOUND = ("alpha", "beta")  # alpha: a project integration, beta: an owner one
NAMES = FOUND + ("gone", "zeta")  # gone: listed in the config without a folder, zeta: neither listed nor found
OTHER = st.sampled_from(["dispatch.limit: 3", "mode: team", "# a comment", "", "   # indented: x"])


@st.composite
def configs(draw):
    """None (no file) or a config text with comments, other keys and maybe an integrations line, \\n or \\r\\n."""
    if draw(st.booleans()):
        return None
    lines = draw(st.lists(OTHER, max_size=4, unique=True))
    if draw(st.booleans()):
        listed = draw(st.lists(st.sampled_from(("alpha", "beta", "gone")), unique=True))
        lines.insert(draw(st.integers(0, len(lines))), "integrations: " + ", ".join(listed))
    end = draw(st.sampled_from(["\n", "\r\n"]))
    return "".join(ln + end for ln in lines)


def check_sequence(run, text, ops):
    """Each call leaves the integrations value the model expects, a repeat changes no byte, other lines keep bytes."""
    tmp = tempfile.mkdtemp(prefix="integrations-prop-")
    try:
        root, home = os.path.join(tmp, "p"), os.path.join(tmp, "h")
        os.makedirs(os.path.join(root, "solo-sdd", "changes"))
        make(os.path.join(root, "solo-sdd", "integrations"), "alpha", "name: alpha\nabout: a\npoints: checks\ncommand: c\n")
        make(os.path.join(home, OWNER), "beta", "name: beta\nabout: b\npoints: review\nmaterial: r.md\n")
        cfg = os.path.join(root, settings.SETTINGS_FILE)
        if text is not None:
            with open(cfg, "w", newline="") as f:
                f.write(text)
        value = settings.parse_settings(text or "").get("integrations", "")
        model = value.split(", ") if value else []
        others = [ln for ln in (text or "").splitlines(True) if not ln.lstrip().startswith("integrations:")]

        def read():
            try:
                with open(cfg, "rb") as f:
                    return f.read()
            except FileNotFoundError:
                return None
        for op, name in ops:
            if op == "enable":
                want_code = 0 if name in FOUND else 1
                if name in FOUND and name not in model:
                    model.append(name)
            else:
                want_code = 0 if name in model or name in FOUND else 1
                model = [n for n in model if n != name]
            with contextlib.redirect_stdout(io.StringIO()):
                code = run([op, name], root, home)
                after = read()
                again = run([op, name], root, home)
            assert (code, again) == (want_code, 0 if name in FOUND else 1), (op, name, code, again)
            assert read() == after, (op, name, "a repeated call changed the file")
            new = (after or b"").decode()
            value = settings.parse_settings(new).get("integrations", "")
            assert (value.split(", ") if value else []) == model, (op, name, value, model)
            assert [ln for ln in new.splitlines(True) if not ln.lstrip().startswith("integrations:")] == others, new
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def duplicating_run(args, cwd, home):
    """A mutant command: enable appends the name even when it is listed. The property must reject it."""
    cfg = os.path.join(cwd, settings.SETTINGS_FILE)
    text = settings.read_settings_text(cwd)
    listed = settings.parse_settings(text).get("integrations", "")
    if args[0] == "enable" and args[1] in listed.split(", "):
        with open(cfg, "w", newline="") as f:
            f.write(settings.set_text(text, "integrations", listed + ", " + args[1]))
        return 0
    return I.run(args, cwd, home)


class IntegrationsCommandProperty(unittest.TestCase):
    """Requirement: Integrations command (property)."""

    @hsettings(max_examples=150, deadline=None)
    @given(configs(), st.lists(st.tuples(st.sampled_from(("enable", "disable")), st.sampled_from(NAMES)), max_size=8))
    def test_integrations_command_property(self, text, ops):
        check_sequence(I.run, text, ops)

    def test_the_property_rejects_a_duplicating_enable(self):
        with self.assertRaises(AssertionError):
            check_sequence(duplicating_run, "# c\n", [("enable", "alpha"), ("enable", "alpha")])


@st.composite
def bundled_configs(draw):
    """None or a config text whose integrations and integrations.off lines may hold the bundled gamma, the project
    alpha and the stale gone: a bundled name written by hand into integrations and a stale off name included."""
    if draw(st.booleans()):
        return None
    lines = draw(st.lists(OTHER, max_size=3, unique=True))
    for key in ("integrations", "integrations.off"):
        if draw(st.booleans()):
            names = draw(st.lists(st.sampled_from(("alpha", "gamma", "gone")), unique=True))
            lines.insert(draw(st.integers(0, len(lines))), "%s: %s" % (key, ", ".join(names)))
    end = draw(st.sampled_from(["\n", "\r\n"]))
    return "".join(ln + end for ln in lines)


def check_bundled_state(run, text, ops):
    """After each call gamma (bundled) is enabled exactly when integrations.off does not name it, alpha (project)
    exactly when integrations names it, a repeat changes no byte, and the other lines keep their bytes."""
    tmp = tempfile.mkdtemp(prefix="integrations-bundled-")
    try:
        root, home, bundled = (os.path.join(tmp, n) for n in ("p", "h", "b"))
        os.makedirs(os.path.join(root, "solo-sdd", "changes"))
        make(os.path.join(root, "solo-sdd", "integrations"), "alpha", "name: alpha\nabout: a\npoints: checks\ncommand: c\n")
        make(bundled, "gamma", "name: gamma\nabout: g\npoints: review\nmaterial: g.md\ntags: ui\n")
        cfg = os.path.join(root, settings.SETTINGS_FILE)
        if text is not None:
            with open(cfg, "w", newline="") as f:
                f.write(text)
        found = settings.parse_settings(text or "")
        listed = I.listed_names(found.get("integrations", ""))
        off = I.listed_names(found.get("integrations.off", ""))
        others = [ln for ln in (text or "").splitlines(True) if not ln.lstrip().startswith("integrations")]

        def read():
            try:
                with open(cfg, "rb") as f:
                    return f.read()
            except FileNotFoundError:
                return b""
        with mock.patch.object(I, "BUNDLED", bundled):
            for op, name in ops:
                if name == "gamma":
                    off = [n for n in off if n != name] if op == "enable" else off if name in off else off + [name]
                elif name == "alpha":
                    listed = listed if op == "disable" or name in listed else listed + [name]
                    listed = [n for n in listed if n != name] if op == "disable" else listed
                elif op == "disable":
                    listed = [n for n in listed if n != name]
                with contextlib.redirect_stdout(io.StringIO()):
                    run([op, name], root, home)
                    after = read()
                    run([op, name], root, home)
                assert read() == after, (op, name, "a repeated call changed the file")
                now = settings.parse_settings(after.decode())
                assert I.listed_names(now.get("integrations", "")) == listed, (op, name, now, listed)
                assert I.listed_names(now.get("integrations.off", "")) == off, (op, name, now, off)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    run(["list"], root, home)
                state = dict(ln.split(" ")[0::2][:2] for ln in out.getvalue().splitlines() if ln.startswith(("alpha ", "gamma ")))
                assert state == {"alpha": "enabled" if "alpha" in listed else "disabled",
                                 "gamma": "disabled" if "gamma" in off else "enabled"}, (op, name, state, listed, off)
                assert [ln for ln in after.decode().splitlines(True) if not ln.lstrip().startswith("integrations")] == others
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def listing_run(args, cwd, home):
    """A mutant command: enable and disable of a bundled name write the integrations line. The property must reject it."""
    if args[0] in ("enable", "disable") and args[1] == "gamma":
        text = settings.read_settings_text(cwd)
        listed = I.listed_names(settings.parse_settings(text).get("integrations", ""))
        new = listed + ["gamma"] if args[0] == "enable" and "gamma" not in listed else [n for n in listed if n != "gamma"]
        with open(os.path.join(cwd, settings.SETTINGS_FILE), "w", newline="") as f:
            f.write(settings.set_text(text, "integrations", ", ".join(new) or None))
        return 0
    return I.run(args, cwd, home)


class BundledDefaultStateProperty(unittest.TestCase):
    """Requirement: Bundled default state (property)."""

    @hsettings(max_examples=150, deadline=None)
    @given(bundled_configs(), st.lists(st.tuples(st.sampled_from(("enable", "disable")),
                                                 st.sampled_from(("alpha", "gamma", "gone"))), max_size=8))
    def test_bundled_default_state_property(self, text, ops):
        check_bundled_state(I.run, text, ops)

    def test_the_property_rejects_a_bundled_name_written_into_integrations(self):
        with self.assertRaises(AssertionError):
            check_bundled_state(listing_run, "# c\n", [("disable", "gamma")])


if __name__ == "__main__":
    unittest.main()
