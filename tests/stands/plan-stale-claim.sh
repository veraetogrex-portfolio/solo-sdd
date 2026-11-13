#!/usr/bin/env bash
# Live Scenario stand of change plan-stale-claim: steps 1-3 on a real run of sdd_dispatch_plan.py.
# Its own project with three stub changes and a temporary HOME: real changes and hook-state are not involved,
# dispatch-stand.sh does not fit here: it needs OpenSpec and its solo schema.
# Run from the repository root: bash tests/stands/plan-stale-claim.sh
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/global/sdd_dispatch_plan.py"
DIR="$(mktemp -d "${TMPDIR:-/tmp}/plan-stale-XXXXXX")"
trap 'rm -rf "$DIR"' EXIT
export HOME="$DIR/home"
mkdir -p "$HOME/.claude/hook-state"
cd "$DIR"
git init -q -b main project
cd project
for id in a-stale b-stale c-live; do
  mkdir -p "openspec/changes/$id"
  printf '# %s\n\n## Depends On\n\nnone\n' "$id" > "openspec/changes/$id/proposal.md"
done
git add -A
git -c user.name=t -c user.email=t@t commit -qm init
echo "claude 2026-10-21 session=stalesid-0000" > openspec/changes/a-stale/CLAIM
echo "claude 2026-10-21 session=stalesid-0000" > openspec/changes/b-stale/CLAIM
echo "claude 2026-10-21 session=live0000-0000" > openspec/changes/c-live/CLAIM
touch "$HOME/.claude/hook-state/live0000-0000.json"

want() {
  case "$OUT" in
    *"$1"*) ;;
    *) echo "NO line: $1" >&2; exit 1 ;;
  esac
}

echo "--- step 2: two abandoned, one live"
OUT="$(python3 "$SCRIPT" .)"
echo "$OUT" | grep ' — '
want "a-stale — CLAIM abandoned: session stalesid silent"
want "b-stale — CLAIM abandoned: session stalesid silent"
want "c-live — CLAIM"
case "$OUT" in *"c-live — CLAIM abandoned"*) echo "the live marker is abandoned" >&2; exit 1 ;; esac
git branch change/a-stale
echo "--- step 3: a branch wins over a marker"
OUT="$(python3 "$SCRIPT" .)"
echo "$OUT" | grep ' — '
want "a-stale — not merged: branch change/a-stale"
git branch -D -q change/a-stale
LEFT="$(find openspec -name CLAIM | wc -l | tr -d ' ')"
[ "$LEFT" = 3 ] || { echo "markers removed: $LEFT left" >&2; exit 1; }
echo "--- markers in place: $LEFT of 3"
