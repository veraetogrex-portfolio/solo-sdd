#!/usr/bin/env bash
# Stand of change artifacts-tracked: the dispatcher queue with git-tracked and ignored specs.
# Repository 1: openspec in git; change done is committed, fresh is untracked, edited is changed after the commit.
# Repository 2: openspec/ in .gitignore, the same three changes lie in the folder.
# Only git and python3 are needed; nothing outside the temporary folder changes.
set -euo pipefail

tool="$(cd "$(dirname "$0")/../.." && pwd)/global/sdd_dispatch_plan.py"
d="$(mktemp -d)"
trap 'rm -rf "$d"' EXIT
g() { git -c user.name=t -c user.email=t@t -C "$1" "${@:2}"; }

need() { grep -qxF -- "$2" <<<"$1" || { echo "NO LINE: $2"; exit 1; }; }
mk() {
  mkdir -p "$1/openspec/changes/$2"
  printf '# %s\n\n## Depends On\n\nnone\n' "$2" > "$1/openspec/changes/$2/proposal.md"
}

echo "=== openspec in git"
a="$d/tracked"; mkdir "$a"; g "$a" init -q -b main
echo r > "$a/README.md"
mk "$a" done; mk "$a" edited
echo "- [ ] 1" > "$a/openspec/changes/edited/tasks.md"
g "$a" add -A; g "$a" commit -qm init
echo "- [x] 1" > "$a/openspec/changes/edited/tasks.md"
mk "$a" fresh
out=$(python3 "$tool" "$a" < /dev/null); echo "$out"
need "$out" 'launch: done'
need "$out" '  edited — not committed'
need "$out" '  fresh — not committed'

echo "=== openspec/ ignored"
b="$d/ignored"; mkdir "$b"; g "$b" init -q -b main
echo r > "$b/README.md"; echo "openspec/" > "$b/.gitignore"
g "$b" add -A; g "$b" commit -qm init
mk "$b" done; mk "$b" edited; mk "$b" fresh
out=$(python3 "$tool" "$b" < /dev/null); echo "$out"
need "$out" 'launch: done edited fresh'
need "$out" 'Artifacts outside git: openspec/'
