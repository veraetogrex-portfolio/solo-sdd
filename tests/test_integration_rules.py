"""Change integration-rules: the rules.md of an enabled integration in the solo-sdd block of AGENTS.md, written by
`init`, `integrations enable` and `disable`, refused when hostile, and `check --point review|audit` listing material."""
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

import marks

REPO = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, REPO)
from solo_sdd import init, integration_run, integrations as I, resources, rules_block  # noqa: E402

MARKER = "name: marker-check\nabout: refuses a marker line\npoints: checks\ncommand: true\n"
RULES = "Never write a DO-NOT-SHIP line.\n"
STYLE = "name: style-notes\nabout: style method\npoints: review\nmaterial: method.md\n"


def base():
    with open(os.path.join(resources.ROOT, "global", "AGENTS.md"), encoding="utf-8") as f:
        return rules_block.norm(f.read().replace("\r\n", "\n"))


def section(name, text):
    return "\n## Integration: %s\n\n%s" % (name, rules_block.norm(text.replace("\r\n", "\n").replace("\r", "\n")))


def call(fn, *args, **kw):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = fn(*args, **kw)
    return code, out.getvalue()


class Project(unittest.TestCase):
    """A temporary project (a .git folder, a solo-sdd/ tree) and a temporary home."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="integration-rules-")
        self.root, self.home = os.path.join(self.tmp, "proj"), os.path.join(self.tmp, "home")
        os.makedirs(os.path.join(self.root, "solo-sdd", "changes"))
        os.makedirs(os.path.join(self.root, ".git"))
        os.makedirs(self.home)
        self.agents = os.path.join(self.root, "AGENTS.md")
        self.cfg = os.path.join(self.root, "solo-sdd", "config")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def integration(self, name, text, rules=None):
        path = os.path.join(self.root, "solo-sdd", "integrations", name)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "integration"), "w") as f:
            f.write(text)
        if rules is not None:
            with open(os.path.join(path, "rules.md"), "wb") as f:
                f.write(rules if isinstance(rules, bytes) else rules.encode())
        return path

    def put(self, path, text):
        with open(path, "w", newline="") as f:
            f.write(text)

    def read(self, path):
        try:
            with open(path, "rb") as f:
                return f.read()
        except FileNotFoundError:
            return None

    def cli(self, *args):
        return call(I.run, list(args), self.root, self.home)

    def initialised(self, own="# Team rules\nown line\n"):
        """AGENTS.md with the team's own text above the block init writes."""
        self.put(self.agents, own)
        self.assertEqual(call(init.project_rules, self.root, "project")[0], 0)

    def body(self):
        parts = rules_block.parse(self.read(self.agents).decode())
        self.assertNotIn(parts, (None, rules_block.BROKEN))
        return parts


class IntegrationRulesInTheProjectBlock(Project):
    """Requirement: Integration rules in the project block."""

    def test_sections_in_name_order_written_by_init(self):
        self.integration("zeta", MARKER.replace("marker-check", "zeta"), "zeta rules\r\n")
        self.integration("alpha", MARKER.replace("marker-check", "alpha"), "alpha rules")
        self.put(self.cfg, "integrations: zeta, alpha\n")
        code, out = call(init.run, self.root, yes=True, home=self.home)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.body()[1], base() + section("alpha", "alpha rules") + section("zeta", "zeta rules\n"))

    def test_scope_global_writes_no_section(self):
        self.integration("marker-check", MARKER, RULES)
        self.initialised()
        self.put(self.cfg, "rules.scope: global\n")
        agents = self.read(self.agents)
        code, out = self.cli("enable", "marker-check")
        self.assertEqual(code, 0, out)
        self.assertIn("rules.scope: global, the rules of marker-check are not written to AGENTS.md", out)
        self.assertEqual(self.read(self.agents), agents)
        code, out = call(init.run, self.root, yes=True, home=self.home)
        self.assertIn("the rules of marker-check are not written", out)
        self.assertEqual(self.read(self.agents), agents)

    def test_scope_global_disable_drops_a_stale_section(self):
        self.integration("marker-check", MARKER, RULES)
        self.initialised()
        self.cli("enable", "marker-check")
        self.put(self.cfg, "rules.scope: global\nintegrations: marker-check\n")
        code, out = self.cli("disable", "marker-check")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.body()[1], base())
        self.assertEqual(self.read(self.cfg), b"rules.scope: global\n")

    def test_blank_rules_give_no_section(self):
        self.integration("marker-check", MARKER, " \n\n")
        self.initialised()
        self.assertEqual(self.cli("enable", "marker-check")[0], 0)
        self.assertEqual(self.body()[1], base())


class RulesWithoutAProjectBlock(Project):
    """Requirement: Rules without a project block."""

    def test_rules_without_a_project_block_no_block_yet(self):
        self.integration("marker-check", MARKER, RULES)
        code, out = self.cli("enable", "marker-check")
        self.assertEqual(code, 0, out)
        self.assertIsNone(self.read(self.agents))
        self.assertIsNone(self.read(os.path.join(self.root, "CLAUDE.md")))
        self.assertIn("the rules of marker-check are not written", out)
        self.assertIn("solo-sdd init", out)

    def test_an_edited_block_is_drift(self):
        self.integration("marker-check", MARKER, RULES)
        self.initialised()
        text = self.read(self.agents).decode().replace("\n" + rules_block.END, "a person's line\n" + rules_block.END)
        self.put(self.agents, text)
        code, out = self.cli("enable", "marker-check")
        self.assertEqual(code, 0, out)
        self.assertIn("drift", out)
        self.assertEqual(self.read(self.agents).decode(), text)
        self.assertEqual(self.read(self.cfg), b"integrations: marker-check\n")

    def test_a_write_that_would_fail_is_refused_first(self):
        self.integration("marker-check", MARKER, RULES)
        self.initialised()
        self.put(self.cfg, "# c\n")
        agents = self.read(self.agents)
        os.chmod(self.cfg, 0o444)
        code, out = self.cli("enable", "marker-check")
        self.assertEqual((code, self.read(self.agents), self.read(self.cfg)), (1, agents, b"# c\n"), out)
        os.chmod(self.cfg, 0o644)
        record = os.path.join(self.root, init.RECORD)
        os.chmod(record, 0o444)
        code, out = self.cli("enable", "marker-check")
        self.assertEqual((code, self.read(self.agents), self.read(self.cfg)), (1, agents, b"# c\n"), out)
        self.assertIn("cannot write solo-sdd/rules-block: not writable", out)

    def test_scope_global_keeps_the_base_rules_of_an_older_block(self):
        self.integration("marker-check", MARKER, RULES)
        self.put(self.agents, "own\n\n" + rules_block.block("old rules\n" + section("marker-check", RULES)))
        with open(os.path.join(self.root, init.RECORD), "w") as f:
            f.write(init._digest("old rules\n" + section("marker-check", RULES)) + "\n")
        self.put(self.cfg, "rules.scope: global\nintegrations: marker-check\n")
        self.assertEqual(self.cli("disable", "marker-check")[0], 0)
        self.assertEqual(self.body()[1], "old rules\n")
        agents = self.read(self.agents)
        self.assertEqual(self.cli("enable", "marker-check")[0], 0)
        self.assertEqual(self.read(self.agents), agents)

    def test_erased_markers_are_drift(self):
        self.integration("marker-check", MARKER, RULES)
        self.initialised()
        self.put(self.agents, "own\n")
        code, out = self.cli("enable", "marker-check")
        self.assertEqual(code, 0, out)
        self.assertIn("drift   AGENTS.md — the solo-sdd markers were erased", out)
        self.assertNotIn("solo-sdd init writes it", out)

    def test_an_unreadable_agents_md_leaves_the_config(self):
        self.integration("marker-check", MARKER, RULES)
        with open(self.agents, "wb") as f:
            f.write(b"own \xff\n")
        self.put(self.cfg, "# c\n")
        code, out = self.cli("enable", "marker-check")
        self.assertEqual((code, self.read(self.cfg)), (1, b"# c\n"), out)
        self.assertIn("cannot read AGENTS.md: not UTF-8", out)


class RulesTextRefused(Project):
    """Requirement: Rules text refused. Every hostile rules.md leaves AGENTS.md and solo-sdd/config as they were."""

    def refused(self, rules, why):
        path = self.integration("marker-check", MARKER, rules)
        self.initialised()
        self.put(self.cfg, "# c\n")
        agents = self.read(self.agents)
        code, out = self.cli("enable", "marker-check")
        self.assertEqual(code, 1, out)
        self.assertIn("solo-sdd/integrations/marker-check/rules.md", out)
        self.assertIn(why, out)
        self.assertEqual((self.read(self.agents), self.read(self.cfg)), (agents, b"# c\n"))
        return path

    def test_rules_text_refused_marker_forms_a_markdown_reader_sees(self):
        """The scenario A marker inside the rules is stand step 3; here the forms of a marker line it does not try."""
        for text, at in (("<!-- solo-sdd:begin -->\n", ":1:"), ("x\n<!-- solo-sdd:end -->  \t\n", ":2:"),
                         ("x\r\n<!-- solo-sdd:end -->\r\n", ":2:"), ("<!-- solo-sdd:end -->", ":1:"),
                         ("x\r<!-- solo-sdd:end -->\n", ":2:")):
            with self.subTest(text=text):
                self.refused(text, at + " the solo-sdd block marker <!-- solo-sdd:")
                self.tearDown()
                self.setUp()

    def test_size_utf8_link_and_fifo(self):
        self.refused("x" * (I.RULES_MAX_BYTES + 1), "larger than 8192 bytes")
        self.tearDown()
        self.setUp()
        self.refused(b"ok\n\xff\n", "not UTF-8 text at byte 3")
        self.tearDown()
        self.setUp()
        secret = os.path.join(self.tmp, "secret")
        self.put(secret, "a secret\n")
        path = self.integration("marker-check", MARKER)
        os.symlink(secret, os.path.join(path, "rules.md"))
        self.refused(None, "a link, not the file itself")
        self.assertNotIn(b"a secret", self.read(self.agents))
        self.tearDown()
        self.setUp()
        path = self.integration("marker-check", MARKER)
        os.mkfifo(os.path.join(path, "rules.md"))
        self.refused(None, "not a regular file")

    def test_the_size_limit_itself_is_accepted(self):
        self.integration("marker-check", MARKER, "x" * (I.RULES_MAX_BYTES - 1) + "\n")
        self.initialised()
        self.assertEqual(self.cli("enable", "marker-check")[0], 0)

    def test_rules_text_refused_disabling_the_broken_one(self):
        path = self.integration("marker-check", MARKER, RULES)
        self.initialised()
        self.cli("enable", "marker-check")
        with open(os.path.join(path, "rules.md"), "w") as f:
            f.write("<!-- solo-sdd:end -->\n")
        code, out = self.cli("disable", "marker-check")
        self.assertEqual(code, 0, out)
        self.assertEqual(self.body()[1], base())

    def test_init_refuses_a_broken_one_before_any_write(self):
        self.integration("marker-check", MARKER, b"\xff")
        self.put(self.cfg, "integrations: marker-check\n")
        code, out = call(init.run, self.root, yes=True, home=self.home)
        self.assertEqual(code, 1, out)
        self.assertIn("rules.md: not UTF-8 text at byte 0; nothing written", out)
        self.assertIsNone(self.read(self.agents))
        self.assertFalse(os.path.exists(os.path.join(self.root, "solo-sdd", "project.md")))
        code, out = call(init.run, self.root, {"rules.scope": "global"}, True, True, home=self.home)
        self.assertEqual((code, self.read(self.cfg)), (1, b"integrations: marker-check\n"), out)

    def test_a_lone_cr_keeps_the_block_in_step_with_its_record(self):
        self.integration("marker-check", MARKER, "a\r\r\nb\r")
        self.initialised()
        self.assertEqual(self.cli("enable", "marker-check")[0], 0)
        self.assertEqual(self.body()[1], base() + section("marker-check", "a\n\nb\n"))
        code, out = call(init.project_rules, self.root, "project",
                         I.rules_sections(I.find_integrations(self.root, self.home), ["marker-check"]))
        self.assertEqual((code, out), (0, ""))


class ReviewAndAuditMaterial(Project):
    """Requirement: Review and audit material."""

    def check(self, *args):
        with mock.patch.object(integration_run, "execute", side_effect=AssertionError("a command started")):
            return call(integration_run.run, list(args), self.root, self.home)

    def test_review_and_audit_material_nothing_enabled_and_failures(self):
        """The scenario Material listed is stand step 5; here the other outcomes, with no process started at all."""
        with mock.patch.object(integration_run.subprocess, "Popen", side_effect=AssertionError("a process started")):
            self.assertEqual(self.check("--point", "audit"), (0, "no integrations enabled\n"))
            self.integration("style-notes", STYLE)
            self.put(self.cfg, "integrations: style-notes\n")
            self.assertEqual(self.check("--point", "audit"), (0, "no enabled integration has the point audit\n"))
        self.integration("style-notes", STYLE.replace("review", "audit"))
        self.put(self.cfg, "integrations: style-notes, no-such\n")
        code, out = self.check("--point", "audit")
        self.assertEqual(code, 1)
        self.assertEqual(out, "FAIL no-such: not found\nFAIL style-notes: material method.md not found\n")
        self.assertIsNone(integration_run.run(["--point", "review", "--change", "x"], self.root, self.home))

    def test_changed_filters_by_applies(self):
        shutil.rmtree(os.path.join(self.root, ".git"))
        env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1", HOME=self.home)

        def git(*args):
            subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "-c", "commit.gpgsign=false",
                            *args], cwd=self.root, env=env, check=True, capture_output=True, stdin=subprocess.DEVNULL)
        path = self.integration("style-notes", STYLE + "applies: *.py\n")
        self.put(os.path.join(path, "method.md"), "m\n")
        self.put(self.cfg, "integrations: style-notes\n")
        git("init", "-q", "-b", "main")
        git("add", "-A")
        git("commit", "-q", "-m", "base")
        self.put(os.path.join(self.root, "README.md"), "x\n")
        with mock.patch.dict(os.environ, env):
            self.assertEqual(self.check("--point", "review", "--changed"),
                             (0, "no integration applies to the changed files\n"))
            self.put(os.path.join(self.root, "app.py"), "x = 1\n")
            code, out = self.check("--point", "review", "--changed")
        self.assertEqual(code, 0)
        self.assertTrue(out.startswith("MATERIAL style-notes: ") and out.endswith("method.md\n"), out)


def check_sequence(run, before, after, rules, ops):
    """Runs ops ((enable|disable, name)) by run on a project whose AGENTS.md is before + the block + after, with the
    rules texts of rules; after each call the block holds exactly the sections of the enabled names in name order,
    the text around the block keeps its bytes and a repeated call changes nothing."""
    tmp = tempfile.mkdtemp(prefix="integration-rules-property-")
    try:
        root, home = os.path.join(tmp, "p"), os.path.join(tmp, "h")
        os.makedirs(os.path.join(root, "solo-sdd", "changes"))
        os.makedirs(home)
        for name, text in rules.items():
            path = os.path.join(root, "solo-sdd", "integrations", name)
            os.makedirs(path)
            with open(os.path.join(path, "integration"), "w") as f:
                f.write(MARKER.replace("marker-check", name))
            with open(os.path.join(path, "rules.md"), "w", newline="") as f:
                f.write(text)
        agents = os.path.join(root, "AGENTS.md")
        with open(agents, "w", newline="") as f:
            f.write(before + rules_block.block(base()) + after)
        with open(os.path.join(root, init.RECORD), "w") as f:
            f.write(init._digest(base()) + "\n")
        enabled = set()
        for op, name in ops:
            enabled = enabled | {name} if op == "enable" else enabled - {name}
            with contextlib.redirect_stdout(io.StringIO()):
                assert run([op, name], root, home) == 0, (op, name)
                with open(agents, "rb") as f:
                    once = f.read()
                assert run([op, name], root, home) == 0, (op, name)
            with open(agents, "rb") as f:
                assert f.read() == once, (op, name, "a repeated call changed AGENTS.md")
            parts = rules_block.parse(once.decode())
            assert parts not in (None, rules_block.BROKEN), once
            assert (parts[0], parts[2]) == (before, after), (op, name, "the text around the block changed")
            want = base() + "".join(section(n, rules[n]) for n in sorted(enabled))
            assert parts[1] == want, (op, name, parts[1][len(base()):], want[len(base()):])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def appending_run(args, cwd, home):
    """A mutant: enable appends the section to the block body as it stands, never removing an old one."""
    path = os.path.join(cwd, "AGENTS.md")
    with open(path, newline="") as f:
        text = f.read()
    code = I.run(args, cwd, home)
    if args[0] == "enable":
        with open(os.path.join(cwd, "solo-sdd", "integrations", args[1], "rules.md"), newline="") as f:
            rules = f.read()
        before, body, after = rules_block.parse(text)
        with open(path, "w", newline="") as f:
            f.write(before + rules_block.block(body + section(args[1], rules)) + after)
    return code


NAMES = ("alpha", "beta", "gamma")
LINE = st.text(st.characters(blacklist_categories=("Cs",), blacklist_characters="\n"), max_size=12)
AROUND = st.lists(LINE, max_size=3).map(lambda ls: "".join(ln + "\n" for ln in ls)).filter(
    lambda t: rules_block.marker(t) is None)
RULES_TEXT = st.lists(st.text(st.characters(blacklist_categories=("Cs",), blacklist_characters="\n"), max_size=20),
                      min_size=1, max_size=4).map(lambda ls: "\r\n".join(ls) if len(ls) % 2 else "\n".join(ls)).filter(
    lambda t: t.strip() and rules_block.marker(t.replace("\r", "\n")) is None)


class IntegrationRulesInTheProjectBlockProperty(unittest.TestCase):
    """Requirement: Integration rules in the project block (property)."""

    @marks.slow
    @hsettings(max_examples=marks.examples(80), deadline=None)
    @given(AROUND, st.one_of(st.just(""), AROUND), st.fixed_dictionaries({n: RULES_TEXT for n in NAMES}),
           st.lists(st.tuples(st.sampled_from(("enable", "disable")), st.sampled_from(NAMES)), max_size=8))
    def test_integration_rules_in_the_project_block_property(self, before, after, rules, ops):
        check_sequence(I.run, before, after, rules, ops)

    def test_the_property_rejects_an_appending_enable(self):
        with self.assertRaises(AssertionError):
            check_sequence(appending_run, "own\n", "", {n: "r\n" for n in NAMES}, [("enable", "alpha"), ("enable", "beta")])


if __name__ == "__main__":
    unittest.main()
