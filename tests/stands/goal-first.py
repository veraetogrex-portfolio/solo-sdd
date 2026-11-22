#!/usr/bin/env python3
"""Stand of the change goal-first: a request of steps without a goal, planned by `spec-plan` and done outside it.

  prepare                  copy `examples/demo` into a fresh `/tmp/goal-first.*` git project (`process.analyze: off`,
                           `process.light-path: off`, `test_usual_bill` slowed by 2 s), a second copy `renamed` with
                           both tests renamed and committed, and the prompts `plan.md` (on the copy) and `outside.md`
                           (on `renamed`) next to them; prints `copy:`, `plan:`, `renamed:` and `outside:`
  clean <copy>             remove a copy `prepare` made
  --grade <answer>         the five lines of a plan answer (the last: the `Proposals:` item of `test_not_a_number`
                           says `moves the check: no`, or `n/a` when the check names no time): `=== <path>` blocks of the files the plan creates, then
                           `=== report` and the plan report
  --grade-report <report>  `goal first`: the report (the whole answer, or its `=== report` block when it has one)
                           opens with the `Goal:` and `Check:` lines, both `(inferred)`

A line is matched with `*` and backquotes stripped, a leading list, quote or heading marker removed, whitespace
collapsed and case folded. A missing block, an unreadable file and a wrong argument exit 1. The answers come from
Claude Code subagents of the lead session, never `claude -p`."""
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PREFIX = "goal-first."
RENAMED = ("test_tip_and_total_of_a_usual_bill", "test_refuses_a_bill_or_percent_that_is_not_a_number")
TIME = re.compile(r"\d\s*(?:ms|s|secs?|seconds?|mins?|minutes?)\b")
GIT = ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.com", "-c", "init.defaultBranch=main",
       "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]
sys.path.insert(0, str(REPO / "tests"))
import skill_text  # noqa: E402

BOUND = ("Your project folder is `%s`; the session has no added working folders: read nothing outside it but the paths this prompt names. This "
         "session cannot write or edit files. The global rules of this computer:\n\n%s")
PLAN = ("The user runs the skill `spec-plan`; follow its text below, not an installed copy.\n\n%s\n\nThe user's "
        "message: remove the tests test_usual_bill and test_not_a_number\n\nRun every step that reads. `solo-sdd "
        "new` lays out the templates of `%s`: instead of running it and writing a file, start each file from its "
        "template and return each file the plan would create as a line `=== <path from the project root>` followed "
        "by the file's full text; skip the plan commit of step 9. End with a line `=== report` followed by the plan "
        "report.")
OUTSIDE = ("The user's message: rename the tests test_usual_bill and test_not_a_number\n\nEarlier in this session "
           "you did the work: in `tests/test_tip.py` `test_usual_bill` is now `test_tip_and_total_of_a_usual_bill` and "
           "`test_not_a_number` is now `test_refuses_a_bill_or_percent_that_is_not_a_number`, and `python3 -m "
           "unittest discover -s tests` printed `Ran 4 tests` and `OK`. Your whole answer is your report to the user "
           "about this work.")


def fail(msg):
    sys.exit("goal-first: " + msg)


def git(cwd, *args):
    subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)


def prepare():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=PREFIX, dir="/tmp"))
    try:
        copy = tmp / "demo"
        shutil.copytree(REPO / "examples/demo", copy)
        test = copy / "tests/test_tip.py"
        text = test.read_text(encoding="utf-8")
        text = text.replace("import sys\n", "import sys\nimport time\n", 1).replace(
            "    def test_usual_bill(self):\n", "    def test_usual_bill(self):\n        time.sleep(2)\n", 1)
        test.write_text(text, encoding="utf-8")
        with open(copy / "solo-sdd/config", "a", encoding="utf-8") as f:
            f.write("process.analyze: off\nprocess.light-path: off\n")
        git(copy, "init", "-q")
        git(copy, "add", "-A")
        git(copy, "commit", "-q", "-m", "demo")
        renamed = tmp / "renamed"
        shutil.copytree(copy, renamed)
        test = renamed / "tests/test_tip.py"
        test.write_text(test.read_text(encoding="utf-8").replace("test_usual_bill", RENAMED[0]).replace(
            "test_not_a_number", RENAMED[1]), encoding="utf-8")
        git(renamed, "commit", "-q", "-am", "rename the tests")
        rules = (REPO / "global/AGENTS.md").read_text(encoding="utf-8")
        (tmp / "plan.md").write_text(BOUND % (copy, rules) + "\n\n" + PLAN % (
            skill_text.skill("spec-plan"), REPO / "templates/solo-sdd/change") + "\n", encoding="utf-8")
        (tmp / "outside.md").write_text(BOUND % (renamed, rules) + "\n\n" + OUTSIDE + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print("copy: %s" % copy)
    print("plan: %s" % (tmp / "plan.md"))
    print("renamed: %s" % renamed)
    print("outside: %s" % (tmp / "outside.md"))


def clean(copy):
    tmp = pathlib.Path(copy).resolve().parent
    if not (tmp.name.startswith(PREFIX) and (tmp / "plan.md").is_file() and tmp.parent == pathlib.Path("/tmp").resolve()):
        fail("%s is not a copy prepare made" % copy)
    shutil.rmtree(tmp)
    print("removed %s" % tmp)


def norm(line):
    line = re.sub(r"^\s*(?:>\s*|#+\s+|(?:[-+*]|\d+[.)])\s+(?:\[[ x]\]\s+)?)*", "", line.replace("*", "").replace("`", ""))
    return " ".join(line.split()).casefold()


def blocks(text):
    """{name: lines} of the `=== <name>` blocks of an answer."""
    out, cur = {}, None
    for line in text.splitlines():
        m = re.fullmatch(r"\s*[*`]*===\s*(.+?)\s*[*`]*\s*", line)
        if m:
            cur = out.setdefault(m.group(1).strip("`* "), [])
        elif cur is not None:
            cur.append(line)
    return out


def block(found, suffix):
    names = [n for n in found if n.casefold() == suffix or n.casefold().endswith("/" + suffix)]
    if not names:
        fail("the answer has no `=== <path ending in %s>` block" % suffix)
    return found[names[0]]


def section(lines, header):
    """The non-empty lines of a `## <header>` section, normalised."""
    out, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip().casefold() == header.casefold()
        elif inside and line.strip():
            out.append(norm(line))
    return out


def proposal_items(lines):
    """The items of the report's `Proposals:` line: its text after the label and the list lines right under it, split
    at `;`, each normalised."""
    out, inside = [], False
    for line in lines:
        flat = norm(line)
        if flat.startswith("proposals:"):
            inside, text = True, flat[len("proposals:"):]
        elif inside and re.match(r"\s*(?:[-*+]|\d+[.)]|\([a-z]\))\s", line):
            text = flat
        else:
            inside = False
            continue
        out += [s.strip() for s in text.split(";") if s.strip()]
    return out


def grade(text):
    found = blocks(text)
    why = section(block(found, "proposal.md"), "Why")
    goal, check = (why[-2:] + ["", ""])[:2] if len(why) >= 2 else ("", "")
    has_goal = goal.startswith("goal:") and check.startswith("check:")
    decisions = section(block(found, "verification.md"), "Decisions Without Owner")
    tasks = [l for l in block(found, "tasks.md") if re.match(r"\s*- \[ \]", l)]
    report = block(found, "report")
    timed = has_goal and TIME.search(check)
    proposals = any("test_not_a_number" in item and "moves the check: no" in item for item in proposal_items(report))
    yes = lambda ok: "yes" if ok else "no"
    print("goal in Why: %s" % yes(has_goal))
    print("check with a number: %s" % yes(has_goal and re.search(r"\d", check)))
    print("inferred marked: %s" % yes(has_goal and "(inferred)" in goal and "(inferred)" in check
                                      and any("goal inferred:" in l for l in decisions)))
    print("both steps have tasks: %s" % yes(all(any(n in l for l in tasks) for n in ("test_usual_bill",
                                                                                     "test_not_a_number"))))
    print("fast test does not move the check: %s" % (yes(proposals) if timed else "n/a (the check names no time)"))


def grade_report(text):
    found = blocks(text)
    lines = [norm(l) for l in (found["report"] if "report" in found else text.splitlines()) if l.strip()]
    first = (lines + ["", ""])[:2]
    ok = first[0].startswith("goal:") and first[1].startswith("check:") and all("(inferred)" in l for l in first)
    print("goal first: %s" % ("yes" if ok else "no"))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["prepare"]:
        prepare()
    elif len(args) == 2 and args[0] == "clean":
        clean(args[1])
    elif len(args) == 2 and args[0] in ("--grade", "--grade-report"):
        try:
            text = pathlib.Path(args[1]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            fail("cannot read %s: %s" % (args[1], e))
        (grade if args[0] == "--grade" else grade_report)(text)
    else:
        fail("usage: goal-first.py prepare | clean <copy> | --grade <answer> | --grade-report <report>")
