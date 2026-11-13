"""`solo-sdd check --change <id>`: the Integrations line of a point in the ## Result section of the change's
verification.md, written by the CLI, and a change refused before any run.

The CLI tests work on a temporary git project and a temporary home with the fictional marker-check of
tests/test_integration_run.py; the property test runs put_line, the function the CLI writes the line with."""
import os
import re
import sys
import unittest

from hypothesis import given, settings as hsettings, strategies as st

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from solo_sdd import integration_run as R, process_format as pf  # noqa: E402
from test_integration_run import Project, git, read, write  # noqa: E402

VERIFICATION = ("## Live Scenario\n\nrun it\n\n## Needs\n\nnone\n\n## Fallback\n\nnot needed.\n\n## Result\n\n"
                "<!-- Filled during apply -->\n\n2026-11-12: the stand passed.\nSuite: n/a -> 10\n\n"
                "## Not Verified\n\nnothing\n")
LINE = re.compile(r"^Integrations (checks|ship) \(tree ([0-9a-f]+|x)\): ", re.M)


def result_section(text):
    """The visible lines of the first ## Result section outside code blocks, read by the doc reader."""
    lines = R.pf.read_doc(type("T", (), {"read_text": lambda self, encoding=None: text})())
    mask = pf.fence_mask(lines)
    found = [code_free for name, _, code_free in pf.sections(lines, mask) if name == "Result"]
    return found[0] if found else None


class ResultLineWrittenByTheCLI(Project):
    """Requirement: Result line written by the CLI."""

    def setUp(self):
        super().setUp()
        self.integration("applies: *.py\nmode: gate\n")
        self.config("integrations: marker-check\n")
        self.vpath = os.path.join(self.root, "solo-sdd", "changes", "marker-demo", "verification.md")
        write(self.vpath, VERIFICATION)
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "change")

    def lines(self):
        return LINE.findall(read(self.vpath).decode())

    def run_on(self, *args):
        """(code, output, the tree the run saw); afterwards the point is recorded for the tree the line left."""
        tree = R.tree_hash(self.root)
        code, out = self.check("--point", "checks", *args, "--change", "marker-demo")
        points = R.read_json(os.path.join(R.repo_dir(self.root, self.home), R.tree_hash(self.root) + ".json"))["points"]
        self.assertIn("checks", points, "recorded under the tree after the line")
        return code, out, tree

    def test_result_line_written_by_the_cli_a_second_run_replaces_the_line(self):
        write(os.path.join(self.root, "app.py"), "x = 1\n")
        code, out, first = self.run_on("--changed")
        self.assertEqual((code, self.lines()), (0, [("checks", first)]), out)
        self.assertIn("Integrations checks (tree %s): marker-check PASS\n" % first, read(self.vpath).decode())
        for _ in range(2):
            code, out, tree = self.run_on("--changed")
            self.assertEqual((code, self.lines()), (0, [("checks", tree)]), out)
        self.assertIn("reused %s" % tree, out, "a run on the tree the line left reuses the record")
        write(os.path.join(self.root, "app.py"), "x = 2\n")
        code, out, second = self.run_on("--changed")
        self.assertNotEqual(first, second)
        self.assertEqual((code, self.lines()), (0, [("checks", second)]), out)
        kept = [ln for ln in read(self.vpath).decode().split("\n") if not ln.startswith("Integrations ")]
        self.assertEqual(kept, VERIFICATION.split("\n"), "the other lines are unchanged")
        write(os.path.join(self.root, "app.py"), "FORBIDDEN\n")
        code, out, third = self.run_on()
        self.assertEqual((code, self.lines()), (1, [("checks", third)]), out)
        self.assertIn("): marker-check FAIL\n", read(self.vpath).decode())

    def test_result_line_written_by_the_cli_an_unknown_change(self):
        write(os.path.join(self.root, "solo-sdd", "changes", "no-result", "verification.md"), "## Live Scenario\n\nx\n")
        write(os.path.join(self.root, "solo-sdd", "changes", "open-comment", "verification.md"),
              "## Result\n\n<!-- never closed\n")
        write(os.path.join(self.root, "solo-sdd", "changes", "archive", "verification.md"), VERIFICATION)
        write(os.path.join(self.root, "solo-sdd", "changes", "no-file", ".keep"), "")
        write(os.path.join(self.root, "solo-sdd", "changes", "latin1", "verification.md"), b"## Result\n\n\xe9\n")
        write(os.path.join(self.root, "app.py"), "x = 1\n")
        for name, why in (("no-such", "no change no-such"), ("archive", "no change archive"),
                          ("../marker-demo", "no change ../marker-demo"), ("marker-demo\n", "no change marker-demo\n"),
                          ("no-result", "no ## Result section"), ("no-file", "no such file"),
                          ("open-comment", "inside a comment"), ("latin1", "utf-8")):
            code, out = self.check("--point", "checks", "--changed", "--change", name)
            self.assertEqual(code, 1, (name, out))
            self.assertIn(why, out, name)
            self.assertEqual((self.starts(), self.tree_records()), (0, []), "no integration started for %r" % name)
        self.assertEqual(read(self.vpath).decode(), VERIFICATION)
        self.assertIsNone(R.run(["--point", "checks", "--change"], self.root, self.home), "--change without a name")


# The property: for any verification.md text and any sequence of runs of the two points, the Result section holds at
# most one line per point, the last one, and every other line keeps its bytes.
OTHER = st.text(alphabet="abc -#*:().", max_size=12).filter(lambda s: not s.startswith("#"))
BLOCK = st.one_of(
    OTHER,
    st.sampled_from(["<!-- Filled during apply -->", "<!-- a", "  ## Result inside -->", "```", "## Result", "~~~",
                     "Integrations checks (tree", "Integrations other (tree 1): x PASS", "Suite: n/a -> 12",
                     "`Integrations checks (tree 9): y PASS`"]),
)


@st.composite
def documents(draw):
    """(text, line break) of a verification.md: sections before and after ## Result, other lines, closed comments,
    closed code blocks holding Result-looking lines, at most one old Integrations line per point."""
    brk = draw(st.sampled_from(["\n", "\r\n"]))

    def lines():
        out = []
        for x in draw(st.lists(BLOCK, max_size=6)):
            out += {"<!-- a": ["<!-- a", "Integrations checks (tree 3): hidden PASS", "-->"],
                    "```": ["```", "## Result", "Integrations checks (tree 4): code PASS", "```"],
                    "~~~": ["~~~", "Integrations ship (tree 5): code PASS", "~~~"]}.get(x, [x])
        return out

    body = lines()
    for point in ("checks", "ship"):
        for n in range(draw(st.integers(0, 2))):  # two old lines of a point: a run keeps one
            body.insert(draw(st.integers(0, len(body))), "Integrations %s (tree %d): old PASS" % (point, n))
    doc = ["## Live Scenario", ""] + lines() + ["## Result", ""] + body
    if draw(st.booleans()):
        doc += ["", "## Not Verified", ""] + lines()
    return brk.join(doc) + brk, brk


RUNS = st.lists(st.tuples(st.sampled_from(["checks", "ship"]), st.text(alphabet="0123456789abcdef", min_size=1,
                                                                        max_size=4)), min_size=1, max_size=5)


def visible_lines(text):
    return [ln for ln in result_section(text) if LINE.match(ln)]


def others(text):
    """Every line with its break but the visible Integrations lines of the ## Result section."""
    segs, lines = R.LINE_BREAK.findall(text), R.pf.read_doc(type("T", (), {"read_text": lambda s, encoding=None: text})())
    mask = pf.fence_mask(lines)
    sec, out = None, []
    for i, seg in enumerate(segs):
        if not mask[i] and pf.H2.match(lines[i]):
            sec = pf.H2.match(lines[i]).group(1)
        if not (sec == "Result" and not mask[i] and LINE.match(lines[i])):
            out.append(seg)
    return out


class ResultLineProperty(unittest.TestCase):
    @hsettings(max_examples=300, deadline=None)
    @given(documents(), RUNS)
    def test_result_line_written_by_the_cli_one_line_per_point(self, doc, runs):
        text, _ = doc
        out, last = text, {}
        for point, tree in runs:
            line = "Integrations %s (tree %s): marker-check PASS" % (point, tree)
            out, last[point] = R.put_line(out, point, line), line
        untouched = [ln for ln in visible_lines(text) if LINE.match(ln).group(1) not in last]
        self.assertEqual(sorted(visible_lines(out)), sorted(untouched + list(last.values())))
        self.assertEqual(others(out), others(text))

    def test_result_line_written_by_the_cli_an_unclosed_block(self):
        for text in ("## Result\n\n<!-- open\n", "## Result\n\n```\ncode\n", "x\n## Results\n"):
            with self.assertRaises(ValueError, msg=text):
                R.put_line(text, "checks", "Integrations checks (tree 1): m PASS")
        with self.assertRaises(ValueError):
            R.put_line("## Result\nIntegrations checks (tree 1): m PASS <!-- c -->\n", "checks", "Integrations checks (tree 2): m PASS")


if __name__ == "__main__":
    sys.exit(0 if unittest.main(exit=False).result.wasSuccessful() else 1)
