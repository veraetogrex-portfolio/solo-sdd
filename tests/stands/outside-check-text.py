#!/usr/bin/env python3
"""Stand of the change outside-check-text: an outside `Check:` pass on a draft of 11 facts (`text.md`), 3 of them
planted wrong and one without a source (`planted.json`), and the answer handed over after it.

  --grade <table>          grade a `| fact | mark | right value | source |` table of a Check: run
  --grade-answer <answer>  grade the handed-over evidence-research answer

A table row is matched to a fact by the `F<n>` label in its fact cell. A table with no header holding the fact and
mark columns, or a row whose cell count is not its header's, is refused with exit 1. The Check: run itself is a
Claude Code subagent of the lead session, never `claude -p`."""
import importlib.util
import itertools
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PLANTED = json.loads((HERE / "outside-check-text" / "planted.json").read_text(encoding="utf-8"))["facts"]
_spec = importlib.util.spec_from_file_location("analyze_outside", HERE / "analyze-outside.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
cells = _mod.cells  # the shared table-cell splitter: `\|` and code spans stay inside a cell
MARKS = ("confirmed", "wrong", "no primary source")


def fail(msg):
    sys.exit("outside-check-text: " + msg)


def value(text, v):
    """True when the value stands in the text as a whole value: not inside a longer number or version."""
    return re.search(r"(?<![\d.])" + re.escape(v) + r"(?!\d|\.\d)", text) is not None


def rows(text, path):
    """{label: (mark, right value)} of every table whose header has fact and mark; the first row of a label wins."""
    out, head, tables = {}, None, 0
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith("|"):
            head = None
            continue
        row = cells(line)
        if head is None:
            names = [c.strip("*` ").casefold() for c in row]
            head = names if "fact" in names and "mark" in names else []
            tables += bool(head)
            continue
        if not head or all(re.fullmatch(r":?-+:?", c) for c in row):
            continue
        if len(row) != len(head):
            fail("%s line %d has %d cells, its header %d" % (path, n, len(row), len(head)))
        r = dict(zip(head, row))
        label = re.search(r"\bF(\d+)\b", r["fact"])
        if not label:
            continue
        mark = r["mark"].strip("*` ").casefold()
        mark = next((m for m in MARKS if mark.startswith(m)), mark)
        out.setdefault("F" + label.group(1), (mark, r.get("right value", "")))
    if not tables:
        fail("%s has no table with the columns fact and mark" % path)
    return out


def grade(path):
    got = rows(pathlib.Path(path).read_text(encoding="utf-8"), path)
    want = {k: [f for f, d in PLANTED.items() if d["mark"] == k] for k in MARKS}
    wrong = sum(got.get(f, ("",))[0] == "wrong" and value(got[f][1], PLANTED[f]["right"]) for f in want["wrong"])
    confirmed = sum(got.get(f, ("",))[0] == "confirmed" for f in want["confirmed"])
    nosource = sum(got.get(f, ("",))[0] == "no primary source" for f in want["no primary source"])
    touched = sum(f in got and got[f][0] != "confirmed" for f in want["confirmed"])
    print("wrong %d of %d with the right values, confirmed %d of %d, no primary source %d of %d, touched correct %d"
          % (wrong, len(want["wrong"]), confirmed, len(want["confirmed"]), nosource, len(want["no primary source"]),
             touched))
    for f in sorted(set(PLANTED) - set(got), key=lambda f: int(f[1:])):
        print("missing: %s" % f)


def grade_answer(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    lines = [re.sub(r"^[\s>*_#-]+", "", l).replace("**", "").replace("`", "") for l in text.splitlines()]
    wrong = [d for d in PLANTED.values() if d["mark"] == "wrong"]
    fixed = sum(value(text, d["right"]) and not value(text, d["wrong"]) for d in wrong)
    tokens = [d["token"].casefold() for d in PLANTED.values() if d["mark"] == "no primary source"]
    raw = text.splitlines()
    item = lambda l: re.match(r"\s*(?:[-*+]|\d+[.)])\s", l)  # a list item right under the Not confirmed: line
    unconfirmed = " ".join(" ".join([l] + list(itertools.takewhile(item, raw[i + 1:]))) for i, l in enumerate(lines)
                           if l.startswith("Not confirmed:")).casefold()
    against = any(l.startswith("Against:") and l[len("Against:"):].strip() for l in lines)
    check = [l.strip() for l in lines if l.startswith("Check: ")]
    print("corrected values %d of %d, not confirmed: %s, counter-argument: %s, check line: %s"
          % (fixed, len(wrong), "yes" if unconfirmed and all(t in unconfirmed for t in tokens) else "no",
             "yes" if against else "no", check[-1] if check else "none"))


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in ("--grade", "--grade-answer"):
        fail("usage: outside-check-text.py --grade <table> | --grade-answer <answer>")
    (grade if sys.argv[1] == "--grade" else grade_answer)(sys.argv[2])
