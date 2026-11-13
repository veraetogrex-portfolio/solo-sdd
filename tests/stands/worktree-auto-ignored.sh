#!/usr/bin/env bash
# Live Scenario stand of change worktree-auto-ignored: steps 1-5 on a real run of sdd_worktree.py.
# Its own project and worktree in a temporary folder; sync.py push is not called.
# Run from the repository root: bash tests/stands/worktree-auto-ignored.sh
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/global/sdd_worktree.py"
DIR="$(mktemp -d "${TMPDIR:-/tmp}/auto-ignored-XXXXXX")"
trap 'rm -rf "$DIR"' EXIT
MAIN="$DIR/main"
WT="$DIR/wt-a"

fail() { echo "FAILED: $1" >&2; exit 1; }

echo "--- step 1: project"
git init -q -b main "$MAIN"
cd "$MAIN"
mkdir docs out data
printf 'docs/architecture.md\nout/\ndata/big.bin\ntsconfig.tsbuildinfo\n.env\n' > .gitignore
printf 'notes\n' > docs/notes.md
printf '# P\n' > AGENTS.md
git add -A
git -c user.name=t -c user.email=t@t commit -qm init
printf 'line 1\nline 2\n' > docs/architecture.md
printf 'x\n' > out/app.js
head -c 2097152 /dev/zero > data/big.bin
printf 'build\n' > tsconfig.tsbuildinfo
printf 'KEY=main\n' > .env
git worktree add -q "$WT" -b change/a

echo "--- step 2: setup"
python3 "$SCRIPT" setup "$MAIN" "$WT"
[ -f "$WT/docs/architecture.md" ] || fail "document not copied"
for f in out data/big.bin tsconfig.tsbuildinfo .env; do
  [ ! -e "$WT/$f" ] || fail "$f copied"
done

echo "--- step 3: edits on both sides"
printf 'line from worktree\n' >> "$WT/docs/architecture.md"
mkdir "$WT/data"
cp data/big.bin "$WT/data/big.bin"
printf 'x' >> "$WT/data/big.bin"
cp tsconfig.tsbuildinfo "$WT/tsconfig.tsbuildinfo"
printf 'wt\n' >> "$WT/tsconfig.tsbuildinfo"
{ printf 'line from main\n'; cat docs/architecture.md; } > "$DIR/doc" && cp "$DIR/doc" docs/architecture.md
cp docs/architecture.md "$DIR/before-transport"

echo "--- step 4: transport"
OUT="$(python3 "$SCRIPT" transport "$MAIN" "$WT")"
echo "$OUT"
grep -qx 'not transported: data/big.bin, tsconfig.tsbuildinfo' <<<"$OUT" || fail "no not-transported line"
grep -q 'line from main' docs/architecture.md || fail "no MAIN line"
grep -q 'line from worktree' docs/architecture.md || fail "no WORKTREE line"
[ "$(cat tsconfig.tsbuildinfo)" = build ] || fail "tsconfig.tsbuildinfo changed"
[ "$(cat .env)" = KEY=main ] || fail ".env changed"

echo "--- step 5: undo"
python3 "$SCRIPT" undo "$MAIN" "$WT"
cmp docs/architecture.md "$DIR/before-transport" || fail "undo did not restore the document"

echo "scenario passed"
