"""The ablation runner `tests/stands/skill-ablation.py` (Requirements: Ablation runner, Ablation grade, Grade outcomes,
Runner input refused, Full skill out of reach in the cut variants, Task sets) on fixture skills and task sets, on
transcripts in the form Claude Code writes them, and on the committed task sets."""
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest

from hypothesis import given, settings, strategies as st

REPO = pathlib.Path(__file__).resolve().parents[1]
STAND = REPO / "tests/stands/skill-ablation.py"
spec = importlib.util.spec_from_file_location("skill_ablation", STAND)
sa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sa)

METHOD, GATE = "Think about the WIDGET-METHOD first.", "Never skip the WIDGET-GATE."
SKILL = "---\nname: widget\n---\n# widget\n\n## Order\n\n1. **Look.** %s\n2. **Hold.** %s\n" % (METHOD, GATE)
ROW = "| Order | %s | %s |  |  |"
CHECK = "import sys\nsys.exit(0 if 'RIGHT' in open(sys.argv[1]).read() else 1)\n"


def fixture(root, tasks=("t1", "t2"), method=True, extra=()):
    """A repository root with the skill `widget` (a method and a gate step), its audit table and its task set."""
    root = pathlib.Path(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / "targets.json").write_text(json.dumps({"skills": {n: ["claude"] for n in ("widget", "plain") + extra}}))
    for name in ("widget", "plain"):
        (root / "skills" / name).mkdir(parents=True)
    (root / "skills/widget/SKILL.md").write_text(SKILL)
    (root / "skills/plain/SKILL.md").write_text("# plain\n\nNo steps.\n")
    (root / "docs").mkdir()
    rows = [ROW % ("1. Look", "method" if method else "gate (code)"), ROW % ("2. Hold", "gate (code)")]
    head = ["| Heading | Step | Mark | Hook | Why |", "|---|---|---|---|---|"]
    (root / "docs/skills-audit.md").write_text("\n".join(["## widget", ""] + head + rows + ["", "## plain", ""] + head
                                                         + ["|  | whole text | method |  |  |", "", "## Gates a hook could hold", ""]) + "\n")
    for t in tasks:
        d = root / "tests/stands/skill-ablation/widget" / t
        (d / "fixture").mkdir(parents=True)
        (d / "fixture/data.txt").write_text("data of %s\n" % t)
        (d / "prompt.md").write_text("Solve task %s and say RIGHT.\n" % t)
        (d / "check.py").write_text(CHECK)
        (d / "required.txt").write_text("data\\.txt\n")
    return root


def call(name, inp):
    return {"type": "tool_use", "id": "toolu_%s" % name, "name": name, "input": inp}


def transcript(path, answer="RIGHT", calls=(("Read", {"file_path": "data.txt"}),), handback=True, model="claude-opus-5-5"):
    """A transcript in the form Claude Code writes a subagent's: a user line, an attachment, assistant lines with
    usage repeated per content block, tool results, and the answer as a SubagentHandback call or a last text."""
    usage = {"input_tokens": 2, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 30}
    lines = [{"type": "user", "message": {"role": "user", "content": "prompt"}}, {"type": "attachment", "attachment": {}}]
    for name, inp in calls:
        lines.append({"type": "assistant", "message": {"model": model, "content": [call(name, inp)], "usage": usage}})
        lines.append({"type": "user", "message": {"content": [{"type": "tool_result", "content": "ok"}]}})
    last = dict(usage, output_tokens=500)
    if answer is not None:
        block = call("SubagentHandback", {"message": answer}) if handback else {"type": "text", "text": answer}
        lines.append({"type": "assistant", "message": {"model": model, "content": [block], "usage": last}})
    pathlib.Path(path).write_text("".join(json.dumps(l) + "\n" for l in lines))


def rows(lines):
    """{(task, variant): (outcome, path, tokens, note)} of the grade table."""
    out = {}
    for l in lines:
        c = [x.strip() for x in l.strip("|").split("|")]
        if l.startswith("| t") and len(c) == 6 and c[0] != "task":
            out[(c[0], c[1])] = tuple(c[2:])
    return out


class Prepare(unittest.TestCase):
    """Requirements: Ablation runner, Full skill out of reach in the cut variants (prepare)."""

    def test_budget_reached_on_the_real_set(self):
        with tempfile.TemporaryDirectory() as d:
            run = pathlib.Path(d) / "run"
            p = subprocess.run([sys.executable, str(STAND), "prepare", "evidence-research", "--budget", "4", "--out",
                                str(run)], capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=REPO)
            self.assertEqual(p.returncode, 3, p.stderr)
            self.assertIn("budget reached: 2 of 6 calls not made", p.stdout)
            self.assertEqual(len(list(run.glob("*.prompt.md"))), 4)
            self.assertEqual(sorted(x["id"] for x in json.loads((run / "manifest.json").read_text())["prompts"]),
                             ["er-alive-cut", "er-alive-full", "er-alive-none", "er-hosting-full"])

    def test_repeated_prepare_gets_its_own_folder(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(pathlib.Path(d) / "repo")
            first = pathlib.Path(sa.prepare("widget", 6, root=root)[1][0].split(": ", 1)[1])
            second = pathlib.Path(sa.prepare("widget", 6, root=root)[1][0].split(": ", 1)[1])
            try:
                self.assertNotEqual(first, second)
                self.assertEqual(len(list(first.glob("*.prompt.md"))), 6)
                self.assertTrue(str(first.name).startswith("skill-ablation-widget-"))
            finally:
                for p in (first, second):
                    shutil.rmtree(p)

    def test_variant_texts_and_the_ban(self):
        with tempfile.TemporaryDirectory() as d:
            root, run = fixture(pathlib.Path(d) / "repo"), pathlib.Path(d) / "run"
            code, lines = sa.prepare("widget", 6, str(run), root)
            self.assertEqual(code, 0)
            text = {v: (run / ("t1-%s.prompt.md" % v)).read_text() for v in ("full", "cut", "none")}
            for v, t in text.items():
                self.assertIn("Do not load the skill `widget`: no `Skill` call for it and no read of any `skills/widget/` "
                              "file", t, v)
                self.assertIn("Do not read `tests/stands/skill-ablation/`", t, v)
                self.assertIn("Solve task t1 and say RIGHT.", t, v)
                self.assertIn("Work only in the folder `%s`" % (run.resolve() / ("t1-" + v)), t, v)
                self.assertTrue((run / ("t1-" + v) / "data.txt").is_file())
            self.assertIn(METHOD, text["full"])
            self.assertIn(GATE, text["full"])
            self.assertNotIn(METHOD, text["cut"])
            self.assertIn(GATE, text["cut"])
            self.assertNotIn(GATE, text["none"])
            self.assertIn("description: Ablation: widget cut t1 run", "\n".join(lines))

    def test_no_cut_variant_without_method_steps(self):
        with tempfile.TemporaryDirectory() as d:
            root, run = fixture(pathlib.Path(d) / "repo", method=False), pathlib.Path(d) / "run"
            code, lines = sa.prepare("widget", 6, str(run), root)
            self.assertEqual(code, 0)
            self.assertEqual(sorted(p.name for p in run.glob("*.prompt.md")),
                             ["t1-full.prompt.md", "t1-none.prompt.md", "t2-full.prompt.md", "t2-none.prompt.md"])

    @settings(max_examples=40, deadline=None)
    @given(st.integers(1, 4), st.integers(0, 15), st.booleans())
    def test_ablation_runner_budget_property(self, n, budget, method):
        """Requirement: Ablation runner: at most the budget, the not-made count, exit 3 only below the total, the ban
        in every prompt; budget 0 and budget equal to the total are reached by the ranges."""
        with tempfile.TemporaryDirectory() as d:
            root = fixture(pathlib.Path(d) / "repo", tasks=["t%d" % i for i in range(n)], method=method)
            run = pathlib.Path(d) / "run"
            code, lines = sa.prepare("widget", budget, str(run), root)
            total = n * (3 if method else 2)
            prompts = list(run.glob("*.prompt.md"))
            self.assertEqual(len(prompts), min(budget, total))
            short = budget < total
            self.assertEqual(code, 3 if short else 0)
            want = ["budget reached: %d of %d calls not made" % (total - budget, total)] if short else []
            self.assertEqual([l for l in lines if l.startswith("budget reached")], want)
            for p in prompts:
                self.assertIn("Do not load the skill `widget`", p.read_text())


class Grade(unittest.TestCase):
    """Requirements: Ablation grade, Grade outcomes, Full skill out of reach in the cut variants (grade)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = fixture(pathlib.Path(self.tmp.name) / "repo")
        self.run = pathlib.Path(self.tmp.name) / "run"
        sa.prepare("widget", 6, str(self.run), self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def grade(self, src=None):
        code, lines = sa.grade(self.run, src, self.root)
        self.assertEqual(code, 0, lines)
        return rows(lines), lines

    def test_outcomes(self):
        t = self.run
        transcript(t / "t1-full.jsonl")
        transcript(t / "t1-cut.jsonl", answer="wrong")
        transcript(t / "t1-none.jsonl", calls=())
        transcript(t / "t2-full.jsonl", handback=False)
        transcript(t / "t2-cut.jsonl", calls=(("Skill", {"skill": "widget"}),))
        got, lines = self.grade()
        self.assertEqual(got[("t1", "full")], ("pass", "1 of 1", "1602", ""))
        self.assertEqual(got[("t1", "cut")][0], "fail", "the check fails")
        self.assertEqual(got[("t1", "none")][:2], ("fail", "0 of 1"), "the path misses a required call")
        self.assertEqual(got[("t2", "full")][0], "pass", "the last assistant text is the answer")
        self.assertEqual(got[("t2", "cut")][0], "leaked", "a leaked row whose check passes is leaked, not pass")
        self.assertEqual(got[("t2", "none")][0], "not run")
        self.assertIn("models: claude-opus-5-5", lines)
        self.assertIn("compare: full 1 of 1, cut 0 of 1, none 0 of 1", lines)
        self.assertIn("not run: 1; leaked: 1; unreadable: 0; not made: 0", lines)
        self.assertEqual((t / "t1-full.answer.md").read_text(), "RIGHT")

    def test_leaks(self):
        for pid, inp in (("t1-full", {"skill": "x:widget"}), ):
            transcript(self.run / (pid + ".jsonl"), calls=(("Read", {"file_path": "data.txt"}), ("Skill", inp)))
        transcript(self.run / "t1-cut.jsonl", calls=(("Read", {"file_path": os.path.expanduser("~/.claude/skills/widget/SKILL.md")}),
                                                     ("Read", {"file_path": "data.txt"})))
        transcript(self.run / "t1-none.jsonl", calls=(("Bash", {"command": "cat tests/stands/skill-ablation/widget/t1/check.py data.txt"}),))
        transcript(self.run / "t2-full.jsonl", calls=(("Skill", {"skill": "other"}), ("Read", {"file_path": "data.txt"})))
        got, lines = self.grade()
        self.assertEqual([got[("t1", v)][0] for v in ("full", "cut", "none")], ["leaked"] * 3)
        self.assertEqual(got[("t2", "full")][0], "pass", "another skill is no leak")
        self.assertIn("compare: full 0 of 0, cut 0 of 0, none 0 of 0", lines)

    def test_missing_transcript_and_answer(self):
        transcript(self.run / "t1-full.jsonl", answer=None)
        transcript(self.run / "t1-cut.jsonl", answer="   ")
        got, lines = self.grade()
        self.assertEqual({got[("t1", v)][0] for v in ("full", "cut", "none")}, {"not run"})
        self.assertIn("not run: 6; leaked: 0; unreadable: 0; not made: 0", lines)

    def test_from_a_subagents_folder(self):
        src = pathlib.Path(self.tmp.name) / "subagents"
        src.mkdir()
        manifest = json.loads((self.run / "manifest.json").read_text())
        for i, p in enumerate(manifest["prompts"]):
            transcript(src / ("agent-a%d.jsonl" % i))
            (src / ("agent-a%d.meta.json" % i)).write_text(json.dumps({"description": p["description"]}))
        transcript(src / "agent-zz.jsonl", answer="wrong")
        (src / "agent-zz.meta.json").write_text(json.dumps({"description": "Ablation: widget full t1 other-run"}))
        got, lines = self.grade(src)
        self.assertEqual({o[0] for o in got.values()}, {"pass"})
        self.assertIn("compare: full 2 of 2, cut 2 of 2, none 2 of 2", lines)
        self.assertTrue((self.run / "t2-none.jsonl").is_file())

    def test_no_cut_variant_and_budget(self):
        root = fixture(pathlib.Path(self.tmp.name) / "repo2", method=False)
        run = pathlib.Path(self.tmp.name) / "run2"
        self.assertEqual(sa.prepare("widget", 3, str(run), root)[0], 3)
        for pid in ("t1-full", "t1-none", "t2-full"):
            transcript(run / (pid + ".jsonl"))
        code, lines = sa.grade(run, None, root)
        self.assertIn("compare: full 1 of 1, cut - of 1, none 1 of 1", lines, "t2 lost its none call to the budget")
        self.assertIn("not run: 0; leaked: 0; unreadable: 0; not made: 1", lines)


class Hostile(unittest.TestCase):
    """Requirement: Runner input refused, and the broken input of Grade outcomes."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = pathlib.Path(self.tmp.name)
        self.root = fixture(self.d / "repo", extra=("ship",))

    def tearDown(self):
        self.tmp.cleanup()

    def test_refused_skill_names(self):
        for name in ("../x", "/etc", "nope", "ship", "../widget"):
            out = self.d / ("out-" + str(abs(hash(name))))
            code, lines = sa.prepare(name, 6, str(out), self.root)
            self.assertEqual(code, 2, name)
            self.assertIn(name, lines[0])
            self.assertFalse(out.exists(), name)

    def test_refused_skill_name_on_the_command_line(self):
        out = self.d / "cli-out"
        p = subprocess.run([sys.executable, str(STAND), "prepare", "../x", "--budget", "6", "--out", str(out)],
                           capture_output=True, text=True, stdin=subprocess.DEVNULL, cwd=REPO)
        self.assertEqual((p.returncode, p.stdout.strip()), (2, "refused: ../x is not a skill of targets.json"))
        self.assertFalse(out.exists())

    def test_non_empty_out(self):
        out = self.d / "full"
        out.mkdir()
        (out / "keep.txt").write_text("mine")
        self.assertEqual(sa.prepare("widget", 6, str(out), self.root)[0], 2)
        self.assertEqual(os.listdir(out), ["keep.txt"])

    def manifest(self, edit):
        run = self.d / "run"
        sa.prepare("widget", 6, str(run), self.root)
        m = json.loads((run / "manifest.json").read_text())
        edit(m)
        (run / "manifest.json").write_text(json.dumps(m))
        return sa.grade(run, None, self.root)

    def test_refused_manifests(self):
        def bad_id(m):
            m["prompts"][0]["id"] = "../x"

        def bad_variant(m):
            m["prompts"][0]["variant"] = "evil"

        def bad_task(m):
            m["tasks"].append("../x")
        for edit in (bad_id, bad_variant, bad_task):
            code, lines = self.manifest(edit)
            self.assertEqual(code, 2, edit.__name__)
            self.assertIn("has no manifest prepare writes", lines[0])
        (self.d / "run" / "manifest.json").write_text("{broken")
        self.assertEqual(sa.grade(self.d / "run", None, self.root)[0], 2)

    def test_broken_transcripts(self):
        run = self.d / "run"
        sa.prepare("widget", 6, str(run), self.root)
        transcript(run / "t1-full.jsonl")
        with (run / "t1-full.jsonl").open("a") as f:
            f.write("{not json\n")
        transcript(run / "t1-cut.jsonl")
        text = (run / "t1-cut.jsonl").read_text()
        (run / "t1-cut.jsonl").write_text(text[:-40])
        transcript(run / "t1-none.jsonl")
        for pid in ("t2-full", "t2-cut"):
            transcript(run / (pid + ".jsonl"))
        transcript(run / "t2-none.jsonl", answer="RIGHT" + "x" * 200)
        old = sa.LIMIT
        sa.LIMIT = (run / "t2-none.jsonl").stat().st_size - 1
        try:
            code, lines = sa.grade(run, None, self.root)
        finally:
            sa.LIMIT = old
        got = rows(lines)
        self.assertEqual(got[("t1", "full")], ("unreadable", "-", "-", "line 6 is not JSON"))
        self.assertEqual(got[("t1", "cut")][0], "unreadable")
        self.assertEqual(got[("t2", "none")][0], "unreadable")
        self.assertIn("compare: full 0 of 0, cut 0 of 0, none 0 of 0", lines)
        self.assertIn("not run: 0; leaked: 0; unreadable: 3; not made: 0", lines)

    def test_from_folder_input(self):
        run, src = self.d / "run", self.d / "subagents"
        sa.prepare("widget", 6, str(run), self.root)
        src.mkdir()
        desc = {p["id"]: p["description"] for p in json.loads((run / "manifest.json").read_text())["prompts"]}
        for name in ("a1", "a2"):
            transcript(src / ("agent-%s.jsonl" % name))
            (src / ("agent-%s.meta.json" % name)).write_text(json.dumps({"description": desc["t1-full"]}))
        transcript(src / "agent-b.jsonl")
        (src / "agent-b.meta.json").write_text("{broken")
        transcript(src / "agent-c.jsonl")
        transcript(self.d / "outside.jsonl")
        os.symlink(self.d / "outside.jsonl", src / "agent-d.jsonl")
        (src / "agent-d.meta.json").write_text(json.dumps({"description": desc["t1-none"]}))
        (src / "agent-c.meta.json").write_text(json.dumps({"other": desc["t1-cut"]}))
        code, lines = sa.grade(run, src, self.root)
        got = rows(lines)
        self.assertEqual(got[("t1", "full")], ("unreadable", "-", "-", "2 transcripts for one description"))
        self.assertEqual(got[("t1", "cut")][0], "not run", "a meta.json without a description is skipped")
        self.assertEqual(got[("t1", "none")][0], "not run", "a link is skipped")
        self.assertFalse((run / "t1-none.jsonl").exists())

    def test_answer_is_read_as_a_file(self):
        run = self.d / "run"
        sa.prepare("widget", 6, str(run), self.root)
        marker = self.d / "PWNED"
        answer = "RIGHT $(touch %s) `touch %s`; touch %s | sh" % (marker, marker, marker)
        transcript(run / "t1-full.jsonl", answer=answer)
        got = rows(sa.grade(run, None, self.root)[1])
        self.assertEqual(got[("t1", "full")][0], "pass")
        self.assertFalse(marker.exists())
        self.assertEqual((run / "t1-full.answer.md").read_text(), answer)


class TaskSets(unittest.TestCase):
    """Requirement: Task sets: every committed reference grades `pass`, every check refuses an empty answer."""

    def test_the_sets(self):
        self.assertEqual(sa.task_errors(), [])
        names = sorted("%s/%s" % (p.parent.parent.name, p.parent.name)
                       for p in (REPO / "tests/stands/skill-ablation").glob("*/*/prompt.md"))
        self.assertEqual(names, ["debug-profile/dp-code", "debug-profile/dp-service", "evidence-research/er-alive",
                                 "evidence-research/er-hosting"])

    def test_a_check_that_passes_an_empty_answer(self):
        with tempfile.TemporaryDirectory() as d:
            root = fixture(d, tasks=("t1",))
            task = root / "tests/stands/skill-ablation/widget/t1"
            transcript(task / "reference.jsonl")
            self.assertEqual(sa.task_errors(root), [])
            (task / "check.py").write_text("import sys\nsys.exit(0)\n")
            self.assertEqual(sa.task_errors(root), ["task set widget/t1: check.py passes an empty answer"])
            (task / "check.py").write_text(CHECK)
            transcript(task / "reference.jsonl", calls=())
            self.assertEqual(sa.task_errors(root), ["task set widget/t1: reference.jsonl grades fail"])
            (task / "required.txt").unlink()
            self.assertEqual(sa.task_errors(root), ["task set widget/t1: no required.txt"])


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
