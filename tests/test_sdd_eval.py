"""Checks sdd_eval.py setup: set, copies on the change base, spec delta, determinism."""
import importlib.util
import json
import os
import pathlib
import shutil
import stat
import subprocess
import tempfile
import unittest
import marks
import shared_repo

from hypothesis import given, settings, strategies as st

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "global/sdd_eval.py"
PLAN = ROOT / "global/sdd_dispatch_plan.py"
FIX = ROOT / "tests/eval/fixtures"

_spec = importlib.util.spec_from_file_location("sdd_eval", SCRIPT)
ev = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ev)

IDS = ["20%d-feat%d" % (i, i) for i in range(8)]
SPEC_CAP = ("# cap\n\n## Requirements\n\n### Requirement: A\na\n\n### Requirement: B\nb\n\n"
            "### Requirement: C\nc\n")
AGENTS = ("# P\n\n## Commands\n\nTests: `true`\n\n## Working copy\n\n- Orchestrators: 3\n- Old: yes\n\n"
          "## Delivery\n\n- Mode: remote\n- Deploy: no\n\n## Misc\n\ntext\n")
TASKS = "- [x] a\n- [X] b\n- [ ] c\n"
VERIF = "# v\n\n## Result\n\nOK\n\n## Not Verified\n\nnothing\n\n## Notes\n\nkeep\n\n## Decisions Without Owner\n\nd\n"


def git(repo, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(repo)] + list(args),
                          capture_output=True, text=True, check=True, stdin=subprocess.DEVNULL).stdout.strip()


def put(base, rel, text):
    p = pathlib.Path(base, rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def run_setup(setfile, cfg, out):
    return subprocess.run(["/usr/bin/python3", str(SCRIPT), "setup", str(setfile), "--config", str(cfg),
                           "--out", str(out)], capture_output=True, text=True, timeout=180,
                          stdin=subprocess.DEVNULL)


def build_env(root, tree):
    """The project of Env in root/proj; returns its oracles."""
    proj = root / "proj"
    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")
    put(proj, ".gitignore", tree + "/\nAGENTS.md\nCLAUDE.md\ndocs/note.md\n")
    put(proj, "README.md", "r\n")
    put(proj, "docs/tracked.md", "t\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "init")
    oracles = {}
    for i, cid in enumerate(IDS):
        put(proj, "src%d.js" % i, "code\n")
        put(proj, "x%d.test.js" % i, "test\n")
        git(proj, "add", "-A")
        git(proj, "commit", "-qm", "c" + cid)
        oracles[cid] = git(proj, "rev-parse", "HEAD")
    git(proj, "tag", "future")
    put(proj, "AGENTS.md", AGENTS)
    put(proj, "CLAUDE.md", "claude\n")
    put(proj, "docs/note.md", "note\n")
    put(proj, tree + "/config.yaml", "schema: solo\n")
    put(proj, tree + "/specs/cap/spec.md", SPEC_CAP)
    put(proj, tree + "/specs/cap2/spec.md", "# cap2\n\n## Requirements\n\n### Requirement: X\nx\n")
    put(proj, tree + "/changes/archive/2025-12-31-100-dep/proposal.md", "## Why\nd\n")
    put(proj, tree + "/changes/archive/2025-12-30-other/proposal.md", "## Why\no\n")
    for i, cid in enumerate(IDS):
        d = tree + "/changes/archive/2026-01-01-" + cid
        deps = {0: "- `100-dep`\n", 1: "- `999-ghost`\n"}.get(i, "- none\n")
        put(proj, d + "/proposal.md", "## Why\nw\n\n## Depends On\n\n" + deps)
        put(proj, d + "/tasks.md", TASKS)
        put(proj, d + "/verification.md", VERIF)
        put(proj, d + "/design.md", "dz\n")
        put(proj, d + "/.openspec.yaml", "schema: solo\n")
        put(proj, d + "/CLAIM", "c\n")
        put(proj, d + "/WAITING", "w\n")
    return oracles


class Env:
    """A toy project with 8 oracles, a set and a configuration, a copy of one built once per tree (tests/shared_repo.py);
    cleans up after itself."""

    def __init__(self, prepare="true", tree="openspec"):
        folder, oracles = shared_repo.template(("Env", tree), lambda root: build_env(root, tree))
        self.root = shared_repo.copy(folder)
        self.proj = self.root / "proj"
        self.oracles = dict(oracles)
        self.arch = lambda cid: self.proj / (tree + "/changes/archive/2026-01-01-" + cid)
        self.write_set(prepare=prepare)
        self.cfg = self.root / "cfg.json"
        self.cfg.write_text(json.dumps({"name": "base1", "working_copy": ["Orchestrators: 5", "New: yes"]}))

    def write_set(self, changes=None, prepare="true", **extra):
        ch = changes if changes is not None else [{"id": c, "oracle": o} for c, o in self.oracles.items()]
        self.set = self.root / "set.json"
        self.set.write_text(json.dumps(dict({"project": str(self.proj), "prepare": prepare, "changes": ch}, **extra)))

    def delta(self, cid, text):
        put(self.arch(cid), "specs/cap/spec.md", text)

    def setup(self, out="out"):
        return run_setup(self.set, self.cfg, self.root / out)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def make_env(t, **kw):
    e = Env(**kw)
    t.addCleanup(e.close)
    return e


@marks.release
class RejectTests(unittest.TestCase):
    def test_seven_changes(self):
        e = make_env(self)
        e.write_set(changes=[{"id": c, "oracle": o} for c, o in list(e.oracles.items())[:7]])
        r = e.setup()
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("changes: 7", r.stderr)
        self.assertIn("changes", r.stderr)
        self.assertFalse((e.root / "out").exists())

    def test_missing_oracle(self):
        e = make_env(self)
        ch = [{"id": c, "oracle": o} for c, o in e.oracles.items()]
        del ch[3]["oracle"]
        e.write_set(changes=ch)
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn(IDS[3], r.stderr)
        self.assertIn("oracle", r.stderr)
        self.assertFalse((e.root / "out").exists())

    def test_oracle_only_deletes_test(self):
        e = make_env(self)
        git(e.proj, "rm", "-q", "x0.test.js")
        git(e.proj, "commit", "-qm", "delete")
        e.write_set(changes=[{"id": c, "oracle": git(e.proj, "rev-parse", "HEAD") if c == IDS[0] else o}
                             for c, o in e.oracles.items()])
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn("oracle without tests: " + IDS[0], r.stderr)
        self.assertFalse((e.root / "out").exists())

    def test_duplicate_id(self):
        e = make_env(self)
        e.write_set(changes=[{"id": c, "oracle": o} for c, o in e.oracles.items()] +
                            [{"id": IDS[0], "oracle": e.oracles[IDS[1]]}])
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn("%s: repeated in the set" % IDS[0], r.stderr.splitlines())
        self.assertFalse((e.root / "out").exists())

    def test_bad_change_types(self):
        for bad in ("string", {"id": 5, "oracle": "x"}):
            e = make_env(self)
            e.write_set(changes=[bad] + [{"id": c, "oracle": o} for c, o in list(e.oracles.items())[:7]])
            r = e.setup()
            self.assertEqual(r.returncode, 2, r.stderr)
            self.assertIn("changes[0]: an object needed", r.stderr)
            self.assertFalse((e.root / "out").exists())

    def test_not_in_archive(self):
        e = make_env(self)
        shutil.rmtree(e.arch(IDS[2]))
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn(IDS[2], r.stderr)
        self.assertFalse((e.root / "out").exists())

    def test_oracle_without_tests(self):
        e = make_env(self)
        put(e.proj, "only.js", "code\n")
        git(e.proj, "add", "-A")
        git(e.proj, "commit", "-qm", "code only")
        e.oracles[IDS[1]] = git(e.proj, "rev-parse", "HEAD")
        e.write_set()
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn("oracle without tests: " + IDS[1], r.stderr)
        self.assertFalse((e.root / "out").exists())

    def test_oracle_not_on_main(self):
        e = make_env(self)
        git(e.proj, "checkout", "-q", "-b", "side")
        put(e.proj, "s.test.js", "t\n")
        git(e.proj, "add", "-A")
        git(e.proj, "commit", "-qm", "side")
        e.oracles[IDS[4]] = git(e.proj, "rev-parse", "HEAD")
        git(e.proj, "checkout", "-q", "main")
        e.write_set()
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn(IDS[4], r.stderr)
        self.assertFalse((e.root / "out").exists())

    def test_existing_copy_folder(self):
        e = make_env(self)
        (e.root / "out" / IDS[5]).mkdir(parents=True)
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn(IDS[5], r.stderr)
        self.assertEqual(sorted(p.name for p in (e.root / "out").iterdir()), [IDS[5]])


@marks.release
class CopyTests(unittest.TestCase):
    def test_setup_copy(self):
        e = make_env(self)
        git(e.proj, "remote", "add", "origin", str(e.proj))
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        for cid in IDS:
            c = e.root / "out" / cid
            self.assertEqual(git(c, "rev-parse", "HEAD"), git(e.proj, "rev-parse", e.oracles[cid] + "^1"))
            self.assertEqual(git(c, "remote"), "")
            self.assertEqual(git(c, "tag", "-l"), "")
            self.assertNotIn(e.oracles[cid], git(c, "log", "--all", "--format=%H"))
            ag = (c / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("- Mode: local\n", ag)
            self.assertIn("- Orchestrators: 1\n", ag)
            self.assertIn("- New: yes\n", ag)
            for old in ("remote", "Deploy", "Orchestrators: 3", "Orchestrators: 5", "Old"):
                self.assertNotIn(old, ag)
            self.assertIn("## Misc\n\ntext\n", ag)
            self.assertEqual((c / "CLAUDE.md").read_text(), "claude\n")
            self.assertEqual((c / "docs/note.md").read_text(), "note\n")
            self.assertEqual((c / "openspec/config.yaml").read_text(), "schema: solo\n")
            ch = c / "openspec/changes" / cid
            self.assertEqual((ch / "tasks.md").read_text(), "- [ ] a\n- [ ] b\n- [ ] c\n")
            v = (ch / "verification.md").read_text()
            self.assertEqual(v, "# v\n\n## Result\n\n## Not Verified\n\n## Notes\n\nkeep\n\n"
                                "## Decisions Without Owner\n\n")
            self.assertTrue((ch / "design.md").exists() and (ch / ".openspec.yaml").exists())
            self.assertFalse((ch / "CLAIM").exists() or (ch / "WAITING").exists())
            meta = json.loads((c / ".sdd-eval").read_text(encoding="utf-8"))
            self.assertEqual(meta["config"], "base1")
            self.assertEqual(meta["id"], cid)
            self.assertEqual(meta["oracle"], e.oracles[cid])
            self.assertEqual(meta["base"], git(c, "rev-parse", "HEAD"))
            self.assertEqual(meta["main"], "main")
            self.assertEqual(meta["tests"], ["*.test.*", "tests/"])
            self.assertIn(".sdd-eval", (c / ".git/info/exclude").read_text())
            self.assertEqual(git(c, "status", "--porcelain"), "")
        self.assertEqual([pathlib.Path(p).name for p in ev.copies(e.root / "out")], sorted(IDS))

    def test_added_requirement_stripped(self):
        e = make_env(self)
        e.delta(IDS[0], "## ADDED Requirements\n\n### Requirement: B\nx\n")
        e.delta(IDS[1], "## ADDED Requirements\n\n### Requirement: X\nx\n")
        put(e.arch(IDS[1]), "specs/cap2/spec.md", "## ADDED Requirements\n\n### Requirement: X\nx\n")
        (e.arch(IDS[1]) / "specs/cap/spec.md").unlink()
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        spec = (e.root / "out" / IDS[0] / "openspec/specs/cap/spec.md").read_text(encoding="utf-8")
        self.assertEqual(spec, SPEC_CAP.replace("### Requirement: B\nb\n\n", ""))
        self.assertFalse((e.root / "out" / IDS[1] / "openspec/specs/cap2").exists())
        self.assertTrue((e.root / "out" / IDS[1] / "openspec/specs/cap/spec.md").exists())

    def test_modified_requirement_noted(self):
        e = make_env(self)
        e.delta(IDS[0], "## MODIFIED Requirements\n\n### Requirement: B\nx\n")
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        line = "spec after the change: %s B" % IDS[0]
        self.assertIn(line, r.stdout.splitlines())
        c = e.root / "out" / IDS[0]
        self.assertEqual((c / "openspec/specs/cap/spec.md").read_text(encoding="utf-8"), SPEC_CAP)
        self.assertEqual(json.loads((c / ".sdd-eval").read_text(encoding="utf-8"))["spec_notes"], [line])

    def test_removed_renamed_noted(self):
        e = make_env(self)
        e.delta(IDS[0], "## REMOVED Requirements\n\n### Requirement: B\n\n## RENAMED Requirements\n\n"
                        "- FROM: `### Requirement: C`\n- TO: `### Requirement: C2`\n")
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = ["spec after the change: %s %s" % (IDS[0], n) for n in ("B", "C", "C2")]
        c = e.root / "out" / IDS[0]
        for ln in lines:
            self.assertIn(ln, r.stdout.splitlines())
        self.assertEqual(json.loads((c / ".sdd-eval").read_text(encoding="utf-8"))["spec_notes"], lines)
        self.assertEqual((c / "openspec/specs/cap/spec.md").read_text(encoding="utf-8"), SPEC_CAP)

    def test_dependencies(self):
        e = make_env(self)
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        c = e.root / "out" / IDS[0]
        self.assertEqual(sorted(p.name for p in (c / "openspec/changes/archive").iterdir()), ["2025-12-31-100-dep"])
        self.assertIn("dependency not archived: %s 999-ghost" % IDS[1], r.stdout.splitlines())
        plan = subprocess.run(["/usr/bin/python3", str(PLAN), str(c)], capture_output=True, text=True,
                              stdin=subprocess.DEVNULL)
        self.assertIn("launch: " + IDS[0], plan.stdout.splitlines())

    def test_depends_none_variants(self):
        e = make_env(self)
        for cid, dep in zip(IDS[2:7], ["none.", "None", "—", "none (explanation)", "none, `999-ghost`"]):
            put(e.arch(cid), "proposal.md", "## Why\nw\n\n## Depends On\n\n- %s\n" % dep)
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual([ln for ln in r.stdout.splitlines() if "not archived" in ln],
                         ["dependency not archived: %s 999-ghost" % IDS[1]])
        for cid in IDS[2:7]:
            arch = e.root / "out" / cid / "openspec/changes/archive"
            self.assertEqual(list(arch.iterdir()) if arch.exists() else [], [])

    def test_answers_validated(self):
        e = make_env(self)
        for bad in (["x"], {"q": 1}, "string", {"q": None}):
            e.write_set(answers=bad)
            r = e.setup()
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("answers:", r.stderr)
            self.assertFalse((e.root / "out").exists())

    def test_answers_in_meta(self):
        e = make_env(self)
        r = e.setup("o0")
        self.assertEqual(json.loads((e.root / "o0" / IDS[0] / ".sdd-eval").read_text())["answers"], {})
        e.write_set(answers={"Mode?": "local"})
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((e.root / "out" / IDS[0] / ".sdd-eval").read_text())["answers"],
                         {"Mode?": "local"})

    def test_oracle_prepare_validated_and_in_meta(self):
        e = make_env(self)
        for bad in (["x"], 5, {"a": "b"}):
            e.write_set(oracle_prepare=bad)
            r = e.setup()
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("oracle_prepare:", r.stderr)
            self.assertFalse((e.root / "out").exists())
        e.write_set()
        self.assertEqual(e.setup("o0").returncode, 0)
        self.assertIsNone(json.loads((e.root / "o0" / IDS[0] / ".sdd-eval").read_text())["oracle_prepare"])
        e.write_set(oracle_prepare="npm run build")
        self.assertEqual(e.setup().returncode, 0)
        self.assertEqual(json.loads((e.root / "out" / IDS[0] / ".sdd-eval").read_text())["oracle_prepare"],
                         "npm run build")

    def test_repeat_is_identical(self):
        e = make_env(self)
        a, b = e.setup("o1"), e.setup("o2")
        self.assertEqual((a.returncode, b.returncode), (0, 0), a.stderr + b.stderr)
        self.assertEqual(a.stdout, b.stdout)
        for cid in IDS:
            x, y = e.root / "o1" / cid, e.root / "o2" / cid
            self.assertEqual(git(x, "rev-parse", "HEAD"), git(y, "rev-parse", "HEAD"))
            self.assertEqual(ev.tree_hash(x / "openspec"), ev.tree_hash(y / "openspec"))
            self.assertIn("%s %s %s" % (cid, git(x, "rev-parse", "HEAD"), ev.tree_hash(x / "openspec")),
                          a.stdout.splitlines())

    def test_prepare_failure_one_copy(self):
        e = make_env(self, prepare="if [ -d openspec/changes/%s ]; then echo boom-line; exit 7; fi" % IDS[6])
        r = e.setup()
        self.assertEqual(r.returncode, 3)
        self.assertIn(IDS[6], r.stderr)
        self.assertIn("boom-line", r.stderr)
        self.assertIn("7", r.stderr)
        self.assertEqual(len(ev.copies(e.root / "out")), 8)
        ok = [ln for ln in r.stdout.splitlines() if ln.split()[0] in IDS]
        self.assertEqual(len(ok), 7)
        self.assertNotIn(IDS[6], [ln.split()[0] for ln in ok])


names = st.text(alphabet="abcdefg ", min_size=1, max_size=5).map(str.strip).filter(bool)
bodies = st.text(alphabet="xyz \n", max_size=10)
lined = bodies.map(lambda x: x + "\n" if x and not x.endswith("\n") else x)
sect_titles = st.sampled_from(["Result", "Not Verified", "Decisions Without Owner", "Notes", "Other"])
EMPTIED = {"Result", "Not Verified", "Decisions Without Owner"}


@marks.release
class OwnTreeCopy(unittest.TestCase):
    """Requirement: Process root. setup reads the archive and specs from solo-sdd/ and carries them into the copy."""

    def test_setup_own_tree(self):
        e = make_env(self, tree="solo-sdd")
        put(e.proj, "solo-sdd/project.md", "intent\n")
        put(e.arch(IDS[2]), "specs/cap2/spec.md", "## ADDED Requirements\n\n### Requirement: X\nx\n")
        r = e.setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("openspec", r.stderr + r.stdout)
        c0 = e.root / "out" / IDS[0]
        self.assertEqual((c0 / "solo-sdd/project.md").read_text(), "intent\n")
        self.assertEqual((c0 / "solo-sdd/changes" / IDS[0] / "tasks.md").read_text(), "- [ ] a\n- [ ] b\n- [ ] c\n")
        self.assertEqual(sorted(p.name for p in (c0 / "solo-sdd/changes/archive").iterdir()), ["2025-12-31-100-dep"])
        self.assertFalse((c0 / "openspec").exists())
        self.assertFalse((e.root / "out" / IDS[2] / "solo-sdd/specs/cap2").exists())
        self.assertIn("%s %s %s" % (IDS[0], git(c0, "rev-parse", "HEAD"), ev.tree_hash(c0 / "solo-sdd")), r.stdout)
        put(c0, "solo-sdd/changes/archive/2026-01-01-%s/f" % IDS[0], "a\n")
        self.assertTrue(ev.archived(str(c0), IDS[0]))

    def test_missing_archive_names_tree(self):
        e = make_env(self, tree="solo-sdd")
        shutil.rmtree(e.arch(IDS[3]))
        r = e.setup()
        self.assertEqual(r.returncode, 2)
        self.assertIn("%s: no folder in solo-sdd/changes/archive" % IDS[3], r.stderr)

    def test_legacy_hint(self):
        r = make_env(self).setup()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("process in openspec/: run solo-sdd import openspec", r.stderr)


@marks.release
class ReplayCopyProperties(unittest.TestCase):
    @settings(max_examples=50, deadline=None)
    @given(st.lists(st.tuples(sect_titles, lined), max_size=6), lined)
    def test_replay_copy_verification_reset(self, secs, pre):
        text = pre + "".join("## %s\n%s" % (t, b) for t, b in secs)
        once = ev.reset_verification(text)
        self.assertEqual(ev.reset_verification(once), once)
        exp = pre + "".join("## %s\n\n" % t if t in EMPTIED else "## %s\n%s" % (t, b) for t, b in secs)
        self.assertEqual(once, exp)

    @settings(max_examples=50, deadline=None)
    @given(st.lists(st.sampled_from(["- [x] a", "- [X] b", "- [ ] c", "  - [x] d", "text [x]", ""]), max_size=8))
    def test_replay_copy_tasks_reset(self, lines):
        text = "\n".join(lines) + "\n"
        once = ev.reset_tasks(text)
        self.assertEqual(ev.reset_tasks(once), once)
        for a, b in zip(text.splitlines(), once.splitlines()):
            if "- [" in a:
                self.assertEqual(b, a.replace("[x]", "[ ]").replace("[X]", "[ ]"))
            else:
                self.assertEqual(a, b)
        self.assertNotRegex(once, r"- \[[xX]\]")

    @settings(max_examples=50, deadline=None)
    @given(st.lists(st.tuples(names, bodies), min_size=1, max_size=6, unique_by=lambda t: t[0]),
           st.data())
    def test_replay_copy_strip_added(self, reqs, data):
        head = "# cap\n\n## Requirements\n\n"
        block = lambda n, b: "### Requirement: %s\n%s\n\n" % (n, b)
        gone = data.draw(st.sets(st.sampled_from([n for n, _ in reqs])))
        if data.draw(st.booleans()):
            gone = {reqs[0][0]} if data.draw(st.booleans()) else {reqs[-1][0]}
        spec = head + "".join(block(n, b) for n, b in reqs) + "## Tail\n\nend\n"
        exp = head + "".join(block(n, b) for n, b in reqs if n not in gone) + "## Tail\n\nend\n"
        self.assertEqual(ev.strip_added(spec, gone), exp)

    def test_replay_copy_delta_parse(self):
        t = ("## ADDED Requirements\n\n### Requirement: A\nx\n\n### Requirement: B\n\n"
             "## MODIFIED Requirements\n\n### Requirement: C\n\n## REMOVED Requirements\n\n### Requirement: D\n\n"
             "## RENAMED Requirements\n\n- FROM: `### Requirement: E`\n- TO: `### Requirement: F`\n")
        self.assertEqual(ev.delta_requirements(t), {"ADDED": ["A", "B"], "MODIFIED": ["C"], "REMOVED": ["D"],
                                                    "RENAMED": ["E", "F"]})

    def test_replay_copy_is_test_file(self):
        p = ["*.test.*", "tests/"]
        self.assertTrue(ev.is_test_file("a/b/x.test.js", p))
        self.assertTrue(ev.is_test_file("tests/a.js", p))
        self.assertTrue(ev.is_test_file("apps/tests/a.js", p))
        self.assertFalse(ev.is_test_file("mytests/a.js", p))
        self.assertFalse(ev.is_test_file("src/a.js", p))


# ---- run ----

FAKE_CLAUDE = """#!/bin/sh
echo "$1 $2 $3 $4 $5 $6" >> "$FAKE_COUNT"
printf '%s\\0' "$@" > "$FAKE_COUNT.argv"
if [ -n "$FAKE_LOG" ]; then
  mkdir -p "$HOME/.claude/projects/x"
  cp "$FAKE_LOG" "$HOME/.claude/projects/x/$6.jsonl"
fi
if [ -n "$FAKE_PAR" ]; then
  mkdir "$FAKE_PAR/run.$$"
  n=$(ls "$FAKE_PAR" | grep -c '^run\\.')
  echo "$n" >> "$FAKE_PAR/seen"
  sleep 0.3
  rmdir "$FAKE_PAR/run.$$"
fi
case "$(cat mode)" in
 fail) exit 1;;
 nocommit) exit 0;;
 merge)
  id=$(basename "$PWD")
  mkdir -p openspec/changes/archive/2026-01-01-$id
  echo a > openspec/changes/archive/2026-01-01-$id/f
  git add -A
  git -c user.name=t -c user.email=t@t commit -qm m
  exit 0;;
esac
"""


def build_copy(root):
    git(root, "init", "-q", "-b", "main")
    put(root, "README.md", "r\n")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "base")
    return git(root, "rev-parse", "HEAD")


def make_copy(folder, cid, mode="nocommit"):
    c = pathlib.Path(folder) / cid
    c.parent.mkdir(parents=True, exist_ok=True)
    tpl, base = shared_repo.template("make_copy", build_copy)
    shared_repo.copy(tpl, c)
    meta = {"config": "cfg1", "id": cid, "base": base, "main": "main"}
    put(c, ".sdd-eval", json.dumps(meta))
    (c / "mode").write_text(mode)
    with open(c / ".git/info/exclude", "a") as f:
        f.write(".sdd-eval\nmode\n")
    return c


@marks.release
class RunTests(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        fake = self.bin / "claude"
        fake.write_text(FAKE_CLAUDE)
        fake.chmod(fake.stat().st_mode | stat.S_IXUSR)
        self.count = self.root / "count"
        self.folder = self.root / "copies"
        self.folder.mkdir()

    def run_cmd(self, *args, path=None, par=None, log=None):
        env = dict(os.environ, FAKE_COUNT=str(self.count), PATH=path or "%s:/usr/bin:/bin" % self.bin,
                   HOME=str(self.root / "home"))
        if log:
            env["FAKE_LOG"] = str(log)
        if par:
            env["FAKE_PAR"] = str(par)
        return subprocess.run(["/usr/bin/python3", str(SCRIPT), "run", str(self.folder)] + list(args),
                              capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL, env=env)

    def journal(self, label="L1"):
        return json.loads((self.folder / "runs" / (label + ".json")).read_text(encoding="utf-8"))

    def calls(self):
        return self.count.read_text().splitlines() if self.count.exists() else []

    def test_run_statuses(self):
        make_copy(self.folder, "c-fail", "fail")
        make_copy(self.folder, "c-none", "nocommit")
        make_copy(self.folder, "c-ok", "merge")
        r = self.run_cmd("--label", "L1")
        self.assertEqual(r.returncode, 0, r.stderr)
        j = self.journal()
        self.assertEqual((j["label"], j["dispatcher_model"], j["config"]), ("L1", "sonnet", "cfg1"))
        st_ = {k: (v["exit"], v["status"]) for k, v in j["copies"].items()}
        self.assertEqual(st_, {"c-fail": (1, "not finished"), "c-none": (0, "not finished"), "c-ok": (0, "merged")})
        for v in j["copies"].values():
            self.assertTrue(v["start"].endswith("Z") and v["end"].endswith("Z") and v["start"] <= v["end"])
            self.assertEqual(len(v["session"]), 36)
            self.assertEqual(v["config"], "cfg1")
        self.assertEqual(r.stdout.splitlines(), ["c-fail not finished", "c-none not finished", "c-ok merged",
                                                 "finished 1 of 3"])
        self.assertTrue((self.folder / "runs/L1.c-ok.log").exists())
        sid = j["copies"]["c-ok"]["session"]
        self.assertIn("-p /spec-dispatch --model sonnet --session-id " + sid, self.calls())

    def test_repeat_label(self):
        make_copy(self.folder, "c1", "merge")
        self.assertEqual(self.run_cmd("--label", "L1").returncode, 0)
        n = len(self.calls())
        r = self.run_cmd("--label", "L1")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(len(self.calls()), n)

    def test_no_copies(self):
        r = self.run_cmd("--label", "L1")
        self.assertEqual(r.returncode, 2)
        self.assertEqual(self.calls(), [])

    def test_parallel(self):
        for i in range(5):
            make_copy(self.folder, "c%d" % i, "merge")
        r = self.run_cmd("--label", "L1", "--parallel", "3", "--dispatcher-model", "haiku")
        self.assertEqual(r.returncode, 0, r.stderr)
        j = self.journal()
        self.assertEqual(sorted(j["copies"]), ["c%d" % i for i in range(5)])
        self.assertEqual(j["dispatcher_model"], "haiku")
        self.assertEqual({v["status"] for v in j["copies"].values()}, {"merged"})
        self.assertIn("finished 5 of 5", r.stdout)

    def max_parallel(self, n):
        for i in range(6):
            make_copy(self.folder, "c%d" % i, "merge")
        par = self.root / "par"
        par.mkdir()
        r = self.run_cmd("--label", "L1", "--parallel", str(n), par=par)
        self.assertEqual(r.returncode, 0, r.stderr)
        return max(int(x) for x in (par / "seen").read_text().split())

    def test_parallel_limit(self):
        self.assertEqual(self.max_parallel(1), 1)

    def test_parallel_three(self):
        self.assertTrue(1 < self.max_parallel(3) <= 3)

    def test_claude_not_executable(self):
        (self.bin / "claude").chmod(0o644)
        make_copy(self.folder, "c1", "merge")
        make_copy(self.folder, "c2", "merge")
        r = self.run_cmd("--label", "L1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(sorted(self.journal()["copies"]), ["c1", "c2"])
        for v in self.journal()["copies"].values():
            self.assertEqual((v["exit"], v["status"]), (127, "not finished"))

    def test_no_claude(self):
        make_copy(self.folder, "c1", "merge")
        make_copy(self.folder, "c2", "merge")
        r = self.run_cmd("--label", "L1", path="/usr/bin:/bin")
        self.assertEqual(r.returncode, 0, r.stderr)
        for v in self.journal()["copies"].values():
            self.assertEqual((v["exit"], v["status"]), (127, "not finished"))


    def argv(self):
        return self.count.with_name("count.argv").read_text(encoding="utf-8").split("\0")[:-1]

    def test_answers_prompt(self):
        c = make_copy(self.folder, "c1", "merge")
        meta = json.loads((c / ".sdd-eval").read_text())
        meta["answers"] = {"Remove markers?": "Remove and clear", "Mode?": "local"}
        (c / ".sdd-eval").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
        self.assertEqual(self.run_cmd("--label", "L1").returncode, 0)
        a = self.argv()
        self.assertEqual(a[:2], ["-p", "/spec-dispatch"])
        txt = a[a.index("--append-system-prompt") + 1]
        self.assertIn("do not ask the owner", txt)
        self.assertIn("- Remove markers? → Remove and clear", txt.splitlines())
        self.assertIn("- Mode? → local", txt.splitlines())

    def test_prompt_flag_without_answers(self):
        make_copy(self.folder, "c1", "merge")
        self.assertEqual(self.run_cmd("--label", "L1").returncode, 0)
        a = self.argv()
        self.assertIn("do not ask the owner", a[a.index("--append-system-prompt") + 1])

    def ask(self, lines, cid="c1"):
        log = self.root / "fake.jsonl"
        log.write_text("\n".join(lines) + "\n", encoding="utf-8")
        make_copy(self.folder, cid, "merge")
        r = self.run_cmd("--label", "L-" + cid, log=log)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.journal("L-" + cid)["copies"][cid], r.stdout

    def text_line(self, text):
        return L(DAY + "09:00:00.000Z", "m1", OP, blocks=[{"type": "text", "text": text}])

    def test_question_ask_tool(self):
        q = {"questions": [{"question": "Mode?"}, {"question": "Remove markers?"}]}
        rec, out = self.ask([L(DAY + "09:00:00.000Z", "m1", OP, blocks=[tu("q1", "AskUserQuestion", q)])])
        self.assertEqual(rec["question"], "question: Mode?; Remove markers?")
        self.assertEqual(rec["status"], "merged")
        self.assertIn("c1 merged question: Mode?; Remove markers?", out.splitlines())

    def test_question_in_subagent(self):
        home = self.root / "home"
        d = home / ".claude/projects/x"
        (d / "s-1/subagents").mkdir(parents=True)
        (d / "s-1.jsonl").write_text(self.text_line("done") + "\n")
        (d / "s-1/subagents/agent-1.jsonl").write_text(L(
            DAY + "09:00:00.000Z", "m2", SN, blocks=[tu("q", "AskUserQuestion", {"questions": [{"question": "What?"}]})]))
        old = os.environ["HOME"]
        os.environ["HOME"] = str(home)
        self.addCleanup(os.environ.__setitem__, "HOME", old)
        self.assertEqual(ev.questions("s-1"), "What?")
        self.assertIsNone(ev.questions("no-such"))

    def test_question_need_from_you(self):
        rec, out = self.ask([self.text_line("Summary\n**Needs from you:** pick a mode\ntail")])
        self.assertEqual(rec["question"], "question: pick a mode")

    def test_need_from_you_in_subagent_not_counted(self):
        home = self.root / "home"
        d = home / ".claude/projects/x"
        (d / "s-2/subagents").mkdir(parents=True)
        (d / "s-2.jsonl").write_text(self.text_line("done") + "\n")
        (d / "s-2/subagents/agent-1.jsonl").write_text(L(
            DAY + "09:00:00.000Z", "m2", SN, blocks=[{"type": "text", "text": "Needs from you: pick a mode"}]))
        old = os.environ["HOME"]
        os.environ["HOME"] = str(home)
        self.addCleanup(os.environ.__setitem__, "HOME", old)
        self.assertIsNone(ev.questions("s-2"))

    def test_question_limit(self):
        rec, out = self.ask([self.text_line("Needs from you: " + "é" * 400)])
        self.assertEqual(len(rec["question"]), len("question: ") + 300)

    def test_question_on_next_line(self):
        for i, t in enumerate(("Needs from you:\n- pick a mode", "**Needs from you:**\n\npick a mode",
                               "Summary\nNeeds from you:\n\n* pick a mode\ntail")):
            rec, out = self.ask([self.text_line(t)], cid="c%d" % i)
            self.assertEqual(rec["question"], "question: pick a mode", t)

    def test_no_question_for_report_field(self):
        for i, t in enumerate(("Needs from you: nothing", "Needs from you: — None", "Needs from you:", "Needs from you: nothing needed",
                               "Needs from you: none", "Needs from you:\n\nnothing", "Needs from you:\n- None", "Summary\nNeeds from you:")):
            rec, out = self.ask([self.text_line(t)], cid="c%d" % i)
            self.assertNotIn("question", rec, t)
            self.assertIn("c%d merged" % i, out.splitlines())

    def test_question_starting_like_no(self):
        for i, q in enumerate(("a non-trivial mode choice", "no access to the API?", "No, but a branch is needed")):
            rec, _ = self.ask([self.text_line("Needs from you: " + q)], cid="c%d" % i)
            self.assertEqual(rec["question"], "question: " + q)

    def test_question_ask_tool_without_text(self):
        rec, _ = self.ask([L(DAY + "09:00:00.000Z", "m1", OP, blocks=[tu("q1", "AskUserQuestion", {})])])
        self.assertEqual(rec["question"], "question: no text")

    def test_no_session_log_no_question(self):
        make_copy(self.folder, "c1", "merge")
        self.assertEqual(self.run_cmd("--label", "L1").returncode, 0)
        self.assertNotIn("question", self.journal()["copies"]["c1"])


# ---- metrics ----

def L(ts, mid, model, inp=0, out=0, read=0, cc=0, block=None, blocks=()):
    u = {"input_tokens": inp, "output_tokens": out, "cache_read_input_tokens": read,
         "cache_creation_input_tokens": cc}
    if block:
        u["cache_creation"] = {"ephemeral_5m_input_tokens": block[0], "ephemeral_1h_input_tokens": block[1]}
    return json.dumps({"type": "assistant", "timestamp": ts, "message": {"id": mid, "model": model, "usage": u,
                                                                         "content": list(blocks)}})


def tu(i, name, inp=None):
    return {"type": "tool_use", "id": i, "name": name, "input": inp or {}}


def tr(i, text):
    return json.dumps({"type": "user", "timestamp": "2026-10-23T%s.000Z" % text[0], "message": {"content": [
        {"type": "tool_result", "tool_use_id": i, "content": text[1]}]}})


PRICES = {"claude-opus-5-5": {"input": 4, "output": 20, "cache_write_5m": 5, "cache_write_1h": 8, "cache_read": 0.2},
          "claude-sonnet-5-5": {"input": 2, "output": 10, "cache_write_5m": 2.5, "cache_write_1h": 4,
                                "cache_read": 0.1}}
OP, SN = "claude-opus-5-5", "claude-sonnet-5-5"
DAY = "2026-10-23T"


def main_log():
    z = lambda t, mid, *b: L(DAY + t + ".000Z", mid, OP, blocks=b)
    return "\n".join([
        L(DAY + "09:00:00.000Z", "msg_m1", OP, inp=10, out=5, read=1000, cc=200),
        L(DAY + "09:00:01.000Z", "msg_m1", OP, inp=10, out=20, read=1000, cc=200),
        "not json {",
        L(DAY + "09:00:02.000Z", "msg_m1", OP, inp=10, out=50, read=1000, cc=200),
        L(DAY + "09:00:03.000Z", "msg_syn", "<synthetic>", inp=999, out=999),
        L(DAY + "10:00:00.000Z", "msg_m2", OP, inp=1, out=2, blocks=[tu("a1", "Agent", {"description": "Orchestrator x"})]),
        z("10:05:00", "msg_z1", tu("sm1", "SendMessage")),
        z("10:06:00", "msg_z2", tu("sm2", "SendMessage")),
        z("10:59:00", "msg_z3", tu("b1", "Bash", {"command": "gh api -X PUT merge"})),
        tr("b1", ("11:00:00", '{"sha":"s1","merged":true}')),
        z("12:00:00", "msg_z4", tu("b2", "Bash", {"command": "sdd-pr.py merge 5"})),
        tr("b2", ("12:00:00", [{"type": "text", "text": "PR #5 x merged (squash)"}])),
        z("12:10:00", "msg_z5", tu("b3", "Bash", {"command": "sdd-pr.py merge 5"})),
        tr("b3", ("12:30:00", "PR #5 x merged (already)")),
        z("12:50:00", "msg_z6", tu("b4", "Bash", {"command": "git merge -q --no-ff --no-edit change/foo"})),
        tr("b4", ("13:00:00", "exit 0")),
        z("13:10:00", "msg_z7", tu("b5", "Bash", {"command": "git merge -q --no-ff --no-edit change/bar"})),
        tr("b5", ("13:20:00", "exit 1")),
        json.dumps({"type": "cost-state", "totalCostUSD": 2.5, "modelUsage": {OP: {"outputTokens": 1000}}}),
    ]) + "\n"


SUB_IMPL = "\n".join([
    L(DAY + "10:10:00.000Z", "msg_s1", SN, inp=5, out=3, read=50, cc=400, block=(100, 300)),
    L(DAY + "10:10:01.000Z", "msg_s1", SN, inp=5, out=7, read=50, cc=400, block=(100, 300)),
    L(DAY + "10:10:02.000Z", "msg_m1", OP, inp=10, out=50, read=1000, cc=200),
]) + "\n"
SUB_GEN = tr("x", ("10:20:00", [{"type": "text", "text": "Status not accepted by the hook, mismatches:\n- x"}])) + "\n"


@marks.release
class MetricsSession(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.root, True)
        self.home = self.root / "home"
        self.proj = self.home / ".claude/projects/x"
        self.proj.mkdir(parents=True)
        self.prices = self.root / "prices.json"
        self.set_prices(PRICES)

    def set_prices(self, d):
        self.prices.write_text(json.dumps(d))

    def hand(self, sid="hand", big=False):
        extra = L(DAY + "10:30:00.000Z", "msg_big", OP, read=6000000) + "\n" if big else ""
        (self.proj / (sid + ".jsonl")).write_text(main_log() + extra, encoding="utf-8")
        sub = self.proj / sid / "subagents"
        sub.mkdir(parents=True)
        for n, desc, body in (("agent-1", "Implement: a", SUB_IMPL), ("agent-2", "Explore b", SUB_GEN)):
            if big and n == "agent-1":
                body += L(DAY + "10:30:00.000Z", "msg_big2", SN, read=3000000) + "\n"
            (sub / (n + ".jsonl")).write_text(body, encoding="utf-8")
            (sub / (n + ".meta.json")).write_text(json.dumps({"description": desc}))

    def metrics(self, *args):
        return subprocess.run(["/usr/bin/python3", str(SCRIPT), "metrics"] + list(args), capture_output=True,
                              text=True, timeout=120, stdin=subprocess.DEVNULL,
                              env=dict(os.environ, HOME=str(self.home)))

    def load(self, sid="hand"):
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(self.home)
        self.addCleanup(os.environ.__setitem__, "HOME", old)
        return ev.session_metrics(sid, json.loads(self.prices.read_text()))

    def test_hand_written(self):
        self.hand()
        m = self.load()
        self.assertEqual(m["roles"]["dispatcher/" + OP], {"input": 11, "cache_5m": 200, "cache_1h": 0,
                                                         "cache_read": 1000, "output": 52, "input_total": 1211})
        self.assertEqual(m["roles"]["implement/" + SN], {"input": 5, "cache_5m": 100, "cache_1h": 300,
                                                        "cache_read": 50, "output": 7, "input_total": 455})
        self.assertEqual(sorted(m["roles"]), ["dispatcher/" + OP, "implement/" + SN])
        self.assertEqual(m["models"][OP]["output"], 1000)
        self.assertEqual(m["models"][OP]["output_source"], "cost-state")
        self.assertEqual(m["models"][SN]["output"], 7)
        self.assertEqual(m["models"][SN]["output_source"], "journal")
        self.assertEqual(m["agents"], {"orchestrator": 0, "implement": 1, "general": 1, "review": 0})
        self.assertEqual((m["returns"], m["rejected"], m["merged"]), (2, 1, 3))
        self.assertEqual(m["first_orchestrator"], DAY + "10:00:00.000Z")
        self.assertEqual(m["last_merge"], DAY + "13:00:00.000Z")
        self.assertAlmostEqual(m["hours"], 3.0)
        self.assertEqual(m["cost_state_usd"], 2.5)
        self.assertEqual(m["unpriced"], [])
        self.assertAlmostEqual(m["cost_usd"], (2284 + 948 * 20 + 1535) / 1e6, places=12)

    def test_unpriced(self):
        self.hand()
        self.set_prices({OP: PRICES[OP]})
        m = self.load()
        self.assertIsNone(m["cost_usd"])
        self.assertEqual(m["unpriced"], [SN])

    def test_unpriced_cli_and_total(self):
        self.hand()
        self.set_prices({OP: PRICES[OP]})
        r = self.metrics("--session", "hand", "--prices", str(self.prices))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[-1], "cost: n/a (no price: %s)" % SN)
        folder = self.root / "copies"
        make_copy(folder, "ca")
        put(folder, "runs/L1.json", json.dumps({"label": "L1", "copies": {
            "ca": {"session": "hand", "status": "not finished"}}}))
        old = os.environ.get("HOME")
        os.environ["HOME"] = str(self.home)
        self.addCleanup(os.environ.__setitem__, "HOME", old)
        data, _ = ev.label_metrics(folder, "L1", json.loads(self.prices.read_text()))
        self.assertEqual(data["total"]["unpriced"], [SN])
        self.assertIsNone(data["total"]["cost_usd"])

    def test_long_tariff(self):
        self.hand()
        lg = {"above": 400, "input": 20, "output": 100, "cache_write_5m": 25, "cache_write_1h": 40, "cache_read": 1}
        self.set_prices({OP: PRICES[OP], SN: dict(PRICES[SN], long=lg)})
        self.assertAlmostEqual(self.load()["cost_usd"], (2284 + 948 * 20 + 15350) / 1e6, places=12)

    def test_cli_session(self):
        self.hand(big=True)
        r = self.metrics("--session", "hand", "--prices", str(self.prices))
        self.assertEqual(r.returncode, 0, r.stderr)
        # dispatcher 1211 + 6 000 000, executor 455 + 3 000 000; divided by 3 merges
        self.assertEqual(r.stdout.splitlines(), [
            "merged: 3", "time: 3.00 h",
            "dispatcher/%s: 2.00M per change" % OP, "implement/%s: 1.00M per change" % SN,
            "agents: orchestrator 0, implement 1, general 1, review 0",
            "returns: 2, rejected statuses: 1", "cost: $1.52 (cost-state $2.50)"])

    def test_fixture(self):
        shutil.copy(FIX / "fixture-session.jsonl", self.proj)
        shutil.copytree(FIX / "fixture-session", self.proj / "fixture-session")
        r = self.metrics("--session", "fixture-session", "--prices", str(ROOT / "tests/eval/prices.json"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("merged: 1", r.stdout)
        self.assertIn("\ntime: 0.47 h\n", "\n" + r.stdout)  # 20:02:00 -> 20:30:00 = 28 min
        self.assertIn("agents: orchestrator 1, implement 1, general 0, review 1", r.stdout)
        self.assertIn("returns: 1, rejected statuses: 1", r.stdout)
        self.assertIn("(cost-state $1.50)", r.stdout)

    def test_no_session_and_prices(self):
        r = self.metrics("--session", "nope", "--prices", str(self.prices))
        self.assertEqual((r.returncode, r.stderr.strip()), (3, "journal not found: nope"))
        self.assertEqual(self.metrics("--session", "nope", "--prices", "/no/such.json").returncode, 2)
        self.assertEqual(self.metrics("--prices", str(self.prices)).returncode, 2)

    def test_folder(self):
        shutil.copy(FIX / "fixture-session.jsonl", self.proj)
        shutil.copytree(FIX / "fixture-session", self.proj / "fixture-session")
        folder = self.root / "copies"
        a, b = make_copy(folder, "ca"), make_copy(folder, "cb")
        (a / "f.txt").write_text("x")
        git(a, "add", "-A")
        subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-C", str(a), "commit", "-qm", "m"],
                       check=True, env=dict(os.environ, GIT_COMMITTER_DATE="2026-10-23T22:02:00Z"))
        put(folder, "runs/L1.json", json.dumps({"label": "L1", "copies": {
            "ca": {"session": "fixture-session", "status": "merged"},
            "cb": {"session": "nope", "status": "not finished"}}}))
        args = ["metrics", str(folder), "--label", "L1", "--prices", str(ROOT / "tests/eval/prices.json")]
        r = subprocess.run(["/usr/bin/python3", str(SCRIPT)] + args, capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, env=dict(os.environ, HOME=str(self.home)))
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("cb journal not found", r.stdout)
        out = json.loads((folder / "runs/L1.metrics.json").read_text(encoding="utf-8"))
        self.assertEqual(out["copies"]["cb"]["error"], "journal not found")
        self.assertAlmostEqual(out["copies"]["ca"]["hours"], 2.0)
        self.assertEqual(out["copies"]["ca"]["merged"], 1)
        self.assertEqual(out["total"]["rejected"], 1)
        self.assertIsNotNone(out["total"]["cost_usd"])
        self.assertIn(OP, out["total"]["models"])
        self.assertTrue(r.stdout.splitlines()[0].startswith("ca merged 2.00 $"))
        r = subprocess.run(["/usr/bin/python3", str(SCRIPT)] + args[:3] + ["L9"] + args[4:], capture_output=True,
                           text=True, stdin=subprocess.DEVNULL, env=dict(os.environ, HOME=str(self.home)))
        self.assertEqual(r.returncode, 2)


FIX_LINES = [ln for p in [FIX / "fixture-session.jsonl"] + sorted((FIX / "fixture-session/subagents").glob("*.jsonl"))
             for ln in p.read_text(encoding="utf-8").splitlines()]


@marks.release
class MainBranch(unittest.TestCase):
    def test_origin_head_wins(self):
        with tempfile.TemporaryDirectory() as d:
            git(d, "init", "-q", "-b", "work")
            git(d, "commit", "-q", "--allow-empty", "-m", "x")
            self.assertEqual(ev.main_branch(d), "work")
            git(d, "update-ref", "refs/remotes/origin/trunk", "HEAD")
            git(d, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/trunk")
            self.assertEqual(ev.main_branch(d), "trunk")


@marks.release
class LandLocalMerges(unittest.TestCase):
    def merges(self, text):
        return ev.merges([
            {"message": {"content": [{"type": "tool_use", "id": "b", "name": "Bash",
                                      "input": {"command": "python3 sdd-dispatch.py land-local M W x --check t"}}]}},
            {"timestamp": "T", "message": {"content": [{"type": "tool_result", "tool_use_id": "b", "content": text}]}}])

    def test_land_local_counted(self):
        self.assertEqual(self.merges("merged abc123"), {"abc123": "T"})
        self.assertEqual(self.merges("merged abc123, not cleaned: remove: x"), {"abc123": "T"})

    def test_land_local_refused_not_counted(self):
        self.assertEqual(self.merges("not merged: merge conflict: f"), {})


@marks.release
class MetricsProperties(unittest.TestCase):
    @settings(max_examples=50, deadline=None)
    @given(st.permutations(FIX_LINES), st.lists(st.integers(0, len(FIX_LINES) - 1), max_size=20))
    def test_metrics_one_method_order_and_repeats(self, perm, extra):
        want = ev.usage_by_message(FIX_LINES)
        self.assertTrue(want)
        self.assertEqual(ev.usage_by_message(list(perm) + [FIX_LINES[i] for i in extra]), want)

    def test_metrics_null_counter_is_zero(self):
        got = ev.usage_by_message([L("t", "m", OP, inp=None, out=5), L("t", "m", OP, inp=7, out=None, read=None)])
        self.assertEqual((got["m"]["input"], got["m"]["output"], got["m"]["cache_read"]), (7, 5, 0))
        got = ev.usage_by_message([L("t", "m", OP, inp=None), L("t", "m", OP, inp=3)])
        self.assertEqual(got["m"]["input"], 3)

    def test_metrics_one_method_max_not_sum(self):
        got = ev.usage_by_message([L("t", "m", OP, out=5), L("t", "m", OP, out=20), L("t", "m", OP, out=20)])
        self.assertEqual(got["m"]["output"], 20)


# ---- compare ----

RUNNER = ("[ -n \"$COUNT_FILE\" ] && echo run >> \"$COUNT_FILE\"\nrc=0\n"
          "for f in \"$@\"; do sh \"$f\" || { echo \"FAIL  $f > f\"; rc=1; }; done\nexit $rc\n")
CMP_AGENTS = "# P\n\n## Commands\n\n| What | Command |\n|---|---|\n| Tests | `sh run-tests.sh` — note |\n"
PRICES_FILE = str(ROOT / "tests/eval/prices.json")


def build_cmp(root):
    """The project of CmpEnv in root/proj; returns its oracles and bases."""
    proj = root / "proj"
    proj.mkdir()
    git(proj, "init", "-q", "-b", "main")
    put(proj, "run-tests.sh", RUNNER)
    put(proj, "old.test.sh", "exit 0\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "base")
    oracle, base = {}, {}
    for cid in ("c1", "c2"):
        base[cid] = git(proj, "rev-parse", "HEAD")
        put(proj, cid + ".test.sh", ". ./code_%s.sh\ntype f_%s >/dev/null 2>&1\n" % (cid, cid))
        git(proj, "add", "-A")
        git(proj, "commit", "-qm", cid)
        oracle[cid] = git(proj, "rev-parse", "HEAD")
    base["c3"] = git(proj, "rev-parse", "HEAD")
    git(proj, "rm", "-q", "old.test.sh")
    git(proj, "commit", "-qm", "c3")
    oracle["c3"] = git(proj, "rev-parse", "HEAD")
    base["c4"] = oracle["c3"]
    put(proj, "c4.test.sh", "test -f built/data.txt\n")
    git(proj, "add", "-A")
    git(proj, "commit", "-qm", "c4")
    oracle["c4"] = git(proj, "rev-parse", "HEAD")
    return oracle, base


def build_cmp_copy(root, proj, base, cid, kind):
    """A copy of kind for cid in root/c, cloned from proj: everything of CmpEnv.copy except the per-test files."""
    c = root / "c"
    git(root, "clone", "-q", "--no-checkout", str(proj), str(c))
    git(c, "checkout", "-q", "-B", "main", base)
    git(c, "remote", "remove", "origin")
    if kind in ("good", "red"):
        put(c, "code_%s.sh" % cid, "f_%s() { :; }\n" % cid if kind == "good" else "x=1\n")
        git(c, "add", "-A")
        git(c, "commit", "-qm", "merge")
    if kind == "built":  # prepare result: the ignored folder exists only in the copy
        put(c, "built/data.txt", "x\n")
        put(c, ".git/info/exclude", (c / ".git/info/exclude").read_text() + "built/\n")


class CmpEnv:
    """A toy project with oracles c1, c2 (the test sources code_<id>.sh and looks for the function f_<id>) and c3 (the oracle only deletes the test).
    The project and each kind of copy are built once (tests/shared_repo.py) and copied per test."""

    def __init__(self):
        self.tpl, (oracle, base) = shared_repo.template("CmpEnv", build_cmp)
        self.root = shared_repo.copy(self.tpl)
        self.proj = self.root / "proj"
        self.oracle, self.base = dict(oracle), dict(base)
        self.count = self.root / "count"
        self.agents = CMP_AGENTS
        self.meta_extra = {}

    def copy(self, folder, cid, kind, notes=()):
        """kind: good, red (code without the function), missing (no code), none (nothing merged)."""
        c = pathlib.Path(folder) / cid
        tpl, _ = shared_repo.template(("CmpEnv.copy", cid, kind, self.base[cid]), lambda root: build_cmp_copy(
            root, self.tpl / "proj", self.base[cid], cid, kind))
        shared_repo.copy(tpl / "c", c, {self.tpl / "proj": self.proj})  # the clone's reflog names its project
        put(c, "AGENTS.md", self.agents)
        meta = {"config": "cfg", "id": cid, "oracle": self.oracle[cid], "base": self.base[cid], "main": "main",
                "project": str(self.proj), "spec_notes": list(notes), "tests": ["*.test.sh"], **self.meta_extra}
        put(c, ".sdd-eval", json.dumps(meta))
        with open(c / ".git/info/exclude", "a") as f:
            f.write(".sdd-eval\nAGENTS.md\n")

    def label(self, E, label, kinds, sub=True, notes=()):
        """Folder E/<label> (or E) with copies and the log runs/<label>.json; kinds: {id: kind}."""
        f = pathlib.Path(E) / label if sub else pathlib.Path(E)
        (f / "runs").mkdir(parents=True, exist_ok=True)
        copies = {}
        for cid, kind in kinds.items():
            self.copy(f, cid, kind, notes)
            copies[cid] = {"session": "none-" + label, "start": "", "end": "", "exit": 0,
                           "status": "not finished" if kind == "none" else "merged"}
        put(f, "runs/%s.json" % label, json.dumps({"label": label, "config": "cfg", "copies": copies}))
        return f

    def compare(self, E, a, b, *extra):
        return subprocess.run(["/usr/bin/python3", str(SCRIPT), "compare", str(E), "--a"] + a + ["--b"] + b +
                              ["--prices", PRICES_FILE] + list(extra), capture_output=True, text=True, timeout=300,
                              stdin=subprocess.DEVNULL, env=dict(os.environ, COUNT_FILE=str(self.count)))

    def runs(self):
        return len(self.count.read_text().split()) if self.count.exists() else 0

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)


def cmp_env(t):
    e = CmpEnv()
    t.addCleanup(e.close)
    e.E = e.root / "E"
    e.E.mkdir()
    return e


G, R = {"c1": "good", "c2": "good"}, {"c1": "red", "c2": "good"}


@marks.release
class CompareTests(unittest.TestCase):
    def mk(self, a, b):
        """a, b: {label: {id: kind}}"""
        e = cmp_env(self)
        for lb, k in list(a.items()) + list(b.items()):
            e.label(e.E, lb, k)
        r = e.compare(e.E, list(a), list(b))
        self.assertEqual(r.returncode, 0, r.stderr)
        return e, r.stdout

    def test_merged_red(self):
        e, out = self.mk({"p1": R, "p2": R}, {"q1": G, "q2": G})
        self.assertRegex(out, r"\| c1 \| merged, oracle red: c1\.test\.sh > f [^|]*\|")
        self.assertIn("| a | 1, 1 of 2 |", out)
        self.assertIn("| b | 2, 2 of 2 |", out)
        self.assertIn("- c1: done in every run of b, not done in p1: c1.test.sh > f; p2: c1.test.sh > f", out)

    def test_green_done(self):
        e, out = self.mk({"p1": G, "p2": G}, {"q1": G, "q2": G})
        row = [ln for ln in out.splitlines() if ln.startswith("| c1 ")][0]
        self.assertEqual(row.count("done"), 4)
        self.assertNotIn("red", out)
        self.assertIn("Flipped: none", out)
        self.assertIn("# Comparison: a = p1, p2; b = q1, q2", out)
        self.assertIn("n/a", row)

    def test_green_done_metrics_values(self):
        e = cmp_env(self)
        for lb in ("p1", "p2", "q1", "q2"):
            f = e.label(e.E, lb, G)
            cs = {c: {"hours": 1.25, "cost_usd": 2.5} for c in G}
            put(f, "runs/%s.metrics.json" % lb, json.dumps({"label": lb, "copies": cs}))
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        row = [ln for ln in r.stdout.splitlines() if ln.startswith("| c1 ")][0]
        self.assertEqual(row.count("done 1.25 h $2.50"), 4, row)
        self.assertIn("| a | 2, 2 of 2 | 5.00 | $10.00 |", r.stdout)
        self.assertIn("| b | 2, 2 of 2 | 5.00 | $10.00 |", r.stdout)

    def test_oracle_prepare_runs_before_tests(self):
        e = cmp_env(self)
        e.meta_extra = {"oracle_prepare": "mkdir -p built && echo x > built/data.txt"}
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, {"c4": "missing"})
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("| a | 1, 1 of 1 |", r.stdout)
        self.assertNotIn("red", r.stdout)

    def test_oracle_prepare_failure_is_red(self):
        e = cmp_env(self)
        e.meta_extra = {"oracle_prepare": "exit 5"}
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, {"c4": "built"})  # without oracle_prepare the oracle test would be green
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("merged, oracle red: oracle_prepare: code 5", r.stdout)
        self.assertIn("| a | 0, 0 of 1 |", r.stdout)
        self.assertEqual(e.runs(), 0)

    def test_oracle_prepare_timeout(self):
        e = cmp_env(self)
        e.meta_extra = {"oracle_prepare": "sleep 30"}
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, {"c4": "built"})
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"], "--timeout", "1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("oracle_prepare: timeout 1 s", r.stdout)

    def test_no_prices_file_warning(self):
        e = cmp_env(self)
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, G)
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"], "--prices", "/no/such.json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("price file not found: /no/such.json; time and cost n/a", r.stderr.splitlines())
        self.assertIn("| a | 2, 2 of 2 | n/a | n/a |", r.stdout)

    def test_missing_module_is_red(self):
        e, out = self.mk({"p1": {"c1": "missing"}, "p2": {"c1": "missing"}}, {"q1": {"c1": "good"}, "q2": {"c1": "good"}})
        self.assertIn("merged, oracle red: c1.test.sh", out)
        self.assertIn("| a | 0, 0 of 1 |", out)

    def test_no_oracle_files_is_red(self):
        e, out = self.mk({"p1": {"c3": "none"}, "p2": {"c3": "none"}}, {"q1": {"c3": "good"}, "q2": {"c3": "good"}})
        self.assertIn("not merged", out)
        self.assertIn("merged, oracle red: no oracle files", out)
        self.assertIn("| b | 0, 0 of 1 |", out)

    def test_unfinished_not_run(self):
        e, out = self.mk({"p1": {"c1": "none", "c2": "good"}, "p2": {"c1": "none", "c2": "good"}},
                         {"q1": {"c1": "none", "c2": "good"}, "q2": {"c1": "none", "c2": "good"}})
        row = [ln for ln in out.splitlines() if ln.startswith("| c1 ")][0]
        self.assertEqual(row.count("not merged"), 4)
        self.assertEqual(e.runs(), 4)

    def test_flips_both_directions(self):
        e, out = self.mk({"p1": {"c1": "good", "c2": "red"}, "p2": {"c1": "good", "c2": "good"}},
                         {"q1": {"c1": "red", "c2": "good"}, "q2": {"c1": "good", "c2": "good"}})
        self.assertIn("- c1: done in every run of a, not done in q1: c1.test.sh > f", out)
        self.assertIn("- c2: done in every run of b, not done in p1: c2.test.sh > f", out)

    def test_self_compare_runs_once_per_label(self):
        e = cmp_env(self)
        e.label(e.E, "x", G)
        e.label(e.E, "y", R)
        r = e.compare(e.E, ["x", "y"], ["x", "y"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Flipped: none", r.stdout)
        self.assertEqual(e.runs(), 4)
        self.assertEqual(r.stdout.splitlines()[0], "# Comparison: a = x, y; b = x, y")

    def test_one_label(self):
        e = cmp_env(self)
        r = e.compare(e.E, ["x", "y"], ["z"])
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("2 or more runs needed: b", r.stderr.splitlines())
        self.assertEqual(e.runs(), 0)
        self.assertIn("2 or more runs needed: a", e.compare(e.E, ["x"], ["z", "w"]).stderr.splitlines())

    def test_no_journal(self):
        e = cmp_env(self)
        r = e.compare(e.E, ["x", "y"], ["z", "w"])
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("x", r.stderr)

    def test_no_test_command(self):
        e = cmp_env(self)
        e.label(e.E, "p1", G)
        e.agents = "# P\n\n## Commands\n\n| What | Command |\n|---|---|\n| Build | `make` |\n"
        e.label(e.E, "p2", G)
        for lb in ("q1", "q2"):
            e.label(e.E, lb, G)
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("no test command: c1 (%s)" % (e.E / "p2/c1"), r.stderr)
        self.assertEqual(e.runs(), 0)

    def test_single_folder(self):
        e = cmp_env(self)
        f = e.label(e.E, "x", G, sub=False)
        shutil.copy(f / "runs/x.json", f / "runs/y.json")
        r = e.compare(e.E, ["x", "y"], ["x", "y"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(e.runs(), 4)

    def test_cleanup_and_main_unchanged(self):
        e, out = self.mk({"p1": R, "p2": G}, {"q1": G, "q2": G})
        c = e.E / "p1/c1"
        self.assertEqual(len(git(c, "worktree", "list").splitlines()), 1)
        self.assertEqual(git(c, "rev-parse", "main"), git(c, "rev-parse", "HEAD"))
        self.assertEqual(git(c, "log", "-1", "--format=%s", "main"), "merge")
        self.assertEqual(git(c, "status", "--porcelain"), "")

    def test_spec_notes(self):
        e = cmp_env(self)
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, G, notes=["spec after the change: c1 Zeta", "spec after the change: c1 Alpha"])
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertTrue(r.stdout.endswith("Spec after the change:\n- spec after the change: c1 Alpha\n"
                                          "- spec after the change: c1 Zeta\n"), r.stdout)

    def test_spec_notes_from_unfinished_copy(self):
        e = cmp_env(self)
        for lb in ("p1", "p2"):
            e.label(e.E, lb, {"c1": "none", "c2": "good"}, notes=["spec after the change: c1 Beta"])
        for lb in ("q1", "q2"):
            e.label(e.E, lb, G)
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("- spec after the change: c1 Beta", r.stdout.splitlines())

    def test_oracle_run_no_files(self):
        e = cmp_env(self)
        f = e.label(e.E, "p1", {"c3": "good"})
        meta = json.loads((f / "c3/.sdd-eval").read_text())
        self.assertEqual(ev.oracle_tests(meta["project"], meta["oracle"], meta["tests"]), [])
        o = ev.oracle_run(str(f / "c3"), meta, 60)
        self.assertEqual((o["green"], o["failed"]), (False, ["no oracle files"]))

    def test_ignored_prepare_results_visible(self):
        e = cmp_env(self)
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, {"c4": "built"})
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        row = [ln for ln in r.stdout.splitlines() if ln.startswith("| c4 ")][0]
        self.assertEqual(row.count("done"), 4, row)
        for lb in ("p1", "q2"):
            self.assertEqual((e.E / lb / "c4/built/data.txt").read_text(), "x\n")
            self.assertEqual(len(git(e.E / lb / "c4", "worktree", "list").splitlines()), 1)

    def test_unique_labels_counted(self):
        e = cmp_env(self)
        r = e.compare(e.E, ["x", "y"], ["z", "z"])
        self.assertEqual((r.returncode, r.stdout), (2, ""))
        self.assertIn("2 or more runs needed: b", r.stderr.splitlines())

    def test_chained_command(self):
        e = cmp_env(self)
        e.agents = CMP_AGENTS.replace("`sh run-tests.sh`", "`sh run-tests.sh && true`")
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, G)
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("test command is a chain: c1 (%s)" % (e.E / "p1/c1"), r.stderr)
        self.assertEqual(e.runs(), 0)

    def test_chained_pipe_in_backticks(self):
        e = cmp_env(self)
        e.agents = CMP_AGENTS.replace("`sh run-tests.sh`", "`a | b`")
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, G)
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("test command is a chain: c1 (%s)" % (e.E / "p1/c1"), r.stderr)

    def test_sum_unknown_when_copy_has_no_price(self):
        e = cmp_env(self)
        for lb in ("a1", "a2", "b1", "b2"):
            f = e.label(e.E, lb, {"c1": "good", "c2": "good"})
            cost = None if lb == "a1" else 2.0
            put(f, "runs/%s.metrics.json" % lb, json.dumps({"copies": {"c1": {"hours": 1.0, "cost_usd": 2.0},
                                                                     "c2": {"hours": 1.0, "cost_usd": cost}}}))
        r = e.compare(e.E, ["a1", "a2"], ["b1", "b2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        rows = {ln.split("|")[1].strip(): ln for ln in r.stdout.splitlines() if ln.startswith("| ")}
        self.assertTrue(rows["a"].rstrip(" |").endswith("n/a"), rows["a"])
        self.assertTrue(rows["b"].rstrip(" |").endswith("$8.00"), rows["b"])

    def test_copy_without_meta_is_code_3(self):
        e = cmp_env(self)
        for lb in ("a1", "a2", "b1", "b2"):
            e.label(e.E, lb, {"c1": "good"})
        os.remove(e.E / "a1/c1/.sdd-eval")
        r = e.compare(e.E, ["a1", "a2"], ["b1", "b2"])
        self.assertEqual(r.returncode, 3, r.stderr)
        self.assertIn("oracle failed: c1", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_oracle_failure_no_traceback(self):
        e = cmp_env(self)
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, G)
        mp = e.E / "p1/c1/.sdd-eval"
        mp.write_text(json.dumps(dict(json.loads(mp.read_text()), main="nope")))
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual((r.returncode, r.stdout), (3, ""))
        self.assertIn("oracle failed: c1: ", r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_no_spec_block_without_notes(self):
        e, out = self.mk({"p1": G, "p2": G}, {"q1": G, "q2": G})
        self.assertNotIn("Spec after the change", out)


@marks.release
class QuestionCompare(unittest.TestCase):
    def test_question_not_flip(self):
        e = cmp_env(self)
        for lb, k in (("p1", G), ("p2", G), ("q1", R), ("q2", G)):
            e.label(e.E, lb, k)
        jp = e.E / "q1/runs/q1.json"
        j = json.loads(jp.read_text())
        j["copies"]["c1"]["question"] = "question: pick a mode"
        jp.write_text(json.dumps(j))
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertEqual(r.returncode, 0, r.stderr)
        row = next(ln for ln in r.stdout.splitlines() if ln.startswith("| c1 |"))
        cells = [c.strip() for c in row.strip("|").split(" | ")]
        self.assertEqual(["(question)" in c for c in cells[1:]], [False, False, True, False])
        self.assertIn("| a | 2, 2 of 2 |", r.stdout)
        self.assertIn("| b | 1, 2 of 2 |", r.stdout)
        self.assertIn("\nWith a question:\n- c1: q1: question: pick a mode\n", r.stdout + "\n")
        self.assertNotIn("- c1: done", r.stdout)

    def test_no_section_without_question(self):
        e = cmp_env(self)
        for lb in ("p1", "p2", "q1", "q2"):
            e.label(e.E, lb, G)
        r = e.compare(e.E, ["p1", "p2"], ["q1", "q2"])
        self.assertNotIn("With a question", r.stdout)
        self.assertNotIn("(question)", r.stdout)


@marks.release
class ParseFailed(unittest.TestCase):
    def test_ansi_and_dups(self):
        out = "\x1b[31mFAIL\x1b[0m  a.test.js > one\n  FAIL  a.test.js > one\nok\n\x1b[1m FAIL  b > two\x1b[0m\n"
        self.assertEqual(ev.parse_failed(out), ["a.test.js > one", "b > two"])

    def test_limit_and_empty(self):
        self.assertEqual(len(ev.parse_failed("\n".join("FAIL  t%d" % i for i in range(50)))), 20)
        self.assertEqual(ev.parse_failed("all fine\n"), [])

    def test_test_command(self):
        d = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, d, True)
        self.assertIsNone(ev.test_command(str(d)))
        (d / "AGENTS.md").write_text(CMP_AGENTS)
        self.assertEqual(ev.test_command(str(d)), "sh run-tests.sh")
        (d / "AGENTS.md").write_text("## Commands\n\n| What | C |\n|---|---|\n| Tests | `a | b` |\n")
        self.assertEqual(ev.test_command(str(d)), "a | b")
        (d / "AGENTS.md").write_text("## Commands\n\n| What | C |\n|---|---|\n| Build | `make` |\n")
        self.assertIsNone(ev.test_command(str(d)))


if __name__ == "__main__":
    unittest.main()
