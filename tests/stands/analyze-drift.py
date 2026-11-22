#!/usr/bin/env python3
"""Stand of the change analyze-plan-drift: a `spec-analyze` run on a fixture change whose tasks drift from its
requirements (a default, a setting key) and from its proposal (a promised file no task names).

  prepare new|base    copy the fixture project into a temporary git project and write the prompt of an `Analyze:`
                      subagent; prints `project: <path>` and `prompt: <path>`. `new` embeds the laid-out
                      spec-analyze of this working folder, `base` the text of the base commit read by `git show`
  clean <project>     remove a project `prepare` made
  grade <findings>    the planted holes a saved report names, the decoys it falls for and its `Retell:` block

A row of a Markdown table under a header with Pass, Where and Finding (a row whose Mark starts with `drop` is
skipped) matches a hole when its Level cell holds the hole's level as a whole word, its Pass cell starts with the
hole's pass as a whole token (`7` is not `7a`) and every token of the hole stands whole in its Where or Finding cell:
no letter, digit, `_`, `-` or `.` before it, and no letter, digit, `_`, `-` or a `.` before a letter or digit after
it (`1.3` holds no `3`). A decoy matches by pass and tokens alone. The retell block is a line above the first findings
table that starts with `Retell:` after leading `#`, `*`, `>`, `-` and spaces, with text after the colon or on the next
lines up to a blank line, a table row or a heading, and none of that text names a pass 1 hole token. The subagent
runs inside the lead's Claude Code session, never as `claude -p`."""
import importlib.util
import json
import pathlib
import re
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent / "analyze-drift"
REPO = HERE.parents[2]
BASE = "214ff16"  # main before analyze-outside and this change: its pass 1 has no retell, its pass 7 no value check
PREFIX = "analyze-drift-"
sys.path.insert(0, str(REPO / "tests"))
import skill_text  # noqa: E402

_spec = importlib.util.spec_from_file_location("analyze_outside", HERE.parent / "analyze-outside.py")
analyze_outside = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(analyze_outside)
git = analyze_outside.git


def prepare(variant):
    text = skill_text.skill("spec-analyze") if variant == "new" else \
        git(REPO, "show", "%s:skills/spec-analyze/SKILL.md" % BASE)
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=PREFIX))
    try:
        project = tmp / "project"
        shutil.copytree(HERE / "project", project)
        git(project, "init", "-q")
        git(project, "add", "-A")
        git(project, "commit", "-q", "-m", "fixture")
        prompt = tmp / "prompt.md"
        prompt.write_text(
            "You are an `Analyze:` subagent. Run every pass of the `spec-analyze` skill text below, in place, on the "
            "change `add-retry` of the project `%s`: launch no subagent. Follow only the text below: do not call the "
            "Skill tool and do not read an installed `spec-analyze`, whose text may differ (variant: %s). Edit no "
            "file and write nothing anywhere. Hand back the report in the skill's Report form: its header lines, any "
            "block the form names, the findings table with the columns ID, Pass, Level, Where, Finding and What was "
            "done (leave it empty), and the Ready line.\n\n=== spec-analyze (SKILL.md) ===\n%s" % (project, variant, text))
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print("project: %s" % project)
    print("prompt: %s" % prompt)


def clean(project):
    tmp = pathlib.Path(project).resolve().parent
    if not (tmp.name.startswith(PREFIX) and (tmp / "prompt.md").is_file()
            and tmp.parent == pathlib.Path(tempfile.gettempdir()).resolve()):
        sys.exit("analyze-drift: %s is not a project prepare made" % project)
    shutil.rmtree(tmp)
    print("removed %s" % tmp)


def whole(token, text):
    return re.search(r"(?<![A-Za-z0-9_.-])%s(?![A-Za-z0-9_-]|\.[A-Za-z0-9])" % re.escape(token), text) is not None


def table(lines, path):
    """(index of the first findings header or None, rows): the rows of every table under a header with Pass, Where
    and Finding, as dicts of lowercased header -> cell; a row whose cell count is not its header's is refused."""
    first, rows, head = None, [], None
    for n, line in enumerate(lines):
        if not line.strip().startswith("|"):
            head = None
            continue
        row = analyze_outside.cells(line)
        if head is None:
            names = [c.casefold() for c in row]
            head = names if {"pass", "where", "finding"} <= set(names) else []
            first = n if head and first is None else first
        elif head and not all(re.fullmatch(r":?-+:?", c) for c in row):
            if len(row) != len(head):
                sys.exit("analyze-drift: %s line %d has %d cells, its header %d" % (path, n + 1, len(row), len(head)))
            rows.append(dict(zip(head, row)))
    return first, [r for r in rows if not r.get("mark", "").casefold().startswith("drop")]


def matches(row, item):
    if not re.match(r"\s*%s(?![0-9A-Za-z])" % re.escape(item["pass"]), row.get("pass", "")):
        return False
    if "level" in item and not re.search(r"\b%s\b" % item["level"], row.get("level", "")):
        return False
    where = row.get("where", "") + " " + row.get("finding", "")
    return all(whole(t, where) for t in item["tokens"])


def retell(lines, first, banned):
    """Whether a `Retell:` block with text and without a banned token stands above the first findings table."""
    for n, line in enumerate(lines[:len(lines) if first is None else first]):
        head = line.lstrip("#*>- \t")
        if not head.startswith("Retell:"):
            continue
        body = [head[len("Retell:"):].strip("* \t")]
        for nxt in lines[n + 1:]:
            if nxt.strip().startswith(("|", "#")) or (not nxt.strip() and any(body)):
                break
            body.append(nxt.strip())
        text = " ".join(b for b in body if b)
        if text and not any(whole(t, text) for t in banned):
            return True
    return False


def grade(path):
    p = pathlib.Path(path)
    try:
        text = p.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        sys.exit("analyze-drift: cannot read %s: %s" % (path, e))
    planted = json.loads((HERE / "planted.json").read_text(encoding="utf-8"))
    lines = text.splitlines()
    first, rows = table(lines, path)
    holes = planted["holes"]
    found = [h for h in holes if any(matches(r, h) for r in rows)]
    false = [r for r in rows if any(matches(r, d) for d in planted["decoys"])]
    banned = [t for h in holes if h["pass"] == "1" for t in h["tokens"]]
    for h in holes:
        print("%s %s: %s" % (h["pass"], "/".join(h["tokens"]), "yes" if h in found else "no"))
    print("found %d of %d, false positives %d, retell block: %s"
          % (len(found), len(holes), len(false), "yes" if retell(lines, first, banned) else "no"))


def main(argv):
    if len(argv) == 2 and argv[0] == "prepare" and argv[1] in ("new", "base"):
        prepare(argv[1])
    elif len(argv) == 2 and argv[0] == "clean":
        clean(argv[1])
    elif len(argv) == 2 and argv[0] == "grade":
        grade(argv[1])
    else:
        sys.exit("usage: analyze-drift.py prepare new|base | clean <project> | grade <findings>")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
