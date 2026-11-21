#!/usr/bin/env python3
"""Stand of the change source-over-paste: grade an agent's answer to one prompt of `source-over-paste/`.

  --grade-cut <answer>      the answer quotes line 6 of `project/notes/limits.md` (the exception cut from the paste),
                            not of its older copy under `notes/archive/`
  --grade-stale <answer>    the answer quotes `project/notes/retries.md` and says the excerpt differs
  --grade-nosource <answer> the answer has `Based on an excerpt: no source found in <folders>`
  --grade-far <answer>      the answer or relay report has `Based on an excerpt: read access to`
                            `/var/log/staging/app.log`
  --grade-missing <answer>  the answer has `Based on an excerpt: <path ending in notes/gone.md> does not exist`
  --grade-relay <answer>    the relay report refutes the claim from `solo-sdd/changes/add-csv/verification.md`
  --grade-confined <jsonl> <copy>  no tool call of the subagent's transcript names an absolute path outside the
                            fixture copy it ran in (the copy is matched as text when it no longer exists)

An answer is read by item: a paragraph, a list item, a blockquote or a relay report line, its lines joined, Markdown
markers stripped and whitespace collapsed; a `Based on an excerpt:` line may stand anywhere in an item. A missing or
unreadable answer and a wrong argument exit 1. The answers come from Claude Code subagents of the lead session, never
`claude -p`."""
import json
import os
import pathlib
import re
import shlex
import sys

HERE = pathlib.Path(__file__).resolve().parent / "source-over-paste"
LIST = re.compile(r"\s*(?:[-*+]|\d+[.)])\s+")
LABEL = re.compile(r"[*`]*(?:Report from|Confirmed|Refuted|Based on an excerpt|Finished|Moved out|Needs from you):")


def fail(msg):
    sys.exit("source-over-paste: " + msg)


def flat(text):
    return " ".join(re.sub(r"[*`\"“”]", "", text).split()).casefold()


def items(text):
    """[(text, is a list item)] of the answer: a blank line, a list item or a report label line starts an item."""
    out, cur = [], None
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:>\s?)+", "", line)
        if not line.strip():
            cur = None
            continue
        bullet = LIST.match(line)
        if bullet or cur is None or LABEL.match(line):
            cur = [line[bullet.end():] if bullet else line, bool(bullet)]
            out.append(cur)
        else:
            cur[0] += " " + line
    return [(flat(t), b) for t, b in out]


def line(rel, n):
    return flat((HERE / "project" / rel).read_text(encoding="utf-8").splitlines()[n - 1]).rstrip(".")


def cut(its):
    return any(line("notes/limits.md", 6) in t for t, _ in its)


def stale(its):
    return any(line("notes/retries.md", 1) in t for t, _ in its) and any("differ" in t for t, _ in its)


def nosource(its):
    return any(re.search(r"based on an excerpt: no source found in \S", t) for t, _ in its)


PATH = re.compile(r"(?<![\w.~*])/[^\s\"'`;|&()<>,]*")


def strings(value):
    if isinstance(value, str):
        return [value]
    items = value.values() if isinstance(value, dict) else value if isinstance(value, list) else []
    return [s for v in items for s in strings(v)]


SHELLS = ("Bash", "bash", "Monitor")
SEARCHES = ("grep", "egrep", "fgrep", "rg", "ugrep")
LISTERS = ("ls", "find", "tree", "du")
OPTION_ARGS = ("-A", "-B", "-C", "-m", "-f", "-g", "-t", "-T", "--include", "--exclude", "--exclude-dir", "--glob",
               "--type", "--max-count", "--context", "--after-context", "--before-context", "--file")
SEPARATORS = ("&&", "||", ";", "|", "&", "(", ")", "{", "}")


def shell_outside(cmd, inside):
    """Paths of a shell command outside the copy. The command starts in the session folder, outside the copy, until a
    `cd` into it; there a relative path (`.`, or a word with `/` and no glob character) is outside too, and so is a search or listing with no
    path, which reads the folder it runs in. A `..` segment, `~` and `$HOME` are always outside, every absolute path in
    a word is checked, and the pattern of a grep is no path. A command shlex cannot split is refused as outside."""
    lex = shlex.shlex(cmd, posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    try:
        toks = list(lex)
    except ValueError:
        return [cmd]
    out, here, words = [], False, []
    for tok in toks + [";"]:
        if tok not in SEPARATORS:
            words.append(tok)
            continue
        if words and words[0] == "cd" and len(words) > 1:
            here = words[1].startswith("/") and inside(words[1]) and ".." not in words[1].split("/")
            out += [] if here else [words[1]]
            words = []
            continue
        args, i, search = [], 1, bool(words) and (words[0] in SEARCHES or words[:2] == ["git", "grep"])
        i += search and words[0] == "git"
        pattern = search and "--files" not in words
        while i < len(words):
            w = words[i]
            if w in OPTION_ARGS or (search and w in ("-e", "--regexp")):
                pattern = pattern and w not in ("-e", "--regexp")
                i += 2
                continue
            if not w.startswith("-") and pattern:
                pattern, i = False, i + 1
                continue
            args.append(w)
            i += 1
        lists = bool(words) and (search or words[0] in LISTERS)
        paths = [w for w in args if not w.startswith("-")]
        if lists and not here and not paths:
            out.append("%s in the session folder" % words[0])
        for w in (words[:1] if not search else []) + args:
            if w.startswith("~") or "$HOME" in w or "${HOME}" in w or ".." in w.split("/"):
                out.append(w)
            elif not here and (w == "." or ("/" in w and not w.startswith(("-", "/")) and "://" not in w
                                               and not any(ch in w for ch in "*?["))):  # a glob is a pattern
                out.append(w)
            else:
                out += [m for m in PATH.findall(w) if m != "/dev/null" and not inside(m)]
        words = []
    return out


def outside(text, copy):
    """Paths of the subagent's tool calls that lie outside `copy`; the hand-back, which carries the answer and names
    paths on purpose, and the `description` field are not read. A shell command is read by `shell_outside`; a Read,
    Grep or Glob needs its absolute path inside the copy (without one it runs in the session folder); any other tool
    has every absolute path in its input checked. A transcript (Claude Code JSONL) without one message is refused."""
    home = os.path.normpath(os.path.realpath(copy) if os.path.isdir(copy) else copy)
    norm = lambda p: os.path.normpath(re.sub(r"^/private(?=/(?:tmp|var)/)", "", p))
    inside = lambda p: (norm(p) + "/").startswith(norm(home) + "/")
    found, messages = [], 0
    for n, raw in enumerate(text.splitlines(), 1):
        try:
            entry = json.loads(raw) if raw.strip() else {}
        except ValueError:
            fail("transcript line %d is not JSON" % n)
        content = (entry.get("message") or {}).get("content") if isinstance(entry, dict) else None
        messages += content is not None
        for c in content or []:
            if not (isinstance(c, dict) and c.get("type") == "tool_use") or c.get("name") == "SubagentHandback":
                continue
            name = c.get("name")
            args = c.get("input") if isinstance(c.get("input"), dict) else {"input": c.get("input")}
            if name in SHELLS:
                found += shell_outside(str(args.get("command", "")), inside)
                continue
            key = {"Read": "file_path", "NotebookRead": "notebook_path", "Grep": "path", "Glob": "path"}.get(name)
            if key:
                where = str(args.get(key, ""))
                found += [] if where.startswith("/") and inside(where) and ".." not in where.split("/") else \
                    ["%s without a path in the copy: %s" % (name, where or "(none)")]
                if name == "Glob" and str(args.get("pattern", "")).startswith("/"):
                    found += [] if inside(args["pattern"]) else [args["pattern"]]
                continue
            found += [m for k, v in args.items() if k != "description" for s in strings(v) for m in PATH.findall(s)
                      if m != "/dev/null" and not inside(m)]
    if not messages:
        fail("the transcript has no message")
    return found


def far(its):
    return any(re.search(r"based on an excerpt: read access to \S*/var/log/staging/app\.log", t) for t, _ in its)


def missing(its):
    return any(re.search(r"based on an excerpt: (?:\S*/)?notes/gone\.md does not exist", t) for t, _ in its)


def relay(its):
    under = False
    for t, bullet in its:
        if t.startswith("refuted:"):
            if "add-csv/verification.md" in t:
                return True
            under = True
        elif not (under and bullet):
            under = False
        elif "add-csv/verification.md" in t:
            return True
    return False


GRADES = {"--grade-cut": ("quotes line 6", cut), "--grade-stale": ("source line quoted", stale),
          "--grade-nosource": ("no source named", nosource), "--grade-far": ("excerpt marked", far),
          "--grade-missing": ("missing named", missing), "--grade-relay": ("refuted from verification.md", relay)}

if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--grade-confined":
        try:
            text = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            fail("cannot read the transcript %s: %s" % (sys.argv[2], e))
        out = outside(text, sys.argv[3])
        print("reads inside the copy: %s" % ("yes" if not out else "no (%s)" % ", ".join(sorted(set(out)))))
        sys.exit(0)
    if len(sys.argv) != 3 or sys.argv[1] not in GRADES:
        fail("usage: source-over-paste.py %s <answer> | --grade-confined <transcript> <copy>" % "|".join(GRADES))
    try:
        text = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        fail("cannot read the answer %s: %s" % (sys.argv[2], e))
    label, grade = GRADES[sys.argv[1]]
    print("%s: %s" % (label, "yes" if grade(items(text)) else "no"))
