#!/usr/bin/env python3
"""solo-sdd list, new and archive on toy solo-sdd/ trees in temporary folders."""
import contextlib, io, json, os, pathlib, subprocess, sys, tempfile, unittest
from unittest import mock

from hypothesis import given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from solo_sdd import process_cli as pc  # noqa: E402

PROPOSAL = """# Proposal

## Why

A reason.

## What Changes

- A change.

## Capabilities

### Modified Capabilities
- `export`

## Impact

`export.py`.

## Out of Scope

- `other`.

## Depends On

none

## Source

"Do it" (the owner).
"""
VERIFICATION = "## Live Scenario\n\nRun it.\n\n## Needs\n\nnone\n\n## Fallback\n\nNot needed.\n\n## Result\n\nRan it.\n"
TASKS = "## 1. Code\n\n- [x] 1.1 Code\n\n## 2. Acceptance\n\n- [ ] 2.1 Live\n- [ ] 2.2 Archive\n"
TODAY = "2026-11-09"


def req(name, text="do it"):
    return "### Requirement: %s\nThe system SHALL %s.\n\n#### Scenario: S\n- **WHEN** a\n- **THEN** b" % (name, text)


HEAD = "# export Specification\n\n## Purpose\nExports.\n\n## Requirements\n\n"


def main_spec(*names):
    return HEAD + "\n\n".join(req(n) for n in names) + "\n"


def write(root, rel, text):
    p = pathlib.Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in pathlib.Path(root).rglob("*") if p.is_file()}


class Base(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = pathlib.Path(t.name)
        self.tree = self.root / "solo-sdd"
        write(self.root, "solo-sdd/project.md", "Intent: a toy.\n")
        write(self.root, "solo-sdd/specs/export/spec.md", main_spec("Export", "Format"))

    def change(self, cid="demo", deltas=None, **over):
        files = {"proposal.md": PROPOSAL, "verification.md": VERIFICATION, "tasks.md": TASKS}
        files.update(over)
        for cap, text in (deltas or {}).items():
            files["specs/%s/spec.md" % cap] = text
        for rel, text in files.items():
            write(self.root, "solo-sdd/changes/%s/%s" % (cid, rel), text)

    def run_cli(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pc.run(list(args), cwd=str(self.root)) if args[0] != "archive" else \
                pc.archive(self.tree, args[1], "--yes" in args, today=TODAY, force="--force" in args)
        return code, out.getvalue()

    def spec(self, cap="export"):
        return (self.tree / "specs" / cap / "spec.md").read_text(encoding="utf-8")


class NewChange(Base):
    def test_a_new_id(self):
        code, out = self.run_cli("new", "add-export")
        self.assertEqual(code, 0, out)
        folder = self.tree / "changes" / "add-export"
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ["proposal.md", "tasks.md", "verification.md"])
        for name in ("proposal.md", "verification.md", "tasks.md"):
            self.assertIn("solo-sdd/changes/add-export/%s\n" % name, out)
        self.assertIn("## Source", (folder / "proposal.md").read_text())
        self.assertIn("## Fallback", (folder / "verification.md").read_text())
        tasks = (folder / "tasks.md").read_text()
        self.assertIn("solo-sdd validate add-export", tasks)
        self.assertIn("solo-sdd archive add-export --yes", tasks)
        self.assertEqual(self.run_cli("list")[1], "add-export 0/2\n")

    def test_an_existing_open_id(self):
        self.change("add-export")
        before = snapshot(self.root)
        self.assertEqual(self.run_cli("new", "add-export"), (1, "change exists: solo-sdd/changes/add-export\n"))
        self.assertEqual(snapshot(self.root), before)

    def test_an_archived_id(self):
        (self.tree / "changes" / "archive" / "2026-11-01-add-export").mkdir(parents=True)
        before = snapshot(self.root)
        code, out = self.run_cli("new", "add-export")
        self.assertEqual((code, snapshot(self.root)), (1, before))
        self.assertIn("solo-sdd/changes/archive/2026-11-01-add-export", out)
        self.assertFalse((self.tree / "changes" / "add-export").exists())

    def test_not_kebab_case(self):
        for bad in ("Add_Export", "add--export", "../escape", "add-", "1.0", "archive"):
            code, out = self.run_cli("new", bad)
            self.assertEqual(code, 1, bad)
            self.assertIn("not a kebab-case id or reserved", out)
        self.assertFalse((self.tree / "changes").exists())
        self.assertFalse((self.root / "escape").exists())

    def test_no_tree(self):
        with tempfile.TemporaryDirectory() as t, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(pc.run(["new", "x"], cwd=t), 1)
        self.assertEqual(out.getvalue(), "no solo-sdd/ tree\n")


class ListChanges(Base):
    def test_two_open_changes(self):
        self.change("a", **{"tasks.md": "## 1. C\n\n- [x] 1\n- [X] 2\n- [ ] 3\n\n## 2. Acceptance\n\n- [ ] 4\n- [ ] 5\n"})
        write(self.root, "solo-sdd/changes/a/CLAIM", "claude\n")
        self.change("b", **{"tasks.md": "## 1. Acceptance\n\n- [ ] 1\n- [ ] 2\n- [ ] 3\n<!-- - [x] commented -->\n"})
        self.change("c")
        write(self.root, "solo-sdd/changes/c/WAITING", "keys\n")
        write(self.root, "solo-sdd/changes/c/CLAIM", "codex\n")
        write(self.root, "solo-sdd/changes/archive/2026-11-01-old/tasks.md", "- [ ] 1\n")
        self.assertEqual(self.run_cli("list"), (0, "a 2/5 CLAIM\nb 0/3\nc 1/3 CLAIM WAITING\n"))

    def test_json(self):
        self.change("a")
        write(self.root, "solo-sdd/changes/a/WAITING", "x\n")
        code, out = self.run_cli("list", "--json")
        self.assertEqual(json.loads(out), [{"id": "a", "done": 1, "total": 3, "claim": False, "waiting": True}])

    def test_specs(self):
        write(self.root, "solo-sdd/specs/cli/spec.md", main_spec("A", "B", "C").replace("# export", "# cli"))
        self.assertEqual(self.run_cli("list", "--specs"), (0, "cli 3\nexport 2\n"))
        self.assertEqual(json.loads(self.run_cli("list", "--specs", "--json")[1]),
                         [{"id": "cli", "requirements": 3}, {"id": "export", "requirements": 2}])

    def test_empty(self):
        self.assertEqual(self.run_cli("list"), (0, "no open changes\n"))

    def test_bad_arguments(self):
        self.assertIsNone(pc.run(["list", "--yes"], cwd=str(self.root)))
        self.assertIsNone(pc.run(["archive"], cwd=str(self.root)))
        self.assertIsNone(pc.run(["new", "a", "b"], cwd=str(self.root)))


class ArchiveApplies(Base):
    def archive_ok(self, deltas, **over):
        self.change("demo", deltas, **over)
        code, out = self.run_cli("archive", "demo", "--yes")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.tree / "changes" / "demo").exists())
        self.assertTrue((self.tree / "changes" / "archive" / ("%s-demo" % TODAY) / "proposal.md").is_file())
        return out

    def test_added(self):
        self.archive_ok({"export": "## ADDED Requirements\n\n" + req("Csv", "write csv") + "\n"})
        self.assertEqual(self.spec(), HEAD + "\n\n".join([req("Export"), req("Format"), req("Csv", "write csv")]) + "\n")

    def test_modified(self):
        self.archive_ok({"export": "## MODIFIED Requirements\n\n" + req("Export", "export everything") + "\n"})
        self.assertEqual(self.spec(), HEAD + "\n\n".join([req("Export", "export everything"), req("Format")]) + "\n")

    def test_removed(self):
        self.archive_ok({"export": "## REMOVED Requirements\n\n### Requirement: Format\n"})
        self.assertEqual(self.spec(), main_spec("Export"))

    def test_renamed(self):
        self.archive_ok({"export": "## RENAMED Requirements\n\n- FROM: `### Requirement: Format`\n"
                                   "- TO: `### Requirement: Layout`\n"})
        self.assertEqual(self.spec(), main_spec("Export", "Layout"))

    def test_rename_then_modify_by_the_new_name(self):
        self.archive_ok({"export": "## RENAMED Requirements\n\n- FROM: `### Requirement: Format`\n- TO: `### Requirement: Layout`\n\n"
                                   "## MODIFIED Requirements\n\n" + req("Layout", "lay out") + "\n"})
        self.assertIn(req("Layout", "lay out"), self.spec())
        self.assertNotIn("Format", self.spec())

    def test_new_capability(self):
        purpose = "Imports files into the toy project from the formats it reads."
        out = self.archive_ok({"import": "## Purpose\n\n%s\n\n## ADDED Requirements\n\n%s\n" % (purpose, req("Csv"))})
        self.assertEqual(self.spec("import"),
                         "# import Specification\n\n## Purpose\n%s\n\n## Requirements\n\n%s\n" % (purpose, req("Csv")))
        self.assertIn("synced solo-sdd/specs/import/spec.md", out)

    def test_a_change_without_deltas(self):
        before = self.spec()
        self.archive_ok({}, **{"proposal.md": PROPOSAL.replace("- `export`", "Specs: none")})
        self.assertEqual(self.spec(), before)

    def test_the_delta_template_followed_as_written(self):
        template = (pc.TEMPLATES / "spec.md").read_text(encoding="utf-8")
        delta = template.replace("<name>", "Csv", 1).replace("<behaviour>", "write csv")
        delta = delta.replace("<name>", "S").replace("<condition>", "a").replace("<outcome>", "b")
        delta = delta[delta.index("## ADDED"):]
        self.archive_ok({"export": delta})
        self.assertEqual(self.spec(), HEAD + "\n\n".join([req("Export"), req("Format"), req("Csv", "write csv")]) + "\n")

    def test_new_capability_purpose_without_template_comment(self):
        purpose = "Imports files into the toy project from the formats it reads."
        self.archive_ok({"import": "## Purpose\n\n<!-- guidance -->\n%s\n\n## ADDED Requirements\n\n%s\n" % (purpose, req("Csv"))})
        self.assertNotIn("guidance", self.spec("import"))

    def test_rebuilt_format_one_blank_line_between_blocks(self):
        write(self.root, "solo-sdd/specs/export/spec.md", HEAD + req("Export").replace("\n\n", "\n\n\n\n") + "\n\n\n\n"
              + req("Format") + "\n\n\n")
        self.archive_ok({"export": "## ADDED Requirements\n\n\n" + req("Csv") + "\n\n\n"})
        self.assertEqual(self.spec(), HEAD + "\n\n".join([req("Export"), req("Format"), req("Csv")]) + "\n")

    def test_through_the_command(self):
        self.change("demo", {"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"})
        p = subprocess.run([sys.executable, "-m", "solo_sdd", "archive", "demo", "--yes"], cwd=self.root,
                           env=dict(os.environ, PYTHONPATH=str(REPO)), capture_output=True, text=True,
                           stdin=subprocess.DEVNULL)
        self.assertEqual(p.returncode, 0, p.stdout)
        self.assertRegex(p.stdout, r"archived solo-sdd/changes/archive/\d{4}-\d{2}-\d{2}-demo\n$")


class ArchiveAtomic(Base):
    def refused(self, deltas, *names, yes=True, **over):
        self.change("demo", deltas, **over)
        before = snapshot(self.root)
        code, out = self.run_cli("archive", "demo", *(["--yes"] if yes else []))
        self.assertEqual(code, 1, out)
        self.assertEqual(snapshot(self.root), before)
        for n in names:
            self.assertIn(n, out)
        return out

    def test_unknown_modified_name(self):
        self.refused({"export": "## MODIFIED Requirements\n\n" + req("Missing") + "\n"},
                     "solo-sdd/specs/export/spec.md", "Missing")

    def test_unknown_removed_and_renamed_names(self):
        self.refused({"export": "## REMOVED Requirements\n\n### Requirement: Gone\n"}, "Gone")
        self.refused({"export": "## RENAMED Requirements\n\n- FROM: `### Requirement: Gone`\n- TO: `### Requirement: New`\n"}, "Gone")

    def test_added_name_exists(self):
        self.refused({"export": "## ADDED Requirements\n\n" + req("Format") + "\n"}, "ADDED Format")

    def test_rename_onto_an_existing_name(self):
        self.refused({"export": "## RENAMED Requirements\n\n- FROM: `### Requirement: Format`\n- TO: `### Requirement: Export`\n"}, "Export")

    def test_one_bad_delta_blocks_the_good_one(self):
        purpose = "Imports files into the toy project from the formats it reads."
        self.refused({"export": "## MODIFIED Requirements\n\n" + req("Missing") + "\n",
                      "import": "## Purpose\n\n%s\n\n## ADDED Requirements\n\n%s\n" % (purpose, req("Csv"))}, "Missing")
        self.assertFalse((self.tree / "specs" / "import").exists())

    def test_fails_validate(self):
        self.refused({"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"}, "Source", "fails validate",
                     **{"proposal.md": PROPOSAL.split("## Source")[0]})

    def test_archive_folder_exists(self):
        (self.tree / "changes" / "archive" / ("%s-demo" % TODAY)).mkdir(parents=True)
        self.refused({"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"}, "archive folder exists")

    def test_no_terminal(self):
        with mock.patch.object(sys.stdin, "isatty", return_value=False):
            self.refused({"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"}, "--yes", yes=False)

    def test_closed_stdin(self):
        self.change("demo", {"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"})
        before = snapshot(self.root)
        p = subprocess.run(["sh", "-c", 'exec "$0" -m solo_sdd archive demo <&-', sys.executable], cwd=self.root,
                           env=dict(os.environ, PYTHONPATH=str(REPO)), capture_output=True, text=True)
        self.assertEqual(p.returncode, 1, p.stderr)
        self.assertIn("--yes", p.stdout)
        self.assertEqual(p.stderr, "")
        self.assertEqual(snapshot(self.root), before)

    def test_prompt_end_of_input(self):
        self.change("demo", {"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"})
        before = snapshot(self.root)
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", side_effect=EOFError):
            self.assertEqual(self.run_cli("archive", "demo"), (1, "update solo-sdd/specs/export/spec.md\nnot archived\n"))
        self.assertEqual(snapshot(self.root), before)

    def test_prose_to_line_in_renamed_is_not_an_entry(self):
        self.change("demo", {"export": "## RENAMED Requirements\n\nTo: keep the names short.\n\n"
                                       "- FROM: `### Requirement: Format`\n- TO: `### Requirement: Layout`\n"})
        self.assertEqual(self.run_cli("archive", "demo", "--yes")[0], 0)
        self.assertIn("Requirement: Layout", self.spec())

    def test_renamed_with_plain_bulleted_names(self):
        self.change("demo", {"export": "## RENAMED Requirements\n\n- FROM: Format\n- TO: Layout\n"})
        self.assertEqual(self.run_cli("archive", "demo", "--yes")[0], 0)
        self.assertEqual(self.spec(), main_spec("Export", "Layout"))

    def test_terminal_prompt(self):
        self.change("demo", {"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"})
        before = snapshot(self.root)
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="n"):
            code, out = self.run_cli("archive", "demo")
        self.assertEqual((code, snapshot(self.root)), (1, before))
        self.assertIn("update solo-sdd/specs/export/spec.md", out)
        with mock.patch.object(sys.stdin, "isatty", return_value=True), mock.patch("builtins.input", return_value="y"):
            self.assertEqual(self.run_cli("archive", "demo")[0], 0)
        self.assertIn("Requirement: Csv", self.spec())

    def test_a_failed_move_restores_the_specs(self):
        purpose = "Imports files into the toy project from the formats it reads."
        self.change("demo", {"export": "## ADDED Requirements\n\n" + req("Csv") + "\n",
                             "import": "## Purpose\n\n%s\n\n## ADDED Requirements\n\n%s\n" % (purpose, req("Csv"))})
        before = snapshot(self.root)
        with mock.patch.object(pc.os, "rename", side_effect=OSError("disk")):
            code, out = self.run_cli("archive", "demo", "--yes")
        self.assertEqual(code, 1)
        self.assertIn("every file restored", out)
        self.assertEqual(snapshot(self.root), before)
        self.assertFalse((self.tree / "specs" / "import").exists())
        self.assertFalse((self.tree / "changes" / "archive").exists())


class ArchiveRefusesUnfinishedWork(Base):
    DELTA = {"export": "## ADDED Requirements\n\n" + req("Csv") + "\n"}
    OPEN = TASKS.replace("- [x] 1.1 Code\n", "- [x] 1.1 Code\n- [ ] 1.2 Tests\n")
    EMPTY = VERIFICATION.replace("Ran it.", "<!-- Filled during apply: date, what was run, what was observed. -->")

    def refused(self, **over):
        self.change("demo", self.DELTA, **over)
        before = snapshot(self.root)
        code, out = self.run_cli("archive", "demo", "--yes")
        self.assertEqual((code, snapshot(self.root)), (1, before), out)
        return out

    def test_open_implementation_tasks(self):
        out = self.refused(**{"tasks.md": self.OPEN})
        self.assertIn("open task: 1.2", out)
        self.assertNotIn("2.2", out)

    def test_the_acceptance_group(self):
        self.change("demo", self.DELTA)
        code, out = self.run_cli("archive", "demo", "--yes")
        self.assertEqual(code, 0, out)
        self.assertNotIn("forced:", out)
        self.assertFalse((self.tree / "changes" / "demo").exists())
        self.assertIn("Requirement: Csv", self.spec())

    def test_a_task_above_the_first_group(self):
        self.assertIn("open task: 0.1", self.refused(**{"tasks.md": "- [ ] 0.1 Prepare\n\n" + TASKS}))

    def test_forced_keeps_the_other_refusals(self):
        for delta, over in (({"export": "## MODIFIED Requirements\n\n" + req("Missing") + "\n"}, {}),
                            (self.DELTA, {"proposal.md": PROPOSAL.split("## Source")[0]})):
            self.change("demo", delta, **dict({"tasks.md": self.OPEN}, **over))
            before = snapshot(self.root)
            code, out = self.run_cli("archive", "demo", "--yes", "--force")
            self.assertEqual((code, snapshot(self.root)), (1, before), out)
        self.change("demo", self.DELTA, **{"proposal.md": PROPOSAL, "tasks.md": self.OPEN})
        (self.tree / "changes" / "archive" / ("%s-demo" % TODAY)).mkdir(parents=True)
        code, out = self.run_cli("archive", "demo", "--yes", "--force")
        self.assertEqual(code, 1)
        self.assertIn("archive folder exists", out)

    def test_an_empty_result(self):
        self.assertIn("empty section: Result", self.refused(**{"verification.md": self.EMPTY}))
        self.assertIn("empty section: Result", self.refused(**{"verification.md": VERIFICATION.split("\n\n## Result")[0]}))

    def test_forced(self):
        self.change("demo", self.DELTA, **{"tasks.md": self.OPEN, "verification.md": self.EMPTY})
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pc.run(["archive", "demo", "--yes", "--force"], cwd=str(self.root))
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn("forced: 1.2, Result\n", out.getvalue())
        self.assertIn("Requirement: Csv", self.spec())


class ArchiveNamesSiblingDeltas(Base):
    def archive(self, delta, **siblings):
        self.change("demo", {"export": delta})
        for cid, text in siblings.items():
            self.change(cid, {"export": text})
        code, out = self.run_cli("archive", "demo", "--yes")
        self.assertEqual(code, 0, out)
        return [l for l in out.splitlines() if l.startswith("sibling:")]

    def test_two_changes_on_one_requirement(self):
        modify = "## MODIFIED Requirements\n\n" + req("Export", "export more") + "\n"
        rename = "## RENAMED Requirements\n\n- FROM: `### Requirement: Export`\n- TO: `### Requirement: Out`\n"
        self.assertEqual(self.archive(modify, **{"chars-empty": modify, "renamer": rename}),
                         ["sibling: chars-empty MODIFIED Export", "sibling: renamer RENAMED Export"])

    def test_a_removed_requirement(self):
        self.assertEqual(self.archive("## REMOVED Requirements\n\n### Requirement: Format\n",
                                      **{"bytes-fix": "## MODIFIED Requirements\n\n" + req("Format", "f") + "\n"}),
                         ["sibling: bytes-fix MODIFIED Format"])

    def test_a_renamed_requirement_and_a_broken_sibling(self):
        rename = "## RENAMED Requirements\n\n- FROM: `### Requirement: Format`\n- TO: `### Requirement: Layout`\n"
        broken = "## MODIFIED Requirements\n\n" + req("Format", "f") + "\n## RENAMED Requirements\n\n- FROM: Export\n"
        bullet = "## REMOVED Requirements\n\n- `### Requirement: Format`\n\n## RENAMED Requirements\n\n- TO: Export\n"
        self.assertEqual(self.archive(rename, broken=broken, bullet=bullet),
                         ["sibling: broken MODIFIED Format", "sibling: bullet REMOVED Format"])

    def test_no_sibling(self):
        self.assertEqual(self.archive("## MODIFIED Requirements\n\n" + req("Export", "e") + "\n",
                                      other="## MODIFIED Requirements\n\n" + req("Format", "f") + "\n"), [])


NAMES = st.lists(st.sampled_from(["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]),
                 min_size=0, max_size=8, unique=True)


class ArchiveAppliesDeltasProperty(unittest.TestCase):
    @settings(max_examples=300, deadline=None)
    @given(NAMES, st.data())
    def test_archive_applies_deltas_every_block_once_untouched_kept(self, names, data):
        """Requirement Archive applies deltas: every delta block appears once, untouched blocks keep text and order."""
        modified = data.draw(st.lists(st.sampled_from(names), unique=True) if names else st.just([]))
        added = data.draw(st.lists(st.sampled_from(["New1", "New2", "New3"]), unique=True))
        main = main_spec(*names) if names else "# export Specification\n\n## Purpose\nExports.\n\n## Requirements\n"
        delta = ""
        if modified:
            delta += "## MODIFIED Requirements\n\n" + "\n\n".join(req(n, "changed %s" % n) for n in modified) + "\n\n"
        if added:
            delta += "## ADDED Requirements\n\n" + "\n\n".join(req(n, "added %s" % n) for n in added) + "\n"
        out = pc.apply(main, delta, "export")
        for n in modified:
            self.assertEqual(out.count(req(n, "changed %s" % n)), 1)
            self.assertEqual(out.count("### Requirement: %s\n" % n), 1)
        for n in added:
            self.assertEqual(out.count(req(n, "added %s" % n)), 1)
        untouched = [n for n in names if n not in modified]
        for n in untouched:
            self.assertEqual(out.count(req(n)), 1)
        order = [out.index("### Requirement: %s\n" % n) for n in names]
        self.assertEqual(order, sorted(order))
        if names and added:
            self.assertGreater(out.index("### Requirement: %s\n" % added[0]), max(order))


if __name__ == "__main__":
    unittest.main()
