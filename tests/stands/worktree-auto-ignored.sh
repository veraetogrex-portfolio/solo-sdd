#!/usr/bin/env bash
# Стенд живого сценария change worktree-auto-ignored: шаги 1–5 на настоящем запуске sdd_worktree.py.
# Свой проект и worktree во временной папке; sync.py push не вызывается.
# Запуск из корня репозитория: bash tests/stands/worktree-auto-ignored.sh
set -euo pipefail

SCRIPT="$(cd "$(dirname "$0")/../.." && pwd)/global/sdd_worktree.py"
DIR="$(mktemp -d "${TMPDIR:-/tmp}/auto-ignored-XXXXXX")"
trap 'rm -rf "$DIR"' EXIT
MAIN="$DIR/main"
WT="$DIR/wt-a"

fail() { echo "ПРОВАЛ: $1" >&2; exit 1; }

echo "--- шаг 1: проект"
git init -q -b main "$MAIN"
cd "$MAIN"
mkdir docs out data
printf 'docs/architecture.md\nout/\ndata/big.bin\ntsconfig.tsbuildinfo\n.env\n' > .gitignore
printf 'заметки\n' > docs/notes.md
printf '# P\n' > AGENTS.md
git add -A
git -c user.name=t -c user.email=t@t commit -qm init
printf 'строка 1\nстрока 2\n' > docs/architecture.md
printf 'x\n' > out/app.js
head -c 2097152 /dev/zero > data/big.bin
printf 'build\n' > tsconfig.tsbuildinfo
printf 'KEY=main\n' > .env
git worktree add -q "$WT" -b change/a

echo "--- шаг 2: setup"
python3 "$SCRIPT" setup "$MAIN" "$WT"
[ -f "$WT/docs/architecture.md" ] || fail "документ не скопирован"
for f in out data/big.bin tsconfig.tsbuildinfo .env; do
  [ ! -e "$WT/$f" ] || fail "скопирован $f"
done

echo "--- шаг 3: правки с двух сторон"
printf 'строка из worktree\n' >> "$WT/docs/architecture.md"
mkdir "$WT/data"
cp data/big.bin "$WT/data/big.bin"
printf 'x' >> "$WT/data/big.bin"
cp tsconfig.tsbuildinfo "$WT/tsconfig.tsbuildinfo"
printf 'wt\n' >> "$WT/tsconfig.tsbuildinfo"
{ printf 'строка из main\n'; cat docs/architecture.md; } > "$DIR/doc" && cp "$DIR/doc" docs/architecture.md
cp docs/architecture.md "$DIR/before-transport"

echo "--- шаг 4: transport"
OUT="$(python3 "$SCRIPT" transport "$MAIN" "$WT")"
echo "$OUT"
grep -qx 'не перенесены: data/big.bin, tsconfig.tsbuildinfo' <<<"$OUT" || fail "нет строки не перенесены"
grep -q 'строка из main' docs/architecture.md || fail "нет строки MAIN"
grep -q 'строка из worktree' docs/architecture.md || fail "нет строки WORKTREE"
[ "$(cat tsconfig.tsbuildinfo)" = build ] || fail "tsconfig.tsbuildinfo изменён"
[ "$(cat .env)" = KEY=main ] || fail ".env изменён"

echo "--- шаг 5: undo"
python3 "$SCRIPT" undo "$MAIN" "$WT"
cmp docs/architecture.md "$DIR/before-transport" || fail "undo не вернул документ"

echo "сценарий пройден"
