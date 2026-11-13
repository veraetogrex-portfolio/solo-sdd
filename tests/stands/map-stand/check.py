#!/usr/bin/python3
"""Check of the codebase map written by `/project-init` (change codebase-map).

Usage: check.py <repo>. Reads `<repo>/docs/codebase/{STACK,ARCHITECTURE,CONVENTIONS,CONCERNS}.md`.
Prints a missing or empty file, a first line that is not `Commit: <full hash> <commit date>` of a commit of the
repository, a line that is neither a heading nor a list item (every statement is a list item), a file without
statements, and every list item that names no path existing at the stamped commit (paths in backticks;
a `:12` line suffix and a trailing `/` are allowed). Exit 1 on any finding; the last line is the summary.
"""
import pathlib
import re
import subprocess
import sys

FILES = ("STACK.md", "ARCHITECTURE.md", "CONVENTIONS.md", "CONCERNS.md")
STAMP = re.compile(r"^Commit: ([0-9a-f]{40}) (\d{4}-\d{2}-\d{2})\s*$")
ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(.*)$")
TICKS = re.compile(r"`([^`\n]+)`")
LINE_SUFFIX = re.compile(r":\d+(?:-\d+)?$")


def exists(repo, rev, path):
    path = LINE_SUFFIX.sub("", path.strip()).rstrip("/")
    if not path or path.startswith("/"):
        return False
    return git_ok(repo, rev + ":" + (path[2:] if path.startswith("./") else path))


def git_ok(repo, obj):
    return subprocess.run(["git", "-C", str(repo), "cat-file", "-e", obj],
                          capture_output=True, stdin=subprocess.DEVNULL).returncode == 0


def commit_date(repo, rev):
    p = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%cs", rev + "^{commit}", "--"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.stdout.strip() if p.returncode == 0 else None


def check(repo):
    repo = pathlib.Path(repo)
    findings, items = [], 0
    for name in FILES:
        path = repo / "docs" / "codebase" / name
        rel = "docs/codebase/" + name
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
        if not text.strip():
            findings.append("%s: missing or empty" % rel)
            continue
        lines = text.splitlines()
        m = STAMP.match(lines[0])
        if not m or commit_date(repo, m.group(1)) != m.group(2):
            findings.append("%s:1: stamp is not `Commit: <hash> <date>` of a commit of the repository: %s"
                            % (rel, lines[0]))
            continue
        rev, statements = m.group(1), 0
        for no, line in enumerate(lines[1:], 2):
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            item = ITEM.match(line)
            if not item:
                findings.append("%s:%d: not a list item: %s" % (rel, no, line.strip()))
                continue
            statements += 1
            if not any(exists(repo, rev, p) for p in TICKS.findall(item.group(1))):
                findings.append("%s:%d: no existing path: %s" % (rel, no, item.group(1)))
        if not statements:
            findings.append("%s: no statements" % rel)
        items += statements
    for f in findings:
        print(f)
    print("map %s: %d files, %d statements, %d findings"
          % ("ok" if not findings else "FAIL", len(FILES), items, len(findings)))
    return 1 if findings else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: check.py <repo>")
    sys.exit(check(sys.argv[1]))
