#!/usr/bin/env python3
"""solo-sdd validate: the solo-sdd/ tree and its rules, on toy trees in temporary folders."""
import contextlib, io, json, os, pathlib, re, subprocess, sys, tempfile, unittest
import marks
from unittest import mock

from hypothesis import example, given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))
from solo_sdd import process_cli as pc, process_format as pf  # noqa: E402

PROPOSAL = """# Proposal

## Why

A reason.

## What Changes

- A change.

## Capabilities

### New Capabilities
- `foo`: a thing.

## Impact

`foo.py`.

## Out of Scope

- `other`.

## Depends On

none

## Source

"Do it" (the owner).
"""
VERIFICATION = "## Live Scenario\n\nRun it.\n\n## Needs\n\nnone\n\n## Fallback\n\nNot needed.\n"
TASKS = "## 1. Code\n\n- [ ] 1.1 Code\n\n## 2. Acceptance\n\n- [ ] 2.1 Live\n- [ ] 2.2 Archive\n"
REQ = "### Requirement: %s\nThe system SHALL %s.\n\n#### Scenario: S\n- **WHEN** a\n- **THEN** b\n"
PURPOSE = "## Purpose\n\nDefines the foo capability of the toy project for the validate tests.\n\n"
DELTA = PURPOSE + "## ADDED Requirements\n\n" + REQ % ("X", "do x")
MAIN = "# foo\n\n## Purpose\n\nFoo.\n\n## Requirements\n\n" + REQ % ("Y", "do y")


def write(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def valid_tree(root, change="demo"):
    write(root, "solo-sdd/project.md", "Intent: a toy.\n")
    write(root, "solo-sdd/specs/bar/spec.md", MAIN.replace("# foo", "# bar"))
    put_change(root, change)


def put_change(root, change, **over):
    files = {"proposal.md": PROPOSAL, "verification.md": VERIFICATION, "tasks.md": TASKS,
             "specs/foo/spec.md": DELTA}
    files.update(over)
    for rel, text in files.items():
        if text is not None:
            write(root, "solo-sdd/changes/%s/%s" % (change, rel), text)


def cli(cwd, *args, path=None):
    env = dict(os.environ, PYTHONPATH=str(REPO))
    if path is not None:
        env["PATH"] = path
    p = subprocess.run([sys.executable, "-m", "solo_sdd", "validate", *args], cwd=cwd, env=env,
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode, p.stdout


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.root = self._t.name
        valid_tree(self.root)

    def errs(self, change=None):
        return pf.validate(pathlib.Path(self.root) / "solo-sdd", change)

    def rules(self, change=None):
        return [(f, r) for f, r, _ in self.errs(change)]


class ProcessTree(Base):
    def test_valid_tree(self):
        self.assertEqual(cli(self.root, "--all"), (0, "0 errors\n"))

    def test_missing_artifact(self):
        os.remove(os.path.join(self.root, "solo-sdd/changes/demo/verification.md"))
        code, out = cli(self.root, "--all")
        self.assertEqual(code, 1)
        self.assertIn("solo-sdd/changes/demo/verification.md: missing file: verification.md\n", out)
        self.assertTrue(out.endswith("1 errors\n"), out)

    def test_no_project_file(self):
        os.remove(os.path.join(self.root, "solo-sdd/project.md"))
        self.assertEqual(self.errs(), [("solo-sdd/project.md", "missing file", "project.md")])

    def test_found_from_a_subfolder(self):
        sub = os.path.join(self.root, "src", "deep")
        os.makedirs(sub)
        self.assertEqual(cli(sub), (0, "0 errors\n"))

    def test_folder_named_solo_sdd_without_tree_is_not_a_tree(self):
        with tempfile.TemporaryDirectory() as t:
            os.makedirs(os.path.join(t, "solo-sdd", "openspec"))
            self.assertIsNone(pf.find_tree(os.path.join(t, "solo-sdd")))


class Sections(Base):
    def test_no_source(self):
        put_change(self.root, "demo", **{"proposal.md": PROPOSAL.split("## Source")[0]})
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/proposal.md", "missing section", "Source")])

    def test_template_comment_only(self):
        text = PROPOSAL.replace("- `other`.", "<!-- What this change does not do.\n     Name the neighbours. -->")
        put_change(self.root, "demo", **{"proposal.md": text})
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/proposal.md", "empty section", "Out of Scope")])

    def test_header_inside_comment(self):
        text = PROPOSAL.split("## Source")[0] + "<!--\n## Source\n\nquote\n-->\n"
        put_change(self.root, "demo", **{"proposal.md": text})
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/proposal.md", "missing section", "Source")])

    def test_comment_marker_in_code_is_code(self):
        text = PROPOSAL.replace("A reason.", "We parse `<!--` markers.\n\n```html\n<!-- open\n```")
        put_change(self.root, "demo", **{"proposal.md": text,
                                         "tasks.md": TASKS.replace("1.1 Code", "1.1 Code (with `<!--`)")})
        self.assertEqual(self.errs(), [])

    def test_unclosed_comment_is_empty(self):
        put_change(self.root, "demo", **{"proposal.md": PROPOSAL.replace('"Do it" (the owner).', "<!-- a quote")})
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/proposal.md", "empty section", "Source")])

    def test_verification_sections(self):
        put_change(self.root, "demo", **{"verification.md": "## Live Scenario\n\nRun.\n\n## Needs\n\n"})
        self.assertEqual([i for _, _, i in self.errs()], ["Needs", "Fallback"])


class Tasks(Base):
    def test_eleven_tasks(self):
        text = "## 1. Code\n\n" + "".join("- [ ] 1.%d t\n" % i for i in range(9)) + "\n## 2. Acceptance\n\n- [x] a\n- [ ] b\n"
        put_change(self.root, "demo", **{"tasks.md": text})
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/tasks.md", "too many tasks", "11 > 10")])

    def test_ten_tasks_pass(self):
        text = "## 1. Code\n\n" + "".join("- [ ] 1.%d t\n" % i for i in range(8)) + "\n## 2. Acceptance\n\n- [x] a\n- [ ] b\n"
        put_change(self.root, "demo", **{"tasks.md": text})
        self.assertEqual(self.errs(), [])

    def test_comments_do_not_count(self):
        text = ("## 1. Code\n\n- [ ] a\n<!--\n" + "- [ ] c\n" * 11 + "-->\n\n## 2. Acceptance <!-- the end -->\n\n- [ ] b\n")
        put_change(self.root, "demo", **{"tasks.md": text})
        self.assertEqual(self.errs(), [])
        put_change(self.root, "demo", **{"tasks.md": "## 1. Code\n\n- [ ] a\n<!-- ## 2. Acceptance -->\n"})
        self.assertEqual(self.rules(), [("solo-sdd/changes/demo/tasks.md", "no Acceptance group")])

    def test_no_acceptance_group(self):
        put_change(self.root, "demo", **{"tasks.md": "## 1. Code\n\n- [ ] a\n\n## 2. Docs\n\n- [ ] b\n"})
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/tasks.md", "no Acceptance group", "last group: 2. Docs")])


class RequirementFormat(Base):
    def delta(self, body):
        put_change(self.root, "demo", **{"specs/foo/spec.md": PURPOSE + body})
        return self.errs()

    def test_long_requirement(self):
        got = self.delta("## ADDED Requirements\n\n" + REQ % ("Long", "a" * 483))
        self.assertEqual(got, [("solo-sdd/changes/demo/specs/foo/spec.md", "requirement too long", "Long: 501 > 500")])

    def test_scenario_without_then(self):
        got = self.delta("## ADDED Requirements\n\n### Requirement: X\nThe system SHALL x.\n\n#### Scenario: E\n- **WHEN** a\n")
        self.assertEqual(got, [("solo-sdd/changes/demo/specs/foo/spec.md", "scenario step", 'X: scenario "E" has no THEN')])

    def test_unknown_delta_section(self):
        got = self.delta("## DEPRECATED Requirements\n\n" + REQ % ("Old", "x"))
        self.assertEqual(got, [("solo-sdd/changes/demo/specs/foo/spec.md", "not a delta section",
                                'Old: under "## DEPRECATED Requirements"')])

    def test_header_without_space(self):
        got = self.delta("## ADDED Requirements\n\n" + (REQ % ("Y", "y")).replace("### R", "###R"))
        self.assertEqual(got, [("solo-sdd/changes/demo/specs/foo/spec.md", "header without a space after ###", "Y")])

    def test_requirement_without_scenario(self):
        got = self.delta("## ADDED Requirements\n\n### Requirement: Bare\nThe system SHALL x.\n")
        self.assertEqual(got, [("solo-sdd/changes/demo/specs/foo/spec.md", "no scenario", "Bare")])

    def test_removed_needs_no_scenario_and_fence_is_skipped(self):
        write(self.root, "solo-sdd/specs/foo/spec.md", MAIN.replace("Requirement: Y", "Requirement: Gone"))
        got = self.delta("## REMOVED Requirements\n\n### Requirement: Gone\n**Reason**: old.\n\n"
                         "## ADDED Requirements\n\n" + REQ % ("X", "x\n```\n" + "z" * 900 + "\n```\ntail"))
        self.assertEqual(got, [])

    def test_main_spec_checked(self):
        write(self.root, "solo-sdd/specs/bar/spec.md", MAIN.replace("do y", "a" * 600))
        self.assertEqual(self.rules(), [("solo-sdd/specs/bar/spec.md", "requirement too long")])

    def test_main_modified_by_open_change_not_length_checked(self):
        write(self.root, "solo-sdd/specs/bar/spec.md", MAIN.replace("do y", "a" * 600))
        put_change(self.root, "mod", **{"specs/bar/spec.md": "## MODIFIED Requirements\n\n" + REQ % ("Y", "short")})
        self.assertEqual(self.errs(), [])

    def test_same_verdict_as_removed_tests(self):
        """Same verdict as the removed tests: the six pairs tests/test_spec_length.py and
        tests/test_spec_format.py reported on this toy tree, fixed when they were deleted."""
        files = {
            "changes/demo/specs/foo/spec.md": PURPOSE + "## ADDED Requirements\n\n" + REQ % ("Long", "a" * 600)
            + "\n### Requirement: NoThen\nThe system SHALL x.\n\n#### Scenario: E\n- **WHEN** a\n"
            + "\n### Requirement: NoWhen\nThe system SHALL x.\n\n#### Scenario: F\n- **THEN** a\n"
            + "\n## DEPRECATED Requirements\n\n" + REQ % ("Old", "x"),
            "specs/bar/spec.md": MAIN.replace("### Requirement: Y", "###Requirement: Y")
            + "\n" + REQ % ("MainLong", "b" * 700),
        }
        with tempfile.TemporaryDirectory() as t:
            for rel, text in files.items():
                write(t, "solo-sdd/" + rel, text)
            got = {(f[len("solo-sdd/"):], i.split(": ")[0]) for f, r, i in pf.validate(pathlib.Path(t) / "solo-sdd")
                   if r != "missing file"}
        delta = "changes/demo/specs/foo/spec.md"
        self.assertEqual(got, {(delta, "Long"), (delta, "NoThen"), (delta, "NoWhen"), (delta, "Old"),
                               ("specs/bar/spec.md", "MainLong"), ("specs/bar/spec.md", "Y")})

    @settings(max_examples=150, deadline=None)
    @given(n=st.one_of(st.integers(495, 506), st.integers(1, 1200)), emoji=st.integers(0, 600))
    @example(n=500, emoji=0)
    @example(n=501, emoji=0)
    @example(n=501, emoji=250)
    def test_requirement_format_length_property(self, n, emoji):
        """Requirement format: the length rule fires exactly when the text is over 500 UTF-16 units."""
        k = min(emoji, n // 2)
        text = "\U0001F600" * k + "a" * (n - 2 * k)
        with tempfile.TemporaryDirectory() as t:
            p = write(t, "solo-sdd/specs/foo/spec.md",
                      "# foo\n\n## Requirements\n\n### Requirement: R\n%s\n\n#### Scenario: S\n- **WHEN** a\n- **THEN** b\n" % text)
            fired = [e for e in pf.check_spec(p, "x", False) if e[1] == "requirement too long"]
        self.assertEqual(bool(fired), n > 500, (n, k))


class Purpose(Base):
    def test_new_capability_without_purpose(self):
        put_change(self.root, "demo", **{"specs/new-thing/spec.md": "## ADDED Requirements\n\n" + REQ % ("N", "n")})
        self.assertIn(("solo-sdd/changes/demo/specs/new-thing/spec.md", "new capability Purpose",
                       "new-thing: no ## Purpose at the start"), self.errs())

    def test_purpose_with_comment_marker_in_code(self):
        put_change(self.root, "demo", **{"specs/foo/spec.md": DELTA.replace(
            "Defines the foo capability", "Parses `<!--` markers <!-- a note --> and defines the foo capability")})
        self.assertEqual(self.errs(), [])

    def test_short_purpose_and_existing_capability(self):
        put_change(self.root, "demo", **{"specs/foo/spec.md": "## Purpose\n\nShort.\n\n## ADDED Requirements\n\n" + REQ % ("N", "n"),
                                         "specs/bar/spec.md": "## ADDED Requirements\n\n" + REQ % ("Z", "z")})
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/specs/foo/spec.md", "new capability Purpose", "foo: 6 < 50 characters")])

    def test_capability_brought_by_dependency(self):
        new = "specs/new-thing/spec.md"
        put_change(self.root, "a", **{new: DELTA, "specs/foo/spec.md": None})
        put_change(self.root, "demo", **{new: "## ADDED Requirements\n\n" + REQ % ("N", "n")})
        self.assertEqual(self.rules(), [("solo-sdd/changes/demo/" + new, "new capability Purpose")])
        put_change(self.root, "demo", **{"proposal.md": PROPOSAL.replace("## Depends On\n\nnone", "## Depends On\n\na")})
        self.assertEqual(self.errs(), [])

    def test_change_without_deltas(self):
        import shutil
        shutil.rmtree(os.path.join(self.root, "solo-sdd/changes/demo/specs"))
        self.assertEqual(self.rules(), [("solo-sdd/changes/demo/proposal.md", "no deltas")])
        put_change(self.root, "demo", **{"specs/foo/spec.md": None,
                                         "proposal.md": PROPOSAL.replace("### New Capabilities", "Specs: none\n\n### New")})
        self.assertEqual(self.errs(), [])

    def test_specs_none_in_comment_or_fence_and_empty_deltas(self):
        import shutil
        shutil.rmtree(os.path.join(self.root, "solo-sdd/changes/demo/specs"))
        for hidden in ("<!-- Specs: none -->", "```\nSpecs: none\n```"):
            put_change(self.root, "demo", **{"specs/foo/spec.md": None,
                                             "proposal.md": PROPOSAL.replace("### New Capabilities", hidden + "\n\n### New")})
            self.assertEqual(self.rules(), [("solo-sdd/changes/demo/proposal.md", "no deltas")], hidden)
        put_change(self.root, "demo")
        for text, purpose in (("", [("solo-sdd/changes/demo/specs/foo/spec.md", "new capability Purpose")]), (PURPOSE, [])):
            put_change(self.root, "demo", **{"specs/foo/spec.md": text})
            self.assertEqual(self.rules(), [("solo-sdd/changes/demo/proposal.md", "no deltas")] + purpose, text)
        put_change(self.root, "demo", **{"specs/foo/spec.md": PURPOSE + "## RENAMED Requirements\n\n- FROM: `### Requirement: A`\n- TO: `### Requirement: B`\n"})
        write(self.root, "solo-sdd/specs/foo/spec.md", MAIN.replace("Requirement: Y", "Requirement: A"))
        self.assertEqual(self.errs(), [])


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in pathlib.Path(root).rglob("*") if p.is_file()}


class ValidateDryRunsDeltas(Base):
    BAR = "solo-sdd/changes/demo/specs/bar/spec.md"

    def test_a_missing_name(self):
        put_change(self.root, "demo", **{"specs/bar/spec.md": "## MODIFIED Requirements\n\n" + REQ % ("Missing", "m")})
        before = snapshot(self.root)
        self.assertEqual(self.errs("demo"), [(self.BAR, "delta", "solo-sdd/specs/bar/spec.md: MODIFIED Missing: not in the main spec")])
        code, out = cli(self.root, "demo")
        self.assertEqual(code, 1)
        self.assertIn("%s: delta: " % self.BAR, out)
        self.assertEqual(snapshot(self.root), before)

    def test_removed_renamed_and_added_names(self):
        for delta, item in (("## REMOVED Requirements\n\n### Requirement: Gone\n", "REMOVED Gone"),
                            ("## RENAMED Requirements\n\n- FROM: `### Requirement: Gone`\n- TO: `### Requirement: New`\n", "RENAMED Gone"),
                            ("## ADDED Requirements\n\n" + REQ % ("Y", "y"), "ADDED Y")):
            put_change(self.root, "demo", **{"specs/bar/spec.md": delta})
            self.assertEqual([(f, r, i.split(":")[1].strip()) for f, r, i in self.errs("demo")],
                             [(self.BAR, "delta", item)], item)

    def test_provided_by_a_dependency(self):
        put_change(self.root, "a", **{"specs/foo/spec.md": None, "specs/bar/spec.md":
                                      "## ADDED Requirements\n\n" + REQ % ("Z", "z") + "\n## REMOVED Requirements\n\n### Requirement: Y\n"})
        b = {"specs/foo/spec.md": None, "specs/bar/spec.md": "## MODIFIED Requirements\n\n" + REQ % ("Z", "zz")}
        put_change(self.root, "b", **b)
        self.assertEqual(self.rules("b"), [("solo-sdd/changes/b/specs/bar/spec.md", "delta")])
        depends = PROPOSAL.replace("## Depends On\n\nnone", "## Depends On\n\na")
        put_change(self.root, "b", **dict(b, **{"proposal.md": depends}))
        self.assertEqual(self.errs("b"), [])
        put_change(self.root, "b", **{"proposal.md": depends, "specs/foo/spec.md": None,
                                      "specs/bar/spec.md": "## MODIFIED Requirements\n\n" + REQ % ("Y", "yy")})
        self.assertEqual(self.rules("b"), [("solo-sdd/changes/b/specs/bar/spec.md", "delta")])
        self.assertEqual(cli(self.root, "--all")[1].count(": delta: "), 1)

    def test_a_dependency_chain(self):
        def bar(text, deps="none"):
            return {"specs/foo/spec.md": None, "specs/bar/spec.md": text,
                    "proposal.md": PROPOSAL.replace("## Depends On\n\nnone", "## Depends On\n\n" + deps)}
        put_change(self.root, "c1", **bar("## ADDED Requirements\n\n" + REQ % ("X1", "x")))
        put_change(self.root, "c2", **bar("## MODIFIED Requirements\n\n" + REQ % ("X1", "xx") +
                                          "\n## ADDED Requirements\n\n" + REQ % ("X2", "y"), "c1"))
        for deps in ("c2", "c2, c1", "c1, c2", "c3, c2"):
            put_change(self.root, "c3", **bar("## MODIFIED Requirements\n\n" + REQ % ("X2", "yy"), deps))
            self.assertEqual(self.errs("c3"), [], deps)
        self.assertEqual(cli(self.root, "--all"), (0, "0 errors\n"))


POOL = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon"]


def model_refuses(main, added, modified, removed, renamed):
    """An oracle written apart from process_cli.apply: the names a delta may and may not use."""
    present = set(main or ())
    if any(to in added for _, to in renamed):
        return True
    for old, to in renamed:
        if old not in present or to in present:
            return True
        present = (present - {old}) | {to}
    if any(n not in present for n in removed):
        return True
    present -= set(removed)
    return any(n not in present for n in modified) or any(n in present for n in added)


class ValidateDryRunsDeltasProperty(unittest.TestCase):
    @marks.slow
    @settings(max_examples=250, deadline=None)
    @given(st.data())
    def test_validate_dry_runs_deltas_agrees_with_archive(self, data):
        """Requirement Validate dry-runs deltas: validate reports a delta error exactly when archive refuses on one."""
        main = data.draw(st.none() | st.lists(st.sampled_from(POOL), unique=True), label="main")
        section = {n: data.draw(st.sampled_from(["", "ADDED", "MODIFIED", "REMOVED", "RENAMED"]), label=n) for n in POOL}
        pick = lambda k: [n for n in POOL if section[n] == k]
        targets = data.draw(st.lists(st.sampled_from(["Moved1", "Moved2"] + POOL), unique=True,
                                     min_size=len(pick("RENAMED")), max_size=len(pick("RENAMED"))), label="to")
        renamed = list(zip(pick("RENAMED"), targets))
        delta = "## Purpose\n\nDefines the foo capability of the toy project for the validate tests.\n\n"
        for kind in ("ADDED", "MODIFIED"):
            if pick(kind):
                delta += "## %s Requirements\n\n" % kind + "".join(REQ % (n, n.lower()) + "\n" for n in pick(kind))
        if pick("REMOVED"):
            delta += "## REMOVED Requirements\n\n" + "".join("### Requirement: %s\n" % n for n in pick("REMOVED"))
        if renamed:
            delta += "## RENAMED Requirements\n\n" + "".join(
                "- FROM: `### Requirement: %s`\n- TO: `### Requirement: %s`\n" % r for r in renamed)
        main_text = None if main is None else "# foo\n\n## Purpose\n\nFoo.\n\n## Requirements\n\n" + "".join(
            REQ % (n, n.lower()) + "\n" for n in main)
        with tempfile.TemporaryDirectory() as t:
            write(t, "solo-sdd/project.md", "Intent: a toy.\n")
            put_change(t, "demo", **{"specs/foo/spec.md": delta})
            if main_text is not None:
                write(t, "solo-sdd/specs/foo/spec.md", main_text)
            got = [e for e in pf.validate(pathlib.Path(t) / "solo-sdd", "demo") if e[1] == "delta"]
        try:
            pc.apply(main_text, delta, "foo")
            archive_refuses = False
        except pc.Refused:
            archive_refuses = True
        expected = model_refuses(main, pick("ADDED"), pick("MODIFIED"), pick("REMOVED"), renamed)
        self.assertEqual((bool(got), archive_refuses), (expected, expected), (main, section, renamed, got))


class Output(Base):
    def test_without_openspec(self):
        self.assertEqual(cli(self.root, "--all", path="/usr/bin:/bin"), (0, "0 errors\n"))
        os.remove(os.path.join(self.root, "solo-sdd/project.md"))
        self.assertEqual(cli(self.root, "--all", path="/usr/bin:/bin")[0], 1)

    def test_no_external_program(self):
        os.remove(os.path.join(self.root, "solo-sdd/project.md"))
        stop = AssertionError("an external program was started")
        with mock.patch("subprocess.Popen", side_effect=stop), mock.patch("os.system", side_effect=stop), \
                mock.patch("os.posix_spawn", side_effect=stop), mock.patch("os.execv", side_effect=stop), \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pf.run(["--all"], self.root), 1)
        self.assertIn("solo-sdd/project.md: missing file: project.md", out.getvalue())

    def test_json(self):
        os.remove(os.path.join(self.root, "solo-sdd/project.md"))
        put_change(self.root, "demo", **{"tasks.md": "## 1. Code\n\n- [ ] a\n"})
        code, out = cli(self.root, "--all", "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out), [
            {"file": "solo-sdd/project.md", "rule": "missing file", "item": "project.md"},
            {"file": "solo-sdd/changes/demo/tasks.md", "rule": "no Acceptance group", "item": "last group: 1. Code"}])

    def test_error_line(self):
        put_change(self.root, "demo", **{"tasks.md": "## 1. Code\n\n- [ ] a\n"})
        self.assertEqual(cli(self.root), (1, "solo-sdd/changes/demo/tasks.md: no Acceptance group: last group: 1. Code\n1 errors\n"))

    def test_one_change(self):
        put_change(self.root, "bad", **{"tasks.md": "## 1. Code\n\n- [ ] a\n"})
        os.remove(os.path.join(self.root, "solo-sdd/project.md"))
        self.assertEqual(cli(self.root, "demo"), (0, "0 errors\n"))
        code, out = cli(self.root, "bad")
        self.assertEqual((code, out.count("\n")), (1, 2))
        self.assertIn("solo-sdd/changes/bad/tasks.md", out)
        self.assertEqual(cli(self.root, "nope"), (1, "solo-sdd/changes/nope: no change: nope\n1 errors\n"))

    def test_bad_ids(self):
        for cid in ("..", ".", ".hidden", "archive"):
            self.assertEqual(self.errs(cid), [("solo-sdd/changes/%s" % cid, "no change", cid)], cid)

    @unittest.skipIf(os.geteuid() == 0, "root reads everything")
    def test_unreadable_folders(self):
        put_change(self.root, "locked")
        for rel, args in (("solo-sdd/changes/locked", ["--all"]), ("solo-sdd/changes", ["--all"]),
                          ("solo-sdd/changes", ["demo"]), ("solo-sdd", ["--all"])):
            p = os.path.join(self.root, rel)
            os.chmod(p, 0)
            try:
                code, out = cli(self.root, *args)
            finally:
                os.chmod(p, 0o755)
            self.assertEqual((code, out), (1, "%s: unreadable: PermissionError\n1 errors\n" % rel), (rel, args))

    def test_no_tree(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(cli(t), (1, "no solo-sdd/ tree\n"))

    def test_bad_arguments(self):
        for args in (["--bogus"], ["a", "b"], ["a", "--all"]):
            code, out = cli(self.root, *args)
            self.assertEqual(code, 2, args)
            self.assertIn("validate [<id>] [--all] [--json]", out)


class Scope(Base):
    def test_old_archived_change(self):
        put_change(self.root, "archive/2026-01-01-old", **{"specs/foo/spec.md": DELTA.replace("do x", "a" * 600),
                                                           "verification.md": None})
        self.assertEqual(cli(self.root, "--all"), (0, "0 errors\n"))
        self.assertEqual(cli(self.root, "archive")[0], 1)

    def test_unreadable_file(self):
        (pathlib.Path(self.root) / "solo-sdd/changes/demo/tasks.md").write_bytes(b"\xff\xfe\xfa\x80")
        self.assertEqual(self.errs(), [("solo-sdd/changes/demo/tasks.md", "unreadable", "UnicodeDecodeError")])


class DocReaderCopy(unittest.TestCase):
    """global/sdd_dispatch.py reads the Live Scenario with a copy of the validator's reader: the copies match."""

    def test_copies_match(self):
        # Requirement: Tests use the block check (shared-blocks)
        r = subprocess.run([sys.executable, str(REPO / "scripts" / "sync_blocks.py"), "--check"],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
