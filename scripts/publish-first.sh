#!/usr/bin/env bash
# Первая публикация solo-sdd без истории. Без аргументов - проверка и план, с --go - выполнение.
set -Eeuo pipefail

GO=0
case "${1:-}" in
  "") ;;
  --go) GO=1 ;;
  *) echo "Использование: bash scripts/publish-first.sh [--go]" >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "Использование: bash scripts/publish-first.sh [--go]" >&2; exit 2; }

cd "$(git rev-parse --show-toplevel)"

REPO=veraetogrex-portfolio/solo-sdd
OWNER=veraetogrex-portfolio
DESC='Process for spec-driven development with AI coding agents: skills, rules and hooks for Claude Code and Codex'

VIOLATIONS=""
violation() { VIOLATIONS="$VIOLATIONS- $1"$'\n'; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# --- предусловия
[ "$(git symbolic-ref --short -q HEAD || true)" = main ] || violation "текущая ветка не main"
git show-ref --verify --quiet refs/heads/history-local && violation "ветка history-local уже есть"
git show-ref --verify --quiet refs/tags/v0.1.0 && violation "тег v0.1.0 уже есть"
git remote | grep -qx origin && violation "remote origin уже есть"
[ "$(git worktree list | wc -l | tr -d ' ')" = 1 ] || violation "есть другие worktree (git worktree list не из одной строки)"
dirty=$(git status --porcelain -- . ':(exclude)openspec' ':(exclude)docs/waiting.md')
[ -z "$dirty" ] || violation "рабочая копия не чистая (кроме openspec/ и docs/waiting.md):"$'\n'"$dirty"

if out=$(python3 tests/test_public_tree.py 2>&1 < /dev/null); then :; else
  violation "tests/test_public_tree.py не прошёл:"$'\n'"$(printf '%s\n' "$out" | tail -n 8)"
fi

if ! command -v gh > /dev/null; then
  violation "gh не найден, вход и существование репозитория не проверить"
else
  login=$(gh api user --jq .login 2> /dev/null || true)
  [ "$login" = "$OWNER" ] || violation "gh вошёл как '${login:-?}', нужен $OWNER"
  rc=0
  out=$(gh repo view "$REPO" 2>&1 < /dev/null) || rc=$?
  if [ "$rc" = 0 ]; then
    violation "репозиторий $REPO уже существует"
  elif ! printf '%s' "$out" | grep -q 'Could not resolve to a Repository'; then
    violation "не удалось проверить $REPO: $(printf '%s' "$out" | head -n 2)"
  fi
fi

# --- будущий коммит: во временном индексе, ни индекс, ни файлы, ни ветки не меняются
ignore=$(git show HEAD:.gitignore)
new_ignore=$ignore
printf '%s\n' "$ignore" | grep -qxF 'openspec/' || new_ignore=$ignore$'\n''openspec/'
export_idx() { GIT_INDEX_FILE=$tmp/index "$@"; }
export_idx git read-tree HEAD
export_idx git rm -r -q --cached --ignore-unmatch -- openspec docs/waiting.md
blob=$(printf '%s\n' "$new_ignore" | git hash-object -w --stdin)
export_idx git update-index --cacheinfo "100644,$blob,.gitignore"
tree=$(export_idx git write-tree)
commit=$(git commit-tree "$tree" -m 'solo-sdd 0.1.0')

# --- проверки дерева
block=$(printf '%s\n' "$ignore" | awk '/^# под одного владельца/{f=1;next} f&&NF&&!/^#/')
nblock=$(printf '%s' "$block" | grep -c . || true)
[ "$nblock" -ge 10 ] || violation ".gitignore: блок «под одного владельца» короче 10 строк ($nblock)"
bad=$(printf 'openspec/\ndocs/waiting.md\n%s\n' "$block" | grep . | while IFS= read -r p; do
  git ls-tree -r --name-only "$commit" -- "$p"
done | sort -u)
[ -z "$bad" ] || violation "в новом коммите есть запрещённые файлы:"$'\n'"$bad"
[ -z "$(git log -n 1 --format=%H "$commit" -- openspec)" ] || violation "git log нового коммита -- openspec не пуст"

if [ -n "$VIOLATIONS" ]; then
  printf 'Публикация невозможна:\n%s' "$VIOLATIONS" >&2
  exit 1
fi

# --- план; step печатает команду и с --go выполняет её
HOOKS=$(git rev-parse --git-path hooks)

install_hook() {
  mkdir -p "$HOOKS"
  [ ! -e "$HOOKS/pre-push" ] || mv "$HOOKS/pre-push" "$HOOKS/pre-push.before-publish"
  cat > "$HOOKS/pre-push" <<'HOOK'
#!/bin/sh
# solo-sdd: старая история и openspec не уходят на remote
tmp=$(mktemp) || exit 1
trap 'rm -f "$tmp"' EXIT
cat > "$tmp"
while read -r lref lsha rref rsha; do
  case "$lsha" in *[!0]*) ;; *) continue ;; esac
  why=
  if [ "$lref" = refs/heads/history-local ]; then why="это ветка history-local"
  elif ! git rev-parse -q --verify "$lsha^{commit}" > /dev/null; then why="не коммит"
  elif git merge-base "$lsha" history-local > /dev/null 2>&1; then why="общая история с history-local"
  elif [ -n "$(git rev-list -n 1 "$lsha" -- openspec)" ]; then why="в истории есть openspec"
  fi
  if [ -n "$why" ]; then
    echo "pre-push: отказ для $lref: $why" >&2
    exit 1
  fi
done < "$tmp"
old=$(dirname "$0")/pre-push.before-publish
if [ -x "$old" ]; then
  "$old" "$@" < "$tmp"
  exit $?
fi
exit 0
HOOK
  chmod +x "$HOOKS/pre-push"
}

fail() {
  rc=$?
  echo "Не выполнено: $CURRENT (код $rc). Откатов нет: старая история лежит в ветке history-local (если шаг переименования уже прошёл). Остаток плана выполни командами из плана выше." >&2
  exit "$rc"
}

step() {
  CURRENT=$*
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if [ "$GO" = 1 ]; then "$@"; fi
}

[ "$GO" = 1 ] && echo "Выполнение плана (--go):" || echo "План (пробный запуск, ничего не меняется; для выполнения добавь --go):"
echo "Новый коммит $commit: дерево HEAD без openspec/ и docs/waiting.md (git rm --cached), openspec/ в .gitignore."
[ "$GO" = 1 ] && trap fail ERR
step git branch -m main history-local
step git branch main "$commit"
step git symbolic-ref HEAD refs/heads/main
step git read-tree main
step git checkout main -- .gitignore
step git tag v0.1.0
step install_hook
step gh repo create "$REPO" --public --source . --remote origin --description "$DESC"
step gh repo edit "$REPO" --add-topic openspec --add-topic claude-code --add-topic codex --add-topic spec-driven-development
step git push -u origin refs/heads/main:refs/heads/main refs/tags/v0.1.0:refs/tags/v0.1.0
[ "$GO" = 1 ] && echo "Готово." || true
