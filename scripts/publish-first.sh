#!/usr/bin/env bash
# First publication of solo-sdd without history. No arguments: check and plan; with --go: run.
set -Eeuo pipefail

GO=0
case "${1:-}" in
  "") ;;
  --go) GO=1 ;;
  *) echo "Usage: bash scripts/publish-first.sh [--go]" >&2; exit 2 ;;
esac
[ $# -le 1 ] || { echo "Usage: bash scripts/publish-first.sh [--go]" >&2; exit 2; }

cd "$(git rev-parse --show-toplevel)"

REPO=veraetogrex-portfolio/solo-sdd
OWNER=veraetogrex-portfolio
DESC='Process for spec-driven development with AI coding agents: skills, rules and hooks for Claude Code and Codex'

VIOLATIONS=""
violation() { VIOLATIONS="$VIOLATIONS- $1"$'\n'; }

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

# --- preconditions
[ "$(git symbolic-ref --short -q HEAD || true)" = main ] || violation "current branch is not main"
git show-ref --verify --quiet refs/heads/history-local && violation "branch history-local already exists"
git show-ref --verify --quiet refs/tags/v0.1.0 && violation "tag v0.1.0 already exists"
git remote | grep -qx origin && violation "remote origin already exists"
[ "$(git worktree list | wc -l | tr -d ' ')" = 1 ] || violation "there are other worktrees (git worktree list is more than one line)"
dirty=$(git status --porcelain -- . ':(exclude)solo-sdd' ':(exclude)docs/waiting.md')
[ -z "$dirty" ] || violation "working copy is not clean (except solo-sdd/ and docs/waiting.md):"$'\n'"$dirty"

if out=$(python3 tests/test_public_tree.py 2>&1 < /dev/null); then :; else
  violation "tests/test_public_tree.py failed:"$'\n'"$(printf '%s\n' "$out" | tail -n 8)"
fi

if ! command -v gh > /dev/null; then
  violation "gh not found, cannot check login and repository existence"
else
  login=$(gh api user --jq .login 2> /dev/null || true)
  [ "$login" = "$OWNER" ] || violation "gh is logged in as '${login:-?}', need $OWNER"
  rc=0
  out=$(gh repo view "$REPO" 2>&1 < /dev/null) || rc=$?
  if [ "$rc" = 0 ]; then
    violation "repository $REPO already exists"
  elif ! printf '%s' "$out" | grep -q 'Could not resolve to a Repository'; then
    violation "could not check $REPO: $(printf '%s' "$out" | head -n 2)"
  fi
fi

# --- the future commit: in a temporary index; the index, files and branches do not change
ignore=$(git show HEAD:.gitignore)
new_ignore=$ignore
printf '%s\n' "$ignore" | grep -qxF 'solo-sdd/' || new_ignore=$ignore$'\n''solo-sdd/'
export_idx() { GIT_INDEX_FILE=$tmp/index "$@"; }
export_idx git read-tree HEAD
export_idx git rm -r -q --cached --ignore-unmatch -- solo-sdd docs/waiting.md
blob=$(printf '%s\n' "$new_ignore" | git hash-object -w --stdin)
export_idx git update-index --cacheinfo "100644,$blob,.gitignore"
tree=$(export_idx git write-tree)
commit=$(git commit-tree "$tree" -m 'solo-sdd 0.1.0')

# --- tree checks
block=$(printf '%s\n' "$ignore" | awk '/^# single owner/{f=1;next} f&&NF&&!/^#/')
nblock=$(printf '%s' "$block" | grep -c . || true)
[ "$nblock" -ge 10 ] || violation ".gitignore: the \"single owner\" block is shorter than 10 lines ($nblock)"
bad=$(printf 'solo-sdd/\ndocs/waiting.md\n%s\n' "$block" | grep . | while IFS= read -r p; do
  git ls-tree -r --name-only "$commit" -- "$p"
done | sort -u)
[ -z "$bad" ] || violation "the new commit has forbidden files:"$'\n'"$bad"
[ -z "$(git log -n 1 --format=%H "$commit" -- solo-sdd)" ] || violation "git log of the new commit -- solo-sdd is not empty"

if [ -n "$VIOLATIONS" ]; then
  printf 'Publication impossible:\n%s' "$VIOLATIONS" >&2
  exit 1
fi

# --- plan; step prints the command and runs it with --go
HOOKS=$(git rev-parse --git-path hooks)

install_hook() {
  mkdir -p "$HOOKS"
  [ ! -e "$HOOKS/pre-push" ] || mv "$HOOKS/pre-push" "$HOOKS/pre-push.before-publish"
  cat > "$HOOKS/pre-push" <<'HOOK'
#!/bin/sh
# solo-sdd: the old history and the solo-sdd/ tree do not go to the remote
tmp=$(mktemp) || exit 1
trap 'rm -f "$tmp"' EXIT
cat > "$tmp"
while read -r lref lsha rref rsha; do
  case "$lsha" in *[!0]*) ;; *) continue ;; esac
  why=
  if [ "$lref" = refs/heads/history-local ]; then why="this is branch history-local"
  elif ! git rev-parse -q --verify "$lsha^{commit}" > /dev/null; then why="not a commit"
  elif git merge-base "$lsha" history-local > /dev/null 2>&1; then why="shared history with history-local"
  elif [ -n "$(git rev-list -n 1 "$lsha" -- solo-sdd)" ]; then why="the history has solo-sdd/"
  fi
  if [ -n "$why" ]; then
    echo "pre-push: refused for $lref: $why" >&2
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
  echo "Not done: $CURRENT (code $rc). No rollbacks: the old history is in branch history-local (if the rename step has passed). Run the rest of the plan with the commands from the plan above." >&2
  exit "$rc"
}

step() {
  CURRENT=$*
  printf '+'
  printf ' %q' "$@"
  printf '\n'
  if [ "$GO" = 1 ]; then "$@"; fi
}

[ "$GO" = 1 ] && echo "Running the plan (--go):" || echo "Plan (dry run, nothing changes; add --go to run):"
echo "New commit $commit: HEAD tree without solo-sdd/ and docs/waiting.md (git rm --cached), solo-sdd/ in .gitignore."
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
[ "$GO" = 1 ] && echo "Done." || true
