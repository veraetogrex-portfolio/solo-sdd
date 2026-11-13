#!/bin/sh
# solo-sdd pre-push guard: no commit of the private history goes to a remote. Installed as the pre-push hook by
# "Publication without the private history" of docs/release.md; refuses a pushed ref that is not a commit or shares
# history with the local branch history-local or history-private, passes deletions and every other ref.
while read -r lref lsha rref rsha; do
  case "$lsha" in *[!0]*) ;; *) continue ;; esac
  why=
  if ! commit=$(git rev-parse -q --verify "$lsha^{commit}" 2> /dev/null); then why="not a commit"
  else
    for old in history-local history-private; do
      if git merge-base "$commit" "refs/heads/$old" > /dev/null 2>&1; then
        why="shared history with $old"
        break
      fi
    done
  fi
  if [ -n "$why" ]; then
    echo "pre-push: refused for $lref to $rref: $why" >&2
    exit 1
  fi
done
exit 0
