#!/usr/bin/env bash
# Стенд живого сценария change github-publish: первая публикация solo-sdd на клоне текущего коммита.
# Настоящие git и хук pre-push, bare-репозиторий вместо GitHub, подставной gh в PATH.
# Настоящий GitHub и настоящий HOME стенд не трогает: раздел «Установка» README идёт под временным HOME.
# Запуск из корня репозитория: bash tests/stands/publish-first.sh (python3 с Hypothesis в PATH).
# Клонируется HEAD, поэтому стенд видит только закоммиченное.
set -euo pipefail

SRC=$PWD
[ -f "$SRC/scripts/publish-first.sh" ] || { echo "Запусти из корня репозитория solo-sdd." >&2; exit 1; }
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT

ok() { echo "ok: $*"; }
die() { echo "СБОЙ: $*" >&2; exit 1; }

# --- a. клон с историей
git clone -q "$SRC" "$T/repo"
cd "$T/repo"
git checkout -q -B main
git remote remove origin
git branch change/old
deny=$(git -C "$SRC" rev-parse --path-format=absolute --git-common-dir)/info/public-denylist.txt
if [ -f "$deny" ]; then
  mkdir -p .git/info
  cp "$deny" .git/info/public-denylist.txt
fi
ok "клон с историей: main, change/old"

# --- b. подставной gh и c. identity
mkdir "$T/bin"
cat > "$T/bin/gh" <<GH
#!/usr/bin/env bash
case "\$1 \$2" in
  "api user") echo veraetogrex-portfolio ;;
  "repo view") echo "GraphQL: Could not resolve to a Repository with the name 'x'. (repository)" >&2; exit 1 ;;
  "repo create") git init --bare -q "$T/remote.git" && git remote add origin "$T/remote.git" ;;
  "repo edit") exit 0 ;;
  *) echo "gh: неожиданный вызов: \$*" >&2; exit 2 ;;
esac
GH
chmod +x "$T/bin/gh"
export PATH="$T/bin:$PATH"
export GIT_AUTHOR_NAME=stand GIT_AUTHOR_EMAIL=stand@example.invalid
export GIT_COMMITTER_NAME=stand GIT_COMMITTER_EMAIL=stand@example.invalid
export GIT_CONFIG_GLOBAL=/dev/null
ok "подставной gh и identity заданы"

# --- d. пробный запуск
snap() { git branch; git remote; git status --porcelain; git rev-parse HEAD; cat .gitignore; }
before=$(snap)
bash scripts/publish-first.sh > "$T/dry.log" 2>&1 < /dev/null || { cat "$T/dry.log" >&2; die "пробный запуск завершился ошибкой"; }
[ "$before" = "$(snap)" ] || die "пробный запуск изменил ветки, remote, статус, HEAD или .gitignore"
ok "пробный запуск: код 0, ничего не изменилось"

# --- e. --go
bash scripts/publish-first.sh --go > "$T/go.log" 2>&1 < /dev/null || { cat "$T/go.log" >&2; die "--go завершился ошибкой"; }
refs=$(git -C "$T/remote.git" for-each-ref --format='%(refname)' | sort | tr '\n' ' ')
[ "$refs" = "refs/heads/main refs/tags/v0.1.0 " ] || die "в bare не те ссылки: $refs"
[ "$(git rev-list --count main)" = 1 ] || die "в main не один коммит"
block=$(git show main:.gitignore | awk '/^# под одного владельца/{f=1;next} f&&NF&&!/^#/')
[ -n "$block" ] || die "в .gitignore нет блока «под одного владельца»"
for p in openspec docs/waiting.md $block; do
  [ -z "$(git ls-tree -r --name-only main -- "$p")" ] || die "в дереве main есть $p"
done
[ -z "$(git log main -- openspec)" ] || die "git log main -- openspec не пуст"
extra=$(git diff --name-only history-local main | grep -Ev '^(\.gitignore|openspec/.*|docs/waiting\.md)$' || true)
[ -z "$extra" ] || die "main отличается от history-local не только разрешёнными путями: $extra"
[ -d openspec ] && [ -f docs/waiting.md ] || die "openspec/ или docs/waiting.md пропали с диска"
[ -z "$(git status --porcelain)" ] || die "git status не пуст после --go"
ok "--go: один коммит, на remote main и v0.1.0, личное не в дереве, на диске осталось"

# --- f. отказы
reject() {
  local out
  if out=$("$@" 2>&1 < /dev/null); then die "пуш прошёл, а должен быть отклонён: $*"; fi
  printf '%s' "$out" | grep -q 'pre-push: отказ' || die "нет «pre-push: отказ» в выводе: $*"
}
reject git push origin history-local
reject git push origin history-local:refs/heads/x
reject git push origin change/old
git checkout -q -b leak main
mkdir -p openspec/changes/leak
echo x > openspec/changes/leak/note.md
git add -f openspec/changes/leak/note.md
git commit -q -m leak
reject git push origin leak
git checkout -q main
refs=$(git -C "$T/remote.git" for-each-ref --format='%(refname)' | wc -l | tr -d ' ')
[ "$refs" = 2 ] || die "после отказов в bare не две ссылки ($refs)"
ok "хук отклонил history-local, history-local:x, change/old и коммит с openspec"

# --- g. команды CI в свежем клоне
git clone -q "$T/remote.git" "$T/fresh"
cmd=$(awk '/name: Run tests/{f=1;next} f&&/run: \|/{g=1;next} g{print;exit}' "$SRC/.github/workflows/test.yml" | sed 's#/usr/bin/python3#python3#g')
[ -n "$cmd" ] || die "в test.yml не найден шаг Run tests"
if ! (cd "$T/fresh" && bash -c "$cmd" > "$T/t.log" 2>&1); then
  tail -40 "$T/t.log" >&2
  die "тесты CI в свежем клоне упали"
fi
ok "команды CI в свежем клоне: все тесты прошли"

# --- h. README на чистой домашней папке (раскладку на настоящий HOME не выполняем)
mkdir -p "$T/readme" "$T/h"
python3 - "$SRC/README.md" > "$T/install.sh" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
tail = text.split("\n## Установка", 1)[1]
print(re.search(r"```bash\n(.*?)```", tail, re.S).group(1))
PY
grep -q 'https://github.com/veraetogrex-portfolio/solo-sdd' "$T/install.sh" || die "в блоке «Установка» нет адреса GitHub"
(cd "$T/readme" && HOME="$T/h" \
  GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0="url.$T/remote.git.insteadOf" \
  GIT_CONFIG_VALUE_0=https://github.com/veraetogrex-portfolio/solo-sdd \
  bash -eu "$T/install.sh" > "$T/readme.log" 2>&1 < /dev/null) || { tail -30 "$T/readme.log" >&2; die "блок «Установка» завершился ошибкой"; }
[ -s "$T/readme.log" ] || die "блок «Установка» ничего не напечатал"
# git clone пишет «Cloning into» и «done.», push — «создано …» и «всё разложено», status — «ok …»: других строк быть не должно
nok=$(grep -c '^ok ' "$T/readme.log" || true)
ncr=$(grep -c '^создано ' "$T/readme.log" || true)
other=$(grep -Ev '^(ok |создано |всё разложено|Cloning into |done\.)' "$T/readme.log" || true)
[ -z "$other" ] || { echo "$other" >&2; die "в выводе блока «Установка» есть строки, не похожие на ok"; }
{ [ "$nok" -gt 0 ] && [ "$nok" = "$ncr" ]; } || die "строк ok $nok, создано $ncr: ожидалось поровну и больше нуля"
ok "README: установка на чистой домашней папке, $nok строк ok"

echo "стенд пройден"
