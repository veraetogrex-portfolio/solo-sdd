#!/usr/bin/env bash
# Стенд живого сценария change plan-stale-claim: шаги 1–3 на настоящем запуске sdd_dispatch_plan.py.
# Свой проект с тремя change-заглушками и временный HOME: настоящие change и hook-state не участвуют,
# dispatch-stand.sh здесь не годится: он вызывает openspec-after-update.py, то есть sync.py push.
# Запуск из корня репозитория: bash tests/stands/plan-stale-claim.sh
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
echo "claude 2026-10-21 session=deadbeef-0000" > openspec/changes/a-stale/CLAIM
echo "claude 2026-10-21 session=deadbeef-0000" > openspec/changes/b-stale/CLAIM
echo "claude 2026-10-21 session=live0000-0000" > openspec/changes/c-live/CLAIM
touch "$HOME/.claude/hook-state/live0000-0000.json"

want() {
  case "$OUT" in
    *"$1"*) ;;
    *) echo "НЕТ строки: $1" >&2; exit 1 ;;
  esac
}

echo "--- шаг 2: две брошенные, одна живая"
OUT="$(python3 "$SCRIPT" .)"
echo "$OUT" | grep ' — '
want "a-stale — CLAIM брошен: сессия deadbeef молчит"
want "b-stale — CLAIM брошен: сессия deadbeef молчит"
want "c-live — CLAIM"
case "$OUT" in *"c-live — CLAIM брошен"*) echo "живая метка брошена" >&2; exit 1 ;; esac
git branch change/a-stale
echo "--- шаг 3: ветка важнее метки"
OUT="$(python3 "$SCRIPT" .)"
echo "$OUT" | grep ' — '
want "a-stale — не смёрджен: ветка change/a-stale"
git branch -D -q change/a-stale
LEFT="$(find openspec -name CLAIM | wc -l | tr -d ' ')"
[ "$LEFT" = 3 ] || { echo "метки сняты: осталось $LEFT" >&2; exit 1; }
echo "--- метки на месте: $LEFT из 3"
