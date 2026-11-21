#!/usr/bin/env python3
"""Stand of the change analyze-outside: the spec-analyze check before code in the author's session, in one
`Analyze:` subagent, and in `Attack:` subagents with a `Judge:`, on a fixture change with four planted holes.

  prepare same-session|analyze|attack  copy the fixture project into a temporary git project and write the prompt
                                       of the variant subagent; prints `copy: <path>` and `prompt: <path>`
  clean <copy>                         remove a copy `prepare` made
  grade <findings> <transcript>        the planted holes the kept findings name and the agents the transcript launched

A finding matches a hole when its Pass column names one of the hole's passes and its Where or Finding column holds
the hole's token (`planted.json`). A row is kept unless its Mark column starts with `drop`. Every variant runs as a
Claude Code subagent of the lead session, never as `claude -p`."""
import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent / "analyze-outside"
REPO = HERE.parents[2]
BASE = "8ce66d8"  # release 0.3.0: its spec-analyze and spec-next run the passes in the author's session
VARIANTS = ("same-session", "analyze", "attack")
PREFIX = "analyze-outside-"
sys.path.insert(0, str(REPO / "tests"))
import skill_text  # noqa: E402

GIT = ["git", "-c", "user.name=stand", "-c", "user.email=stand@example.com", "-c", "init.defaultBranch=main",
       "-c", "commit.gpgsign=false", "-c", "core.autocrlf=false"]


def git(cwd, *args, **kw):
    return subprocess.run(GIT + list(args), cwd=cwd, check=True, capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, timeout=60, **kw).stdout


def texts(variant):
    """(name, text) of spec-next and spec-analyze: the base commit's for same-session (read from git, apart from the
    working folder), the laid-out ones otherwise."""
    if variant == "same-session":
        return [(n, git(REPO, "show", "%s:skills/%s/SKILL.md" % (BASE, n))) for n in ("spec-next", "spec-analyze")]
    return [(n, skill_text.skill(n)) for n in ("spec-next", "spec-analyze")]


def prepare(variant):
    tmp = pathlib.Path(tempfile.mkdtemp(prefix=PREFIX))
    try:
        copy = tmp / "project"
        shutil.copytree(HERE / "project", copy)
        if variant == "analyze":
            (copy / "solo-sdd" / "config").write_text("process.analyze-attackers: 0\n")
        git(copy, "init", "-q")
        git(copy, "add", "-A")
        git(copy, "commit", "-q", "-m", "fixture")
        parts = ["You are the lead agent of the project `%s`. Run the `spec-next` skill below on the change "
                 "`add-export` there, steps 1 to 4a only, and stop after step 4a: write no code and commit nothing. "
                 "Print the step 4a report: the `Analyze:` line and the findings table with the columns `Pass`, "
                 "`Where` and `Finding` (and `Mark` when a judge marked them). Write nothing outside `%s`. A "
                 "long-lived process only as a managed background task, stopped before the report." % (copy, copy),
                 "Variant: %s. Follow only the skill texts below: do not call the Skill tool and do not read "
                 "an installed skill, whose text may differ from this variant's.%s" % (variant, "" if variant ==
                 "same-session" else " A subagent you launch gets the skill path %s." % (REPO / "skills/spec-analyze/SKILL.md"))]
        parts += ["=== %s (SKILL.md) ===\n%s" % (n, t) for n, t in texts(variant)]
        prompt = tmp / "prompt.md"
        prompt.write_text("\n\n".join(parts) + "\n")
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    print("copy: %s" % copy)
    print("prompt: %s" % prompt)


def clean(copy):
    tmp = pathlib.Path(copy).resolve().parent
    if not (tmp.name.startswith(PREFIX) and (tmp / "prompt.md").is_file()
            and tmp.parent == pathlib.Path(tempfile.gettempdir()).resolve()):
        sys.exit("analyze-outside: %s is not a copy prepare made" % copy)
    shutil.rmtree(tmp)
    print("removed %s" % tmp)


def cells(line):
    """The cells of a table row: split on `|` unless escaped as `\\|` or inside a single-backtick code span (a
    looser rule than GFM's; a row it splits wrong fails the cell-count check of findings())."""
    out, cell, code, i, s = [], "", False, 0, line.strip()
    s = s[1:] if s.startswith("|") else s
    s = s[:-1] if s.endswith("|") and not s.endswith("\\|") else s
    while i < len(s):
        ch = s[i]
        if ch == "\\" and s[i + 1:i + 2] == "|":
            cell, i = cell + "|", i + 2
            continue
        if ch == "`":
            code = not code
        if ch == "|" and not code:
            out, cell = out + [cell.strip()], ""
        else:
            cell += ch
        i += 1
    return out + [cell.strip()]


def findings(text, path):
    """Every row of every Markdown table whose header has Pass and Where: dicts of lowercased header -> cell. A
    row whose cell count is not its header's, or a non-empty text with no such table, is refused."""
    rows, head, tables = [], None, 0
    for n, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith("|"):
            head = None
            continue
        row = cells(line)
        if head is None:
            names = [c.casefold() for c in row]
            head = names if "pass" in names and "where" in names else []
            tables += bool(head)
        elif head and not all(re.fullmatch(r":?-+:?", c) for c in row):
            if len(row) != len(head):
                sys.exit("analyze-outside: %s line %d has %d cells, its header %d" % (path, n, len(row), len(head)))
            rows.append(dict(zip(head, row)))
    if text.strip() and not tables:
        sys.exit("analyze-outside: %s has no findings table with the columns Pass and Where" % path)
    return rows


def kept(row):
    return not row.get("mark", "").casefold().startswith("drop")


def matches(row, hole):
    passes = set(re.findall(r"\b\d+[a-z]?\b", row.get("pass", "").casefold()))
    where = (row.get("where", "") + " " + row.get("finding", "")).casefold()
    return bool(passes & set(hole["passes"])) and hole["token"].casefold() in where


USAGE = re.compile(r"<usage>.*?\b(?:subagent_tokens|total_tokens): *(\d+)", re.S)


def result_tokens(record, content):
    """The tokens of an agent result in the two forms Claude Code writes: `toolUseResult.totalTokens`, or a
    `<usage>` block with `subagent_tokens:` or `total_tokens:` at the end of the result text; None when neither."""
    if isinstance(record, dict) and isinstance(record.get("totalTokens"), int):
        return record["totalTokens"]
    parts = content if isinstance(content, list) else [{"text": content}] if isinstance(content, str) else []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict) and isinstance(p.get("text"), str))
    m = USAGE.search(text)
    return int(m.group(1)) if m else None


def agents(path):
    """[(description, model, tokens)] of the Agent and Task calls of a Claude Code transcript, in order."""
    calls, tokens = [], {}
    with open(path, "rb") as f:
        for n, raw in enumerate(f, 1):
            if not raw.strip():
                continue
            try:
                d = json.loads(raw)
            except ValueError:
                d = None
            if not isinstance(d, dict) or not isinstance(d.get("message", {}), (dict, type(None))):
                sys.exit("analyze-outside: %s line %d is not a transcript record" % (path, n))
            content = (d.get("message") or {}).get("content")
            for p in content if isinstance(content, list) else []:
                if not isinstance(p, dict):
                    continue
                if d.get("type") == "assistant" and p.get("type") == "tool_use" and p.get("name") in ("Agent", "Task"):
                    ti = p.get("input") or {}
                    calls.append((p.get("id"), ti.get("description", ""), ti.get("model") or "inherit"))
                if p.get("type") == "tool_result":
                    used = result_tokens(d.get("toolUseResult"), p.get("content"))
                    if used is not None:
                        tokens[p.get("tool_use_id")] = used
    return [(desc, model, tokens.get(i)) for i, desc, model in calls]


def grade(findings_path, transcript, label=None):
    planted = json.loads((HERE / "planted.json").read_text())
    rows = [r for r in findings(pathlib.Path(findings_path).read_text(encoding="utf-8"), findings_path) if kept(r)]
    holes = planted["holes"]
    found = [h for h in holes if any(matches(r, h) for r in rows)]
    loose = [r for r in rows if not any(matches(r, h) for h in holes)]
    launched = agents(transcript)
    counted = [t for _, _, t in launched if t is not None]
    label = label or pathlib.Path(findings_path).stem
    if not counted:
        spent = "n/a"
    else:
        spent = str(sum(counted)) + ("" if len(counted) == len(launched)
                                     else " (%d of %d agents)" % (len(counted), len(launched)))
    print("%s: found %d of %d, unmatched keep %d, tokens %s" % (label, len(found), len(holes), len(loose), spent))
    for h in holes:
        print("hole %s (pass %s, %s): %s" % (h["id"], "/".join(h["passes"]), h["token"],
                                             "found" if h in found else "missed"))
    for r in loose:
        print("unmatched keep: %s" % " | ".join(r.values()))
    for desc, model, tok in launched:
        print("agent: %s, model %s, tokens %s" % (desc, model, "n/a" if tok is None else tok))


def main(argv):
    if len(argv) == 2 and argv[0] == "prepare" and argv[1] in VARIANTS:
        prepare(argv[1])
    elif len(argv) == 2 and argv[0] == "clean":
        clean(argv[1])
    elif len(argv) in (3, 5) and argv[0] == "grade" and (len(argv) == 3 or argv[3] == "--label"):
        for p in argv[1:3]:
            if not pathlib.Path(p).is_file():
                sys.exit("analyze-outside: no file %s" % p)
        grade(argv[1], argv[2], argv[4] if len(argv) == 5 else None)
    else:
        sys.exit("usage: analyze-outside.py prepare %s | clean <copy> | grade <findings> <transcript> [--label <name>]"
                 % "|".join(VARIANTS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
