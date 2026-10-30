#!/usr/bin/env bash
# Стенд change artifacts-tracked: очередь диспетчера при git-трекаемых и игнорируемых спеках.
# Репозиторий 1: openspec в git; change done закоммичен, fresh не отслеживается, edited изменён после коммита.
# Репозиторий 2: openspec/ в .gitignore, те же три change лежат в папке.
# Нужны только git и python3; ничего вне временной папки не меняется.
set -euo pipefail

tool="$(cd "$(dirname "$0")/../.." && pwd)/global/sdd_dispatch_plan.py"
d="$(mktemp -d)"
trap 'rm -rf "$d"' EXIT
g() { git -c user.name=t -c user.email=t@t -C "$1" "${@:2}"; }

need() { grep -qxF -- "$2" <<<"$1" || { echo "НЕТ СТРОКИ: $2"; exit 1; }; }
mk() {
  mkdir -p "$1/openspec/changes/$2"
  printf '# %s\n\n## Depends On\n\nnone\n' "$2" > "$1/openspec/changes/$2/proposal.md"
}

echo "=== openspec в git"
a="$d/tracked"; mkdir "$a"; g "$a" init -q -b main
echo r > "$a/README.md"
mk "$a" done; mk "$a" edited
echo "- [ ] 1" > "$a/openspec/changes/edited/tasks.md"
g "$a" add -A; g "$a" commit -qm init
echo "- [x] 1" > "$a/openspec/changes/edited/tasks.md"
mk "$a" fresh
out=$(python3 "$tool" "$a" < /dev/null); echo "$out"
need "$out" 'запустить: done'
need "$out" '  edited — не закоммичен'
need "$out" '  fresh — не закоммичен'

echo "=== openspec/ игнорируется"
b="$d/ignored"; mkdir "$b"; g "$b" init -q -b main
echo r > "$b/README.md"; echo "openspec/" > "$b/.gitignore"
g "$b" add -A; g "$b" commit -qm init
mk "$b" done; mk "$b" edited; mk "$b" fresh
out=$(python3 "$tool" "$b" < /dev/null); echo "$out"
need "$out" 'запустить: done edited fresh'
need "$out" 'Артефакты вне git: openspec/'
