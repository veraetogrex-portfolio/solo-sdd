#!/bin/sh
# The ## Lessons section of AGENTS.md next to this script and sha256 of the three installed global rule copies.
cd "$(dirname "$0")" || exit 1
if [ ! -f AGENTS.md ]; then
  echo "AGENTS.md: missing"
elif grep -q '^## Lessons$' AGENTS.md; then
  section=$(awk '/^## /{p=($0=="## Lessons"); next} p && NF' AGENTS.md)
  echo "## Lessons: $(printf '%s\n' "$section" | grep -c .) lines"
  printf '%s\n' "$section"
else
  echo "## Lessons: missing"
fi
for f in "$HOME/AGENTS.md" "$HOME/.codex/AGENTS.md" "$HOME/.claude/CLAUDE.md"; do
  if [ -f "$f" ]; then shasum -a 256 "$f"; else echo "missing $f"; fi
done
