#!/usr/bin/env python3
"""Stand of the change practitioner-techniques: work in a field no spec, lesson or skill covers (money rounding).

  prepare                 copy `examples/demo` into a fresh `/tmp/practitioner-techniques.*` git project
                          (`process.analyze: off`, `process.light-path: off`, the `tip` spec and the demo's changes
                          removed) and write the prompts `check.md` and `plan.md` next to it; prints `copy:`, `check:`
                          and `plan:`
  clean <copy>            remove a copy `prepare` made
  --grade <answer>        `list with sources` and `ran named` of a check answer
  --grade-plan <answer>   `list in proposal` (in its What Changes) and `task per item` of a plan answer: `=== <path>` blocks of the files
                          the plan creates

A line is matched with `*` and backquotes stripped, a leading list, quote or heading marker removed, whitespace
collapsed and case folded. A list is the line starting `Practitioner checks:` and its items: the text after the label
split at `;`, or the list lines right under it. An item has a source when it holds an `http(s)://` link or a named
standard (two or more capital letters and a number: `ISO 4217`, `IEEE 754`). An item is named in a text when one of its
words of five or more letters before the source (four, when it has none), other than a few generic words, occurs in
that text. A missing block,
an unreadable file and a wrong argument exit 1. The answers come from Claude Code subagents of the lead session, never
`claude -p`."""
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[2]
PREFIX = "practitioner-techniques."
SOURCE = re.compile(r"https?://\S+|\b[A-Z][A-Z0-9]+(?:/[A-Z]+)?[ -]?\d{2,}")
LIST = re.compile(r"\s*(?:[-*+]|\d+[.)])\s")
GENERIC = {"check", "checks", "correct", "correctly", "should", "before", "instead", "practitioner", "source",
           "standard", "values", "always", "money", "every", "their", "which", "where", "about"}
GIT = ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.com", "-c", "init.defaultBranch=main",
       "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]
sys.path.insert(0, str(REPO / "tests"))
import skill_text  # noqa: E402

_spec = importlib.util.spec_from_file_location("goal_first", REPO / "tests/stands/goal-first.py")
_gf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gf)
norm, blocks = _gf.norm, _gf.blocks

BOUND = ("Your project folder is `%s`; the session has no added working folders: read nothing outside it but the paths "
         "this prompt names. This session cannot write or edit files. The global rules of this computer:\n\n%s")
CHECK = ("The user's message: check that the tip calculator rounds money correctly\n\nYou may read the code and run "
         "commands that change no file, such as `python3 tip.py 10.10 15`. Your whole answer is your report to the user.")
PLAN = ("The user runs the skill `spec-plan`; follow its text below, not an installed copy.\n\n%s\n\nThe user's "
        "message: make the tip calculator round money the way a bookkeeper does\n\nRun every step that reads. `solo-sdd "
        "new` lays out the templates of `%s`: instead of running it and writing a file, start each file from its "
        "template and return each file the plan would create as a line `=== <path from the project root>` followed "
        "by the file's full text; skip the plan commit of step 9. End with a line `=== report` followed by the plan "
        "report.")


def fail(msg):
    sys.exit("practitioner-techniques: " + msg)


def git(cwd, *args):
    subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True, stdin=subprocess.DEVNULL, timeout=60)


def prepare():
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=PREFIX, dir="/tmp"))
    try:
        copy = tmp / "demo"
        shutil.copytree(REPO / "examples/demo", copy)
        shutil.rmtree(copy / "solo-sdd/specs/tip")
        for path in (copy / "solo-sdd/changes").iterdir():
            shutil.rmtree(path)
        (copy / "solo-sdd/changes/archive").mkdir()
        with open(copy / "solo-sdd/config", "a", encoding="utf-8") as f:
            f.write("process.analyze: off\nprocess.light-path: off\n")
        git(copy, "init", "-q")
        git(copy, "add", "-A")
        git(copy, "commit", "-q", "-m", "demo")
        rules = (REPO / "global/AGENTS.md").read_text(encoding="utf-8")
        (tmp / "check.md").write_text(BOUND % (copy, rules) + "\n\n" + CHECK + "\n", encoding="utf-8")
        (tmp / "plan.md").write_text(BOUND % (copy, rules) + "\n\n" + PLAN % (
            skill_text.skill("spec-plan"), REPO / "templates/solo-sdd/change") + "\n", encoding="utf-8")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print("copy: %s" % copy)
    print("check: %s" % (tmp / "check.md"))
    print("plan: %s" % (tmp / "plan.md"))


def clean(copy):
    tmp = pathlib.Path(copy).resolve().parent
    if not (tmp.name.startswith(PREFIX) and (tmp / "check.md").is_file() and tmp.parent == pathlib.Path("/tmp").resolve()):
        fail("%s is not a copy prepare made" % copy)
    shutil.rmtree(tmp)
    print("removed %s" % tmp)


def raw(line):
    return line.replace("*", "").replace("`", "").strip()


def labelled(lines, label):
    """The items of the first `<label>` line: its text after the label split at `;`, or the list lines right under it."""
    for i, line in enumerate(lines):
        flat = raw(re.sub(r"^\s*(?:>\s*|#+\s+|(?:[-+*]|\d+[.)])\s+)*", "", line))
        if not flat.casefold().startswith(label):
            continue
        rest = flat[len(label):].strip()
        if rest:
            return [s.strip() for s in rest.split(";") if s.strip()]
        items = []
        for nxt in lines[i + 1:]:
            if not nxt.strip() and not items:
                continue
            if not LIST.match(nxt):
                break
            items.append(raw(LIST.sub("", nxt, 1)))
        return items
    return []


def section(lines, header):
    """The lines of the `## <header>` section."""
    out, inside = [], False
    for line in lines:
        if line.startswith("## "):
            inside = line[3:].strip().casefold() == header
        elif inside:
            out.append(line)
    return out


def words(item):
    m = SOURCE.search(item)
    head = (item[:m.start()] if m else item).casefold()
    return ([w for w in re.findall(r"[a-z]{5,}", head) if w not in GENERIC]
            or [w for w in re.findall(r"[a-z]{4,}", head) if w not in GENERIC])


def is_named(item, text):
    return any(w in text for w in words(item))


def sourced(items):
    return len(items) >= 3 and all(SOURCE.search(i) for i in items)


yes = lambda ok: "yes" if ok else "no"


def grade(text):
    lines = text.splitlines()
    items = labelled(lines, "practitioner checks:")
    ran = norm(" ".join(labelled(lines, "practitioner checks run:")))
    print("list with sources: %s" % yes(sourced(items)))
    print("ran named: %s" % yes(bool(ran) and any(is_named(i, ran) for i in items)))


def grade_plan(text):
    found = blocks(text)
    pick = lambda suffix: [lines for name, lines in found.items() if name.casefold().endswith(suffix)]
    proposals, tasks, checks = pick("proposal.md"), pick("tasks.md"), pick("verification.md")
    if not proposals:
        fail("the answer has no `=== <path ending in proposal.md>` block")
    items = [i for lines in proposals for i in labelled(section(lines, "what changes"), "practitioner checks:")]
    live = [line for lines in checks for line in section(lines, "live scenario")]
    target = norm(" ".join(l for lines in tasks for l in lines) + " " + " ".join(live))
    print("list in proposal: %s" % yes(sourced(items)))
    print("task per item: %s" % yes(bool(items) and all(is_named(i, target) for i in items)))


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["prepare"]:
        prepare()
    elif len(args) == 2 and args[0] == "clean":
        clean(args[1])
    elif len(args) == 2 and args[0] in ("--grade", "--grade-plan"):
        try:
            text = pathlib.Path(args[1]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            fail("cannot read %s: %s" % (args[1], e))
        (grade if args[0] == "--grade" else grade_plan)(text)
    else:
        fail("usage: practitioner-techniques.py prepare | clean <copy> | --grade <answer> | --grade-plan <answer>")
