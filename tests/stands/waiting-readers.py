#!/usr/bin/env python3
"""Stand of the change waiting-readers: grade subagent runs of `context-resume`, `blockers` and `project-init` on a copy
of the `next-up` fixture whose `docs/waiting.md` has a `## Closed` table.

  prepare                       copy `next-up/project` into a fresh `waiting-readers.*` temporary folder as a git
                                repository: `docs/waiting.md` gets `## Closed` holding the `publish-docs` row and a
                                `DESIGN.md` row in the first table, `DESIGN.md` has every field filled next to
                                `web/index.html`, the `WAITING`
                                file of `publish-docs` is removed (the owner did it); writes one prompt per skill;
                                prints `copy:` and `prompt <skill>:`
  clean <folder>                remove a folder `prepare` made, refuse any other
  --grade <context-resume answer> <blockers answer> <project-init answer>
                                print the check lines and the summary `waiting readers: <n> of 6 checks pass`
  --grade-confined <transcript>...  `grading out of reach: yes` when no tool input of a run names
                                `tests/stands/waiting-readers` or `tests/stands/next-up`

The `context-resume` answer is its map; the other two hold `=== docs/waiting.md` with the whole new file and may hold
other `=== <path>` blocks and `=== report`. The answers come from Claude Code subagents of the lead session, never
`claude -p`. A missing or unreadable file and a wrong argument exit 1."""
import datetime
import importlib.util
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("next_up_stand", HERE / "next-up.py")
nu = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nu)
nu.fail = lambda msg: sys.exit("waiting-readers: " + msg)  # the refusals of the reused readers
nu.NEAR = re.compile(r"tests/stands/(?:waiting-readers|next-up)(?![A-Za-z0-9_-])")  # the graders and references
PREFIX = "waiting-readers."
DESIGN_ROW = "| — | — | DESIGN.md: fill in the fields Fonts, Dial | owner | 2026-11-05 |"
# every waiting row by its change id or its condition, and the closed row the same way
WAITING = (("dispatch-ci", "red ci"), ("add-import", "csv"), ("release-040", "v0.4.0"), ("design.md",))
CLOSED = ("publish-docs", "v0.3.0")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
DESIGN = """# DESIGN

Filled in by the user, the agent only carries over the answers. An empty field means not decided.

Character: calm, strict
Audience: shop owners
Palette (2-3 main colours and one accent): graphite, paper white; accent orange
Fonts: Inter
Mood: focused
Themes: light
Dial: ENERGY 1 / RHYTHM 2 / MOTION 1
"""
TASKS = {
    "context-resume": ("The user returns to this project after a pause.", "where did we stop?",
                       "Skip step 4 (History): this project has no chat history or notes. Return only the map."),
    "blockers": ("The user runs the skill `blockers` by hand.",
                 "/blockers the change add-export waits for the owner's API key of the export service",
                 "When the skill would edit `docs/waiting.md`, return the whole new file as a line "
                 "`=== docs/waiting.md` followed by its text, any other file it would create the same way under "
                 "`=== <path from the project root>`, then a line `=== report` and the report."),
    "project-init": ("The user runs the skill `project-init` again in this already prepared project.",
                     "/project-init (I filled in every field of DESIGN.md, the Dial numbers too)",
                     "Do only step 5a (`DESIGN.md`) of the text: the other steps are done. When it would edit "
                     "`docs/waiting.md`, return the whole new file as a line `=== docs/waiting.md` followed by its "
                     "text, then a line `=== report` and the report."),
}
PROMPT = """{intro} Follow the skill text below, not an installed copy.

Your project folder is `{copy}`; run every command from it. Read nothing outside the project folder, and never read
`tests/stands` of any repository. This session cannot write or edit files. {task} Today is {today}.

{skill}

The user's message: {message}
"""


def fail(msg):
    sys.exit("waiting-readers: " + msg)


def prepare():
    root = pathlib.Path(tempfile.mkdtemp(prefix=PREFIX))
    copy = root / "project"
    shutil.copytree(HERE / "next-up/project", copy)
    (copy / "docs/waiting.md").write_text(prepared_waiting(), encoding="utf-8")
    (copy / "DESIGN.md").write_text(DESIGN, encoding="utf-8")
    (copy / "web").mkdir()
    (copy / "web/index.html").write_text("<!doctype html>\n<title>Shop</title>\n", encoding="utf-8")
    (copy / "solo-sdd/changes/publish-docs/WAITING").unlink()
    for cmd in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "shop"]):
        subprocess.run(nu.GIT + cmd, cwd=copy, check=True, stdin=subprocess.DEVNULL)
    print("copy: %s" % copy)
    for name, (intro, message, task) in TASKS.items():
        prompt = root / ("prompt-%s.md" % name)
        prompt.write_text(PROMPT.format(intro=intro, copy=copy, task=task, today=datetime.date.today().isoformat(),
                                        skill=nu.skill_text.skill(name).strip(), message=message), encoding="utf-8")
        print("prompt %s: %s" % (name, prompt))


def clean(folder):
    p = pathlib.Path(folder).resolve()
    if p.parent != pathlib.Path(tempfile.gettempdir()).resolve() or not p.name.startswith(PREFIX):
        fail("not a folder prepare made: %s" % folder)
    shutil.rmtree(p)
    print("removed: %s" % p)


def prepared_waiting():
    """The next-up fixture with `publish-docs` under `## Closed` and the `DESIGN.md` row last in the first table."""
    lines = nu.fixture_waiting(True).splitlines()
    last = max(i for i, l in enumerate(lines) if l.startswith("| release-040 |"))
    return "\n".join(lines[:last + 1] + [DESIGN_ROW] + lines[last + 1:]) + "\n"


def split(text):
    """(first table rows, Closed table rows, number of `## Closed` headings), header rows dropped, rows flattened."""
    found = nu.tables(text)
    closed = [t for t in found if t[0] and nu.flat(t[0]) == "## closed"]
    rows = lambda t: [nu.flat(r) for r in t[3][1:]] if t else []
    return rows(found[0] if found else None), rows(closed[0] if closed else None), \
        sum(1 for l in text.splitlines() if nu.flat(l) == "## closed")


def blocker_items(answer):
    """The items of the map's Blockers line: its own text split at `;`, then every list item under it (`-`, `*`, `+`
    or numbered), an indented line continuing the item above; a blank line is skipped, any other line ends it."""
    items, on = [], False
    for line in answer.splitlines():
        f = nu.flat(line).lstrip("# ")
        if not on:
            if f.startswith("blockers"):
                on = True
                items += [i for i in f.split(";")]
        elif not f:
            continue
        elif ITEM.match(line):
            items.append(nu.flat(ITEM.sub("", line, count=1)))
        elif line[:1].isspace() and items:
            items[-1] += " " + f
        else:
            break
    return [i for i in items if i.strip()]


def grade(cr, bl, pi):
    first0, closed0 = split(prepared_waiting())[:2]
    items = blocker_items(cr)
    got = " ".join(items)
    # one closed row, two names; an item that calls it closed does not report it as waiting
    closed_named = int(any(any(w in i for w in CLOSED) and not re.search(r"\bclosed\b", i) for i in items))
    named = sum(1 for words in WAITING if any(w in got for w in words))
    lines = ["context-resume closed rows as blockers: %d" % closed_named,
             "context-resume waiting rows named: %d of %d" % (named, len(WAITING))]
    ok = [bool(got) and closed_named == 0, named == len(WAITING)]
    first, closed, heads = split(nu.blocks(bl).get("docs/waiting.md", ""))
    new = [r for r in first if r not in first0]
    ok += [len(new) == 1 and all(r in first for r in first0), closed == closed0 and heads == 1]
    lines += ["blockers new rows in first table: %d" % len(new),
              "blockers closed table unchanged: %s" % ("yes" if ok[3] else "no")]
    first, closed, heads = split(nu.blocks(pi).get("docs/waiting.md", ""))
    moved = [r for r in closed if "design.md" in r and "no empty fields" in r
             and re.search(r"\|\s*\d{4}-\d{2}-\d{2}\s*\|$", r)]
    ok += [len(moved) == 1 and not any("design.md" in r for r in first) and heads == 1,
           first == first0[:-1] and all(r in closed for r in closed0)]
    lines += ["project-init design row moved to Closed: %s" % ("yes" if ok[4] else "no"),
              "project-init other rows kept: %s" % ("yes" if ok[5] else "no"),
              "waiting readers: %d of %d checks pass" % (sum(ok), len(ok))]
    return lines


if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["prepare"]:
        prepare()
    elif len(a) == 2 and a[0] == "clean":
        clean(a[1])
    elif len(a) == 4 and a[0] == "--grade":
        print("\n".join(grade(*(nu.read(p, "answer") for p in a[1:]))))
    elif len(a) >= 2 and a[0] == "--grade-confined":
        print("grading out of reach: %s" % ("yes" if all(nu.confined(nu.read(p, "transcript")) for p in a[1:])
                                            else "no"))
    else:
        fail("usage: waiting-readers.py prepare | clean <folder> | --grade <context-resume> <blockers> <project-init>"
             " | --grade-confined <transcript>...")
