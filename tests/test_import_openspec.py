#!/usr/bin/env python3
"""solo-sdd import openspec on toy openspec/ trees in temporary folders."""
import contextlib, io, os, pathlib, subprocess, sys, tempfile, unittest
import marks
from unittest import mock

from hypothesis import given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from solo_sdd import import_openspec as io_  # noqa: E402

CONFIG = """schema: solo

context: |
  Language: en.
  Mode: prod
  Intent: a toy project
  for tests.

operations:
  apply:
    guidance:
      - one
"""
PROPOSAL = "# Proposal\n\n## Why\n\nA reason.\n\n## Capabilities\n\n### New Capabilities\n\n## Impact\n\n`x.py`.\n"


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(pathlib.Path(root).rglob("*")) if p.is_file()}


def toy(root, specs=3, open_=2, archived=5):
    """An openspec/ tree with the given counts; returns the root."""
    o = pathlib.Path(root) / "openspec"
    files = {"config.yaml": CONFIG}
    for i in range(specs):
        files["specs/cap%d/spec.md" % i] = "# cap%d Specification\n\nbody \xe9 %d\n" % (i, i)
    for i in range(open_):
        files["changes/c%d/proposal.md" % i] = PROPOSAL
        files["changes/c%d/tasks.md" % i] = "## 1. Acceptance\n\n- [ ] 1.1 x\n"
        files["changes/c%d/.openspec.yaml" % i] = "schema: solo\ncreated: 2026-11-09\n"
    for i in range(archived):
        files["changes/archive/2026-01-0%d-a%d/proposal.md" % (i % 9 + 1, i)] = PROPOSAL
        files["changes/archive/2026-01-0%d-a%d/.openspec.yaml" % (i % 9 + 1, i)] = "schema: solo\n"
    for rel, text in files.items():
        (o / rel).parent.mkdir(parents=True, exist_ok=True)
        (o / rel).write_text(text, encoding="utf-8")
    return pathlib.Path(root)


def run(root, *args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = io_.main(["openspec", str(root), *args])
    return code, out.getvalue()


class Tmp(unittest.TestCase):
    def setUp(self):
        self.umask = os.umask(0)
        os.umask(self.umask)
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()


class ImportPlanAndWrite(Tmp):
    def test_plan_only(self):
        toy(self.root)
        before = snapshot(self.root)
        code, out = run(self.root)
        self.assertEqual(code, 0)
        self.assertIn("3 specs, 2 open changes, 5 archived changes", out)
        self.assertIn("create solo-sdd/specs/cap0/spec.md", out)
        self.assertEqual(snapshot(self.root), before)

    def test_write(self):
        toy(self.root)
        before = snapshot(self.root / "openspec")
        code, out = run(self.root, "--write")
        self.assertEqual(code, 0, out)
        self.assertEqual(snapshot(self.root / "openspec"), before)
        got = snapshot(self.root / "solo-sdd")
        for rel, data in before.items():
            if rel.startswith(("specs/", "changes/")) and not rel.endswith(".openspec.yaml"):
                self.assertEqual(got[rel], data, rel)
        self.assertFalse([r for r in got if r.endswith(".openspec.yaml")])
        self.assertEqual(len([r for r in got if r.startswith("specs/")]), 3)
        self.assertEqual(len({r.split("/")[2] for r in got if r.startswith("changes/archive/")}), 5)
        self.assertIn("created solo-sdd/changes/c1/tasks.md", out)
        self.assertIn("delete openspec/", out.strip().splitlines()[-1])
        self.assertFalse([p for p in self.root.iterdir() if p.name.startswith(".solo-sdd.import")])
        self.assertEqual((self.root / "solo-sdd").stat().st_mode & 0o777, 0o777 & ~self.umask)

    def test_unrelated_hidden_folder_kept(self):
        toy(self.root)
        (self.root / ".solo-sdd.import").mkdir()
        (self.root / ".solo-sdd.import/keep.txt").write_text("mine\n")
        self.assertEqual(run(self.root, "--write")[0], 0)
        self.assertEqual((self.root / ".solo-sdd.import/keep.txt").read_text(), "mine\n")

    def test_linked_folder_refused(self):
        toy(self.root)
        (self.root / "elsewhere").mkdir()
        (self.root / "elsewhere/spec.md").write_text("x\n")
        (self.root / "openspec/specs/linked").symlink_to(self.root / "elsewhere")
        for args in ((), ("--write",)):
            code, out = run(self.root, *args)
            self.assertEqual(code, 1)
            self.assertIn("linked folder not supported", out)
            self.assertIn("openspec/specs/linked", out)
            self.assertFalse((self.root / "solo-sdd").exists())

    @unittest.skipIf(os.geteuid() == 0, "root reads any folder")
    def test_unreadable_folder_refused(self):
        toy(self.root)
        locked = self.root / "openspec/changes/c1"
        locked.chmod(0)
        try:
            code, out = run(self.root, "--write")
        finally:
            locked.chmod(0o755)
        self.assertEqual(code, 1)
        self.assertIn("cannot read", out)
        self.assertFalse((self.root / "solo-sdd").exists())

    def test_interrupt_leaves_no_temporary_folder(self):
        toy(self.root)
        with mock.patch.object(io_.os, "rename", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                run(self.root, "--write")
        self.assertEqual([p.name for p in self.root.iterdir()], ["openspec"])

    def test_not_utf8_config(self):
        toy(self.root)
        (self.root / "openspec/config.yaml").write_bytes(b"context: \xff\n")
        code, out = run(self.root, "--write")
        self.assertEqual(code, 1)
        self.assertIn("cannot read", out)
        self.assertFalse((self.root / "solo-sdd").exists())

    def test_empty_solo_sdd_folder_is_absent(self):
        toy(self.root)
        (self.root / "solo-sdd").mkdir()
        self.assertEqual(run(self.root, "--write")[0], 0)
        self.assertTrue((self.root / "solo-sdd/project.md").is_file())

    def test_cli(self):
        toy(self.root)
        r = subprocess.run([sys.executable, "-m", "solo_sdd", "import", "openspec", str(self.root)], cwd=REPO,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("plan only", r.stdout)
        help_ = subprocess.run([sys.executable, "-m", "solo_sdd"], cwd=REPO, capture_output=True, text=True,
                               stdin=subprocess.DEVNULL, timeout=60).stdout
        self.assertIn("import openspec [folder] [--write]", help_)
        self.assertEqual(io_.main(["spec-kit"]), None)
        self.assertEqual(io_.main(["openspec", "--force"]), None)


class ImportProjectFiles(Tmp):
    def test_context_and_language(self):
        toy(self.root)
        run(self.root, "--write")
        text = (self.root / "solo-sdd/project.md").read_text()
        self.assertEqual(text, "# Project\n\nLanguage: en\nMode: prod\n\nIntent: a toy project\nfor tests.\n")

    def test_no_config(self):
        toy(self.root)
        (self.root / "openspec/config.yaml").unlink()
        run(self.root, "--write")
        self.assertEqual((self.root / "solo-sdd/project.md").read_text(), "# Project\n\n")

    def test_one_line_context(self):
        self.assertEqual(io_.project_text('context: "Mode: demo"\n'), "# Project\n\nMode: demo\n")

    def test_analyze(self):
        toy(self.root)
        (self.root / "openspec/analyze.md").write_bytes(b"# checks\r\n- one\n")
        run(self.root, "--write")
        self.assertEqual((self.root / "solo-sdd/analyze.md").read_bytes(), b"# checks\r\n- one\n")

    def test_change_without_specs(self):
        toy(self.root)
        (self.root / "openspec/changes/c0/.openspec.yaml").write_text("schema: solo\nskip_specs: true\n")
        code, out = run(self.root, "--write")
        text = (self.root / "solo-sdd/changes/c0/proposal.md").read_text()
        self.assertIn("## Capabilities\n\nSpecs: none\n\n### New Capabilities", text)
        self.assertEqual((self.root / "solo-sdd/changes/c1/proposal.md").read_text(), PROPOSAL)
        self.assertIn("Specs: none added to solo-sdd/changes/c0/proposal.md", out)

    def test_specs_none_section_added_or_kept(self):
        self.assertEqual(io_.mark_specs_none("# P\n\n## Why\n\nx\n"), "# P\n\n## Why\n\nx\n\n## Capabilities\n\nSpecs: none\n")
        done = "## Capabilities\n\nSpecs: none\n"
        self.assertEqual(io_.mark_specs_none(done), done)
        self.assertEqual(io_.mark_specs_none("## Capabilities\r\n\r\n## Impact\r\n"),
                         "## Capabilities\r\n\r\nSpecs: none\r\n\r\n## Impact\r\n")
        self.assertEqual(io_.mark_specs_none("## Why\r\nx\n## Capabilities\n\n## Impact\r\n"),
                         "## Why\r\nx\n## Capabilities\n\nSpecs: none\n\n## Impact\r\n")

    def test_skip_specs_forms(self):
        for text in ("skip_specs: true\n", "skip_specs: 'true'  # no deltas\n", "meta:\n  skip_specs: True\n"):
            self.assertTrue(io_.SKIP_SPECS.search(text), text)
        for text in ("skip_specs: false\n", "skip_specs: trueish\n"):
            self.assertFalse(io_.SKIP_SPECS.search(text), text)

    def test_claim_and_waiting_kept(self):
        toy(self.root)
        (self.root / "openspec/changes/c0/CLAIM").write_text("claude 2026-11-09 session=x\n")
        (self.root / "openspec/changes/c1/WAITING").write_text("keys\n")
        run(self.root, "--write")
        self.assertEqual((self.root / "solo-sdd/changes/c0/CLAIM").read_text(), "claude 2026-11-09 session=x\n")
        self.assertEqual((self.root / "solo-sdd/changes/c1/WAITING").read_text(), "keys\n")


class ImportIsIdempotentAndSafe(Tmp):
    def test_repeat(self):
        toy(self.root)
        run(self.root, "--write")
        before = snapshot(self.root)
        code, out = run(self.root, "--write")
        self.assertEqual((code, snapshot(self.root)), (0, before))
        self.assertIn("nothing to import", out)

    def test_foreign_content(self):
        toy(self.root)
        p = self.root / "solo-sdd/specs/cap0/spec.md"
        p.parent.mkdir(parents=True)
        p.write_text("mine\n")
        before = snapshot(self.root)
        for args in ((), ("--write",)):
            code, out = run(self.root, *args)
            self.assertEqual(code, 1)
            self.assertIn("at solo-sdd/specs/cap0/spec.md;", out)
            self.assertEqual(snapshot(self.root), before)

    def test_changed_file_named(self):
        toy(self.root)
        run(self.root, "--write")
        (self.root / "solo-sdd/specs/cap0/spec.md").write_text("mine\n")
        before = snapshot(self.root)
        code, out = run(self.root, "--write")
        self.assertEqual(code, 1)
        self.assertIn("solo-sdd/specs/cap0/spec.md", out)
        self.assertEqual(snapshot(self.root), before)

    def test_extra_file_refused(self):
        toy(self.root)
        run(self.root, "--write")
        (self.root / "solo-sdd/changes/new/proposal.md").parent.mkdir()
        (self.root / "solo-sdd/changes/new/proposal.md").write_text("x\n")
        before = snapshot(self.root)
        code, out = run(self.root, "--write")
        self.assertEqual(code, 1)
        self.assertIn("solo-sdd/changes/new/proposal.md", out)
        self.assertEqual(snapshot(self.root), before)

    def test_no_tree(self):
        before = snapshot(self.root)
        code, out = run(self.root, "--write")
        self.assertEqual((code, out.strip()), (1, "no openspec/ tree"))
        self.assertEqual(snapshot(self.root), before)


def idempotent(root):
    """The property: after one --write, a second --write exits 0, says so and changes no byte."""
    first = run(root, "--write")[0]
    assert first == 0
    before = snapshot(root)
    code, out = run(root, "--write")
    assert code == 0 and "nothing to import" in out, out
    assert snapshot(root) == before


TREES = st.fixed_dictionaries({
    "specs": st.integers(0, 3), "open": st.integers(0, 3), "archived": st.integers(0, 3),
    "skip": st.booleans(), "claim": st.booleans(), "analyze": st.booleans(), "config": st.booleans(),
    "empty_dest": st.booleans()})


def build(root, t):
    toy(root, t["specs"], t["open"], t["archived"])
    o = pathlib.Path(root) / "openspec"
    if t["open"] and t["skip"]:
        (o / "changes/c0/.openspec.yaml").write_text("skip_specs: true\n")
    if t["open"] and t["claim"]:
        (o / "changes/c0/CLAIM").write_text("claude\n")
    if t["analyze"]:
        (o / "analyze.md").write_text("# a\n")
    if not t["config"]:
        (o / "config.yaml").unlink()
    if t["empty_dest"]:
        (pathlib.Path(root) / "solo-sdd").mkdir()


class ImportIsIdempotentAndSafeProperty(unittest.TestCase):
    @marks.slow
    @settings(max_examples=60, deadline=None)
    @given(TREES)
    def test_import_is_idempotent_and_safe(self, t):
        with tempfile.TemporaryDirectory() as d:
            build(d, t)
            idempotent(pathlib.Path(d))

    def test_mutation_rewriting_project_md_fails(self):
        calls = iter(range(1000))
        real = io_.project_text
        with mock.patch.object(io_, "project_text", lambda c: real(c) + "run %d\n" % next(calls)):
            with tempfile.TemporaryDirectory() as d:
                toy(d)
                with self.assertRaises(AssertionError):
                    idempotent(pathlib.Path(d))


if __name__ == "__main__":
    unittest.main()
