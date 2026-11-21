#!/bin/sh
# The ## Lessons section of AGENTS.md next to this script, its lines over 300 characters, its links to ids missing in
# LESSONS.md, its committed lines lost (in neither the section nor LESSONS.md), and sha256 of the three installed
# global rule copies.
cd "$(dirname "$0")" || exit 1
if [ ! -f AGENTS.md ]; then
  echo "AGENTS.md: missing"
else
  if grep -q '^## Lessons$' AGENTS.md; then
    section=$(awk '/^## /{p=($0=="## Lessons"); next} p && NF' AGENTS.md)
    echo "## Lessons: $(printf '%s\n' "$section" | grep -c .) lines"
    printf '%s\n' "$section"
  else
    echo "## Lessons: missing"
  fi
  python3 - <<'PY'
import os, re, subprocess

LINK = re.compile(r"\s*\(\[full text\]\(LESSONS\.md#([^)\s]+)\)\)\s*$")


def items(text):
    """(text before the link, linked id or None) of every '- ' line of the ## Lessons section."""
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line.rstrip() == "## Lessons"
        elif inside and line.startswith("- "):
            m = LINK.search(line)
            out.append((line[2:m.start()] if m else line[2:].rstrip(), m.group(1) if m else None))
    return out


flat = lambda s: " ".join(s.split())
now = items(open("AGENTS.md", encoding="utf-8").read())
lessons = open("LESSONS.md", encoding="utf-8").read() if os.path.isfile("LESSONS.md") else ""
heads = set(re.findall(r"^### (\S+)\s*$", lessons, re.M))
print("over 300: %d" % sum(len(t) > 300 for t, _ in now))
missing = sorted({i for _, i in now if i and i not in heads})
print("missing ids: %s" % (", ".join(missing) or "none"))
git = lambda *a: subprocess.run(("git",) + a, capture_output=True, text=True, stdin=subprocess.DEVNULL)
if git("rev-parse", "--verify", "-q", "HEAD").returncode != 0:
    print("lost: n/a")
else:
    shown = git("show", "HEAD:./AGENTS.md")
    kept = {flat(t) for t, _ in now}
    print("lost: %d" % sum(flat(t) not in kept and flat(t) not in flat(lessons)
                           for t, _ in (items(shown.stdout) if shown.returncode == 0 else [])))
PY
fi
for f in "$HOME/AGENTS.md" "$HOME/.codex/AGENTS.md" "$HOME/.claude/CLAUDE.md"; do
  if [ -f "$f" ]; then shasum -a 256 "$f"; else echo "missing $f"; fi
done
