#!/usr/bin/env bash
# Стенд живого сценария change dispatch-pipeline: прогон скилла диспетчера /spec-dispatch.
# Проект textkit (Python CLI) со схемой OpenSpec solo и пятью открытыми change:
#   add-words, add-lines, chars-bytes — без зависимостей, первая волна;
#   add-top-words — Depends On: add-words, после его merge;
#   chars-empty — меняет то же требование chars, что chars-bytes: ждёт его merge.
# add-words и add-lines оба дописывают строку в конец раздела «Команды» README.md,
# но ни один не называет README в Impact: план поставит их в одну волну,
# и при merge второго будет конфликт в README.md (намеренно, его решает оркестратор).
# Как в проекте-потребителе, openspec/ и AGENTS.md в .gitignore: лежат в папке, но не в git.
# Флаг --github: раздел «Поставка» в AGENTS.md, workflow CI, шестой change ci-red (тест проходит на
# macOS и падает в CI на Linux из-за регистра имени файла), приватный репозиторий на аккаунте
# владельца, защита main (если тариф позволяет) и ожидание первого прогона CI.
# Флаг --bare-remote: раздела «Поставка» нет, remote — локальный bare-репозиторий <папка>-remote.git рядом со стендом
# (удаляется вместе со стендом руками). Флаг --agents-tracked: то же, и AGENTS.md под git.
# Все пять change дописывают строку в таблицу «Стенды» файла AGENTS.md (ведёт диспетчер).
# solo-sdd и глобальные настройки не меняются; глубина субагентов 2 задаётся только в проекте.
set -euo pipefail

GITHUB=0
BARE_REMOTE=0
TRACKED=0
POS=()
for a in "$@"; do
  case "$a" in
    --github) GITHUB=1 ;;
    --bare-remote) BARE_REMOTE=1 ;;
    --agents-tracked) BARE_REMOTE=1; TRACKED=1 ;;
    *) POS+=("$a") ;;
  esac
done
if [ "$GITHUB" = 1 ] && [ "$BARE_REMOTE" = 1 ]; then
  echo "--github несовместим с --bare-remote и --agents-tracked." >&2
  exit 1
fi
DIR="${POS[0]:-$HOME/Desktop/sdd-dispatch-stand}"

if [ -e "$DIR" ] || { [ "$BARE_REMOTE" = 1 ] && [ -e "$DIR-remote.git" ]; }; then
  echo "Папка $DIR или $DIR-remote.git уже есть. Удали её или передай другой путь первым аргументом." >&2
  exit 1
fi
command -v openspec >/dev/null || { echo "Нет openspec в PATH." >&2; exit 1; }
if [ "$GITHUB" = 1 ]; then
  command -v gh >/dev/null || { echo "Нет gh в PATH." >&2; exit 1; }
fi
if ! openspec schemas 2>/dev/null | grep -q '^ *solo'; then
  echo "Схема solo не установлена (openspec schemas). Запусти python3 ~/.local/bin/openspec-after-update.py --force." >&2
  exit 1
fi

mkdir -p "$DIR"
cd "$DIR"
git init -q -b main
openspec init --tools claude --no-animation . >/dev/null

# ---------------------------------------------------------------- код
mkdir -p textkit/commands tests docs

cat > textkit/__init__.py <<'EOF'
"""textkit: маленькие команды для анализа текстовых файлов."""
EOF

cat > textkit/__main__.py <<'EOF'
import importlib
import pkgutil
import sys

from textkit import commands


def load():
    registry = {}
    for info in pkgutil.iter_modules(commands.__path__):
        module = importlib.import_module(f"textkit.commands.{info.name}")
        registry[module.NAME] = module.run
    return registry


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    registry = load()
    if not argv or argv[0] not in registry:
        print("usage: python3 -m textkit <command> [args]", file=sys.stderr)
        print("commands: " + ", ".join(sorted(registry)), file=sys.stderr)
        return 2
    return registry[argv[0]](argv[1:]) or 0


if __name__ == "__main__":
    sys.exit(main())
EOF

cat > textkit/commands/__init__.py <<'EOF'
"""Каждый модуль пакета — команда: объявляет NAME и run(args) -> int."""
EOF

cat > textkit/commands/chars.py <<'EOF'
import sys

NAME = "chars"


def run(args):
    if len(args) != 1:
        print("usage: python3 -m textkit chars FILE", file=sys.stderr)
        return 1
    try:
        with open(args[0], encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"файл не найден: {args[0]}", file=sys.stderr)
        return 1
    print(len(text))
    return 0
EOF

cat > tests/__init__.py <<'EOF'
EOF

cat > tests/test_chars.py <<'EOF'
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from textkit.__main__ import main


class CharsTest(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_counts_characters(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
            f.write("ёж\n")
        try:
            self.assertEqual(self.run_cli("chars", f.name), (0, "3\n", ""))
        finally:
            os.unlink(f.name)

    def test_missing_file(self):
        code, out, err = self.run_cli("chars", "/nonexistent/file.txt")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("/nonexistent/file.txt", err)

    def test_lists_commands(self):
        code, out, err = self.run_cli()
        self.assertEqual(code, 2)
        self.assertIn("chars", err)


if __name__ == "__main__":
    unittest.main()
EOF

cat > sample.txt <<'EOF'
Зима пришла в город тихо. Листья падали на мокрые улицы, и город стал жёлтым.
Кот сидел у окна и смотрел, как падали листья.

Вечером в городе зажглись фонари, и зима стала тёплой.
EOF

cat > .gitignore <<'EOF'
__pycache__/
openspec/
AGENTS.md
.claude/worktrees/
.claude/hooks.log
.claude/ctx-report.txt
.env
EOF

cat > README.md <<'EOF'
# textkit

Команды для анализа текстовых файлов. Python 3.9+, зависимостей нет.

## Команды

- `python3 -m textkit chars FILE` — число символов

## Примеры

    python3 -m textkit chars sample.txt  # 183
EOF

cat > AGENTS.md <<'EOF'
# textkit

## Назначение и режим

Учебный CLI для анализа текстовых файлов: каждая команда — отдельный модуль в `textkit/commands`.
Режим: demo.

## Источники истины

Контракт — `openspec/specs/`. Активная работа — `openspec/changes/`. README — как запустить.

## Работа по спекам

- За один заход один change, до архива.
- Без уточняющих вопросов: обоснованное решение, запись в отчёт.
- Работа вне текущей спеки оформляется новым change.
- После закрытия `tasks.md` — самостоятельный живой тест до отчёта о готовности.

## Команды

| Что | Команда |
|---|---|
| Установка | не нужна |
| Тесты | `python3 -m unittest discover -s tests -v` |
| Запуск | `python3 -m textkit <command> FILE` |
| Живой прогон | `python3 -m textkit <command> sample.txt` |
| Спеки | `openspec validate --all --strict --no-interactive` |

## Карта проекта

| Путь | Роль |
|---|---|
| `textkit/__main__.py` | Диспетчер: находит команды в `textkit/commands` |
| `textkit/commands/*.py` | Команды: `NAME` и `run(args) -> int` |
| `tests/` | unittest, по файлу на команду |
| `sample.txt` | Текст для живого прогона |

## Границы и инварианты

- Новая команда — новый модуль в `textkit/commands`; диспетчер не правится.
- Только стандартная библиотека Python.
- Ошибка ввода: пустой stdout, сообщение в stderr, код 1.

## Стенды

| Проверка | Команда |
|---|---|
| chars | `python3 -m textkit chars sample.txt` |

## Проверка

Перед «готово»: тесты, `openspec validate --all --strict --no-interactive`, живой прогон команды на `sample.txt`.

## Безопасность

Секретов и платных запросов нет.
EOF

echo "@AGENTS.md" > CLAUDE.md

cat > docs/waiting.md <<'EOF'
# Ожидания

Что не может быть закрыто без внешнего условия. Строка убирается, когда условие выполнено.
У change из этой таблицы в папке лежит файл `WAITING` с одной строкой: чего ждём и ссылка сюда.

| Change | Пункты | Чего ждём | От кого | С какого числа |
| --- | --- | --- | --- | --- |
EOF

# ---------------------------------------------------------------- openspec: конфиг и основные спеки
cat > openspec/config.yaml <<'EOF'
schema: solo

context: |
  Language: ru. Keep OpenSpec structural headings and SHALL/MUST keywords in English.
  Режим: demo
  Замысел: textkit — учебный CLI для анализа текстовых файлов; каждая команда отдельным модулем.
  Успех — команда работает на sample.txt и покрыта тестами, диспетчер при этом не меняется.

operations:
  apply:
    guidance:
      - Тесты и живая приёмка на самых дешёвых моделях
      - Готовность доказывается сценарием в том, что получает человек, а не зелёными модульными тестами
EOF

mkdir -p openspec/specs/cli openspec/specs/chars
cat > openspec/specs/cli/spec.md <<'EOF'
# cli Specification

## Purpose

Точка входа textkit: находит команды в пакете `textkit/commands` и запускает выбранную, чтобы новые команды добавлялись без правки диспетчера.

## Requirements

### Requirement: Command discovery
The CLI SHALL находить команды по модулям пакета `textkit/commands`: каждый модуль объявляет `NAME` и функцию `run(args) -> int`, код возврата которой становится кодом процесса.

#### Scenario: Список команд
- **WHEN** запускается `python3 -m textkit` без аргументов
- **THEN** в stderr выводятся строка usage и список всех команд, код выхода 2

#### Scenario: Запуск команды
- **WHEN** запускается `python3 -m textkit chars sample.txt`
- **THEN** выполняется модуль `chars`, его код возврата становится кодом процесса
EOF

cat > openspec/specs/chars/spec.md <<'EOF'
# chars Specification

## Purpose

Подсчёт символов в текстовом файле: самая простая оценка объёма текста.

## Requirements

### Requirement: Character count command
Команда `chars FILE` SHALL печатать в stdout число символов файла в кодировке UTF-8 и завершаться с кодом 0; если файла нет — пустой stdout, сообщение с именем файла в stderr и код 1.

#### Scenario: Обычный файл
- **WHEN** запускается `python3 -m textkit chars sample.txt`
- **THEN** выводится `183`, код выхода 0

#### Scenario: Файл не найден
- **WHEN** запускается `python3 -m textkit chars нет.txt` для несуществующего файла
- **THEN** stdout пуст, в stderr сообщение с именем файла, код выхода 1
EOF

# ---------------------------------------------------------------- change: add-words
openspec new change add-words >/dev/null
C=openspec/changes/add-words
mkdir -p $C/specs/words
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

Сейчас textkit считает только символы, а для оценки объёма текста нужен подсчёт слов. Разбор текста на слова понадобится и следующим командам, поэтому его стоит сделать общим.

## What Changes

- Новая команда `words FILE`: печатает число слов в файле.
- Функция `tokenize(text)` в `textkit/commands/words.py`: общий разбор текста на слова для других команд.
- Строка о команде в разделе «Команды» README.md.
- Строка проверки в таблицу «Стенды» файла AGENTS.md.

## Capabilities

### New Capabilities
- `words`: подсчёт слов в файле и общее правило, что считается словом

### Modified Capabilities

Нет.

## Impact

- `textkit/commands/words.py`
- `tests/test_words.py`
- `AGENTS.md`

## Out of Scope

- Частотный анализ слов (change `add-top-words`).
- Чтение из stdin и нескольких файлов сразу.

## Depends On

none

## Source

«Добавь команду words: сколько слов в файле. Разбор на слова сделай общим, он понадобится для топа слов. И не забудь строку в README.»
EOF
cat > $C/specs/words/spec.md <<'EOF'
## Purpose

Подсчёт слов в текстовом файле и единое правило разбора текста на слова для всех команд textkit.

## ADDED Requirements

### Requirement: Word tokenization
Функция `tokenize(text)` SHALL возвращать список слов текста, где слово — непрерывная последовательность букв или цифр Unicode, приведённая к нижнему регистру; знаки препинания, подчёркивания и пробелы словами не являются.

#### Scenario: Пунктуация и кириллица
- **WHEN** вызывается `tokenize("Привет, мир! 42")`
- **THEN** возвращается `["привет", "мир", "42"]`

#### Scenario: Пустой текст
- **WHEN** вызывается `tokenize("")`
- **THEN** возвращается пустой список

### Requirement: Word count command
Команда `words FILE` SHALL печатать в stdout одно число — количество слов файла по правилу `tokenize` — и завершаться с кодом 0; если файла нет — пустой stdout, сообщение с именем файла в stderr и код 1.

#### Scenario: Обычный файл
- **WHEN** файл содержит `Привет, мир! 42` и запускается `python3 -m textkit words <файл>`
- **THEN** выводится `3`, код выхода 0

#### Scenario: Файл не найден
- **WHEN** запускается `python3 -m textkit words нет.txt` для несуществующего файла
- **THEN** stdout пуст, в stderr сообщение с именем файла, код выхода 1

### Requirement: Words in README
Раздел «Команды» файла README.md SHALL заканчиваться строкой ``- `python3 -m textkit words FILE` — число слов``.

#### Scenario: Строка в README
- **WHEN** открывается README.md
- **THEN** последняя строка раздела «Команды» — ``- `python3 -m textkit words FILE` — число слов``
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'Привет, мир! 42\n' > /tmp/textkit-words.txt && python3 -m textkit words /tmp/textkit-words.txt` → выводится `3`, код 0.
2. `python3 -m textkit words sample.txt` → выводится `32`.
3. `python3 -m textkit words нет.txt; echo "exit $?"` → сообщение с именем файла в stderr, `exit 1`.
4. `python3 -m textkit` → в списке команд есть `words`.
5. `grep -n 'textkit words' README.md` → строка найдена в разделе «Команды».

## Needs

none

## Fallback

Не требуется: сценарий целиком локальный.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. Разбор и команда words

- [ ] 1.1 `tokenize(text)` в `textkit/commands/words.py` по требованию Word tokenization; проверка — unittest на оба сценария требования
- [ ] 1.2 Команда `words FILE` (`NAME = "words"`, `run(args)`) по требованию Word count command; проверка — unittest на оба сценария, включая код выхода и stderr
- [ ] 1.3 Дописать строку ``- `python3 -m textkit words FILE` — число слов`` в конец раздела «Команды» README.md (после последней строки списка) по требованию Words in README; проверка — `grep -n 'textkit words' README.md`
- [ ] 1.4 Дописать строку ``| words | `python3 -m textkit words sample.txt` |`` в конец таблицы раздела «Стенды» файла AGENTS.md; проверка — `grep -n 'textkit words' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate add-words --strict`, sync delta specs and archive the change with `openspec archive add-words --yes`
EOF

# ---------------------------------------------------------------- change: add-lines
openspec new change add-lines >/dev/null
C=openspec/changes/add-lines
mkdir -p $C/specs/lines
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

Число непустых строк показывает, сколько в тексте абзацев и записей, и это нельзя получить из подсчёта символов. Команда нужна для быстрой оценки структуры файла.

## What Changes

- Функция `count_nonempty(text)` в `textkit/commands/lines.py`: число непустых строк текста.
- Новая команда `lines FILE`: печатает число непустых строк файла.
- Строка о команде в разделе «Команды» README.md.
- Строка проверки в таблицу «Стенды» файла AGENTS.md.

## Capabilities

### New Capabilities
- `lines`: подсчёт непустых строк в файле

### Modified Capabilities

Нет.

## Impact

- `textkit/commands/lines.py`
- `tests/test_lines.py`
- `AGENTS.md`

## Out of Scope

- Подсчёт пустых строк и общего числа строк.
- Чтение из stdin и нескольких файлов сразу.

## Depends On

none

## Source

«Нужна команда lines: сколько в файле непустых строк. Добавь её в README.»
EOF
cat > $C/specs/lines/spec.md <<'EOF'
## Purpose

Подсчёт непустых строк в текстовом файле для оценки его структуры.

## ADDED Requirements

### Requirement: Non-empty line counting
Функция `count_nonempty(text)` SHALL возвращать число строк текста, в которых есть хотя бы один непробельный символ; последняя строка без перевода строки тоже считается.

#### Scenario: Пустые и пробельные строки
- **WHEN** вызывается `count_nonempty("a\n\n  \nb")`
- **THEN** возвращается `2`

### Requirement: Non-empty line count command
Команда `lines FILE` SHALL печатать в stdout число непустых строк файла по правилу `count_nonempty` и завершаться с кодом 0.

#### Scenario: Обычный файл
- **WHEN** файл содержит строки `a`, пустую, строку из двух пробелов и `b` без перевода строки в конце, и запускается `python3 -m textkit lines <файл>`
- **THEN** выводится `2`, код выхода 0

### Requirement: Lines missing file
Если файла нет, команда `lines` SHALL печатать пустой stdout, сообщение с именем файла в stderr и завершаться с кодом 1.

#### Scenario: Файл не найден
- **WHEN** запускается `python3 -m textkit lines нет.txt` для несуществующего файла
- **THEN** stdout пуст, в stderr сообщение с именем файла, код выхода 1

### Requirement: Lines in README
Раздел «Команды» файла README.md SHALL заканчиваться строкой ``- `python3 -m textkit lines FILE` — число непустых строк``.

#### Scenario: Строка в README
- **WHEN** открывается README.md
- **THEN** последняя строка раздела «Команды» — ``- `python3 -m textkit lines FILE` — число непустых строк``
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'a\n\n  \nb' > /tmp/textkit-lines.txt && python3 -m textkit lines /tmp/textkit-lines.txt` → выводится `2`, код 0.
2. `python3 -m textkit lines sample.txt` → выводится `3`.
3. `python3 -m textkit lines нет.txt; echo "exit $?"` → сообщение с именем файла в stderr, `exit 1`.
4. `python3 -m textkit` → в списке команд есть `lines`.
5. `grep -n 'textkit lines' README.md` → строка найдена в разделе «Команды».

## Needs

none

## Fallback

Не требуется: сценарий целиком локальный.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. Команда lines

- [ ] 1.1 Функция `count_nonempty(text)` в `textkit/commands/lines.py` по требованию Non-empty line counting (последняя строка без перевода тоже считается); проверка — unittest
- [ ] 1.2 Команда `lines FILE` (`NAME = "lines"`, `run(args)`) по требованию Non-empty line count command; проверка — unittest на обычный файл
- [ ] 1.3 Ошибка «файл не найден» по требованию Lines missing file: пустой stdout, имя файла в stderr, код 1; проверка — unittest
- [ ] 1.4 Дописать строку ``- `python3 -m textkit lines FILE` — число непустых строк`` в конец раздела «Команды» README.md по требованию Lines in README; проверка — `grep -n 'textkit lines' README.md`
- [ ] 1.5 Дописать строку ``| lines | `python3 -m textkit lines sample.txt` |`` в конец таблицы раздела «Стенды» файла AGENTS.md; проверка — `grep -n 'textkit lines' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate add-lines --strict`, sync delta specs and archive the change with `openspec archive add-lines --yes`
EOF

# ---------------------------------------------------------------- change: chars-bytes
openspec new change chars-bytes >/dev/null
C=openspec/changes/chars-bytes
mkdir -p $C/specs/chars
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

Число символов не равно размеру файла: для кириллицы байт вдвое больше. Для оценки размера нужен режим подсчёта байт.

## What Changes

- Флаг `--bytes` у команды `chars`: печатает число байт файла вместо числа символов.
- Строка проверки в таблицу «Стенды» файла AGENTS.md.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities
- `chars`: требование «Character count command» получает режим `--bytes`

## Impact

- `textkit/commands/chars.py`
- `tests/test_chars_bytes.py`
- `AGENTS.md`

## Out of Scope

- Поведение на пустом и отсутствующем файле (change `chars-empty`).
- Другие кодировки, кроме UTF-8.

## Depends On

none

## Source

«Добавь в chars флаг --bytes: сколько байт в файле.»
EOF
cat > $C/specs/chars/spec.md <<'EOF'
## MODIFIED Requirements

### Requirement: Character count command
Команда `chars [--bytes] FILE` SHALL печатать в stdout число символов файла в кодировке UTF-8, а с флагом `--bytes` — число байт файла, и завершаться с кодом 0; если файла нет — пустой stdout, сообщение с именем файла в stderr и код 1.

#### Scenario: Обычный файл
- **WHEN** запускается `python3 -m textkit chars sample.txt`
- **THEN** выводится `183`, код выхода 0

#### Scenario: Режим байт
- **WHEN** файл содержит `ёж` и запускается `python3 -m textkit chars --bytes <файл>`
- **THEN** выводится `4`, код выхода 0

#### Scenario: Файл не найден
- **WHEN** запускается `python3 -m textkit chars нет.txt` для несуществующего файла
- **THEN** stdout пуст, в stderr сообщение с именем файла, код выхода 1
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'ёж' > /tmp/textkit-bytes.txt && python3 -m textkit chars --bytes /tmp/textkit-bytes.txt` → выводится `4`, код 0.
2. `python3 -m textkit chars /tmp/textkit-bytes.txt` → выводится `2`.
3. `python3 -m textkit chars --bytes нет.txt; echo "exit $?"` → сообщение с именем файла в stderr, `exit 1`.
4. `grep -n 'textkit chars --bytes' AGENTS.md` → строка найдена в таблице «Стенды».

## Needs

none

## Fallback

Не требуется: сценарий целиком локальный.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. Режим --bytes

- [ ] 1.1 Флаг `--bytes` в `textkit/commands/chars.py` по требованию Character count command: число байт файла; проверка — unittest в `tests/test_chars_bytes.py` на сценарий «Режим байт»
- [ ] 1.2 Без флага и при отсутствии файла поведение прежнее; проверка — `python3 -m unittest discover -s tests` (тесты `tests/test_chars.py` проходят)
- [ ] 1.3 Дописать строку ``| chars-bytes | `python3 -m textkit chars --bytes sample.txt` |`` в конец таблицы раздела «Стенды» файла AGENTS.md; проверка — `grep -n 'textkit chars --bytes' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate chars-bytes --strict`, sync delta specs and archive the change with `openspec archive chars-bytes --yes`
EOF

# ---------------------------------------------------------------- change: chars-empty
openspec new change chars-empty >/dev/null
C=openspec/changes/chars-empty
mkdir -p $C/specs/chars
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

Поведение `chars` на пустом файле нигде не зафиксировано и не покрыто тестом: пустой файл должен давать `0`, а не ошибку, и отличаться от отсутствующего файла.

## What Changes

- Чтение файла выносится в `read_text(path)` модуля `textkit/textio.py`: возвращает текст или `None`, если файла нет.
- Требование «Character count command» явно описывает пустой файл: `0` и код 0.
- Строка проверки в таблицу «Стенды» файла AGENTS.md.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities
- `chars`: требование «Character count command» явно описывает пустой файл

## Impact

- `textkit/textio.py`
- `tests/test_chars_empty.py`
- `AGENTS.md`

## Out of Scope

- Режим `--bytes` (change `chars-bytes`).
- Чтение из stdin.

## Depends On

none

## Source

«Проверь chars на пустом файле: должен быть 0 и код 0, а для несуществующего — сообщение и код 1.»
EOF
cat > $C/specs/chars/spec.md <<'EOF'
## MODIFIED Requirements

### Requirement: Character count command
Команда `chars FILE` SHALL печатать в stdout число символов файла в кодировке UTF-8 и завершаться с кодом 0, включая пустой файл, для которого печатается `0`; если файла нет — пустой stdout, сообщение с именем файла в stderr и код 1.

#### Scenario: Обычный файл
- **WHEN** запускается `python3 -m textkit chars sample.txt`
- **THEN** выводится `183`, код выхода 0

#### Scenario: Пустой файл
- **WHEN** файл пуст и запускается `python3 -m textkit chars <файл>`
- **THEN** выводится `0`, код выхода 0

#### Scenario: Файл не найден
- **WHEN** запускается `python3 -m textkit chars нет.txt` для несуществующего файла
- **THEN** stdout пуст, в stderr сообщение с именем файла, код выхода 1
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `: > /tmp/textkit-empty.txt && python3 -m textkit chars /tmp/textkit-empty.txt; echo "exit $?"` → выводится `0`, `exit 0`.
2. `python3 -m textkit chars нет.txt; echo "exit $?"` → сообщение с именем файла в stderr, `exit 1`.
3. `grep -n 'textkit chars /tmp' AGENTS.md` → строка найдена в таблице «Стенды».

## Needs

none

## Fallback

Не требуется: сценарий целиком локальный.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. Пустой файл

- [ ] 1.1 `read_text(path)` в `textkit/textio.py` (текст или `None`, если файла нет); проверка — unittest в `tests/test_chars_empty.py`
- [ ] 1.2 Тесты CLI в `tests/test_chars_empty.py` по требованию Character count command: пустой файл → `0` и код 0, отсутствующий → сообщение и код 1; проверка — `python3 -m unittest discover -s tests`
- [ ] 1.3 Дописать строку ``| chars-empty | `python3 -m textkit chars /tmp/textkit-empty.txt` |`` в конец таблицы раздела «Стенды» файла AGENTS.md; проверка — `grep -n 'textkit-empty' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate chars-empty --strict`, sync delta specs and archive the change with `openspec archive chars-empty --yes`
EOF

# ---------------------------------------------------------------- change: add-top-words
openspec new change add-top-words >/dev/null
C=openspec/changes/add-top-words
mkdir -p $C/specs/top-words
cat > $C/proposal.md <<'EOF'
# Proposal

## Why

По самым частым словам видно, о чём текст, без чтения целиком. Разбор на слова уже будет общим после `add-words`, поэтому команда сводится к подсчёту частот и выводу.

## What Changes

- Новая команда `top N FILE`: печатает N самых частых слов файла с числом повторений.
- Строка проверки в таблицу «Стенды» файла AGENTS.md.

## Capabilities

### New Capabilities
- `top-words`: частотный список слов файла

### Modified Capabilities

Нет.

## Impact

- `textkit/commands/top.py`
- `tests/test_top.py`
- `AGENTS.md`

## Out of Scope

- Стоп-слова и морфология: «город» и «городе» — разные слова.
- Чтение из stdin и нескольких файлов сразу.

## Depends On

add-words

## Source

«Сделай top N: самые частые слова файла, с количеством.»
EOF
cat > $C/specs/top-words/spec.md <<'EOF'
## Purpose

Частотный список слов текстового файла, чтобы быстро понять, о чём текст.

## ADDED Requirements

### Requirement: Top words command
Команда `top N FILE` SHALL печатать N самых частых слов файла по правилу `tokenize` из `textkit/commands/words.py`, по одному на строке в формате `слово<TAB>число`, по убыванию числа, при равном числе — по алфавиту; если различных слов меньше N, печатаются все; код выхода 0.

#### Scenario: Частоты
- **WHEN** файл содержит `кот пёс кот мышь пёс кот` и запускается `python3 -m textkit top 2 <файл>`
- **THEN** выводятся строки `кот<TAB>3` и `пёс<TAB>2`, код выхода 0

#### Scenario: Равные частоты
- **WHEN** файл содержит `b a` и запускается `python3 -m textkit top 5 <файл>`
- **THEN** выводятся строки `a<TAB>1` и `b<TAB>1`, код выхода 0

### Requirement: Top words arguments
Команда `top` SHALL завершаться с кодом 1, пустым stdout и сообщением в stderr, если N не целое положительное число или файла нет.

#### Scenario: Неверное N
- **WHEN** запускается `python3 -m textkit top 0 sample.txt`
- **THEN** stdout пуст, в stderr сообщение об N, код выхода 1

#### Scenario: Файл не найден
- **WHEN** запускается `python3 -m textkit top 3 нет.txt` для несуществующего файла
- **THEN** stdout пуст, в stderr сообщение с именем файла, код выхода 1
EOF
cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'кот пёс кот мышь пёс кот\n' > /tmp/textkit-top.txt && python3 -m textkit top 2 /tmp/textkit-top.txt` → две строки: `кот<TAB>3`, `пёс<TAB>2`.
2. `python3 -m textkit top 3 sample.txt` → три строки: `и<TAB>3`, `в<TAB>2`, `город<TAB>2`.
3. `python3 -m textkit top 0 sample.txt; echo "exit $?"` → сообщение об N в stderr, `exit 1`.
4. `python3 -m textkit` → в списке команд есть `top`.

## Needs

none

## Fallback

Не требуется: сценарий целиком локальный.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
cat > $C/tasks.md <<'EOF'
## 1. Команда top

- [ ] 1.1 Команда `top N FILE` в `textkit/commands/top.py` (`NAME = "top"`, `run(args)`) по требованию Top words command, разбор через `tokenize` из `textkit.commands.words`; проверка — unittest на оба сценария
- [ ] 1.2 Проверка аргументов по требованию Top words arguments; проверка — unittest на оба сценария, включая код выхода и stderr
- [ ] 1.3 Дописать строку ``| top | `python3 -m textkit top 3 sample.txt` |`` в конец таблицы раздела «Стенды» файла AGENTS.md; проверка — `grep -n 'textkit top' AGENTS.md`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate add-top-words --strict`, sync delta specs and archive the change with `openspec archive add-top-words --yes`
EOF

# ---------------------------------------------------------------- наблюдение: хуки, глубина, отчёт о контексте
cat > .claude/log_hook.py <<'EOF'
"""Логгер теста: каждое событие хука одной строкой JSON в .claude/hooks.log.
На Stop и SessionEnd главного агента пересчитывает .claude/ctx-report.txt."""
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "hooks.log")
event = sys.argv[1] if len(sys.argv) > 1 else "?"
try:
    data = json.load(sys.stdin)
except Exception:
    data = {}

rec = {"t": time.strftime("%H:%M:%S"), "event": event, "session": str(data.get("session_id", ""))[:8]}
for k in ("agent_id", "agent_type", "tool_name", "tool_use_id", "stop_hook_active", "source", "reason"):
    if k in data:
        rec[k] = data[k]
if data.get("cwd"):
    rec["cwd"] = os.path.relpath(data["cwd"], os.path.dirname(HERE)) if data["cwd"].startswith(os.path.dirname(HERE)) else data["cwd"]
ti = data.get("tool_input") or {}
tool = data.get("tool_name")
if event == "PreToolUse":
    if tool in ("Agent", "Task"):
        rec["input"] = {k: ti.get(k) for k in ("description", "subagent_type", "model", "isolation", "run_in_background")}
        rec["input"]["prompt_chars"] = len(str(ti.get("prompt", "")))
    elif tool == "SubagentHandback":
        rec["handback"] = json.dumps(ti, ensure_ascii=False)[:2000]
    elif "command" in ti:
        rec["cmd"] = str(ti["command"])[:200]
    elif "file_path" in ti:
        rec["file"] = ti["file_path"]
    elif "skill" in ti:
        rec["skill"] = ti.get("skill")
if event in ("Stop", "SubagentStop"):
    if data.get("background_tasks"):
        rec["background_tasks"] = json.dumps(data["background_tasks"], ensure_ascii=False)[:300]
    if data.get("last_assistant_message"):
        rec["last_message"] = str(data["last_assistant_message"])[:300]
if event in ("SessionStart", "SessionEnd"):
    rec["transcript"] = data.get("transcript_path")

with open(LOG, "a", encoding="utf-8") as f:
    f.write(json.dumps(rec, ensure_ascii=False) + "\n")

if event == "SessionStart":
    print("MARKER-SESSIONSTART-7731: этот текст добавлен SessionStart-хуком тестового проекта.")
if event in ("Stop", "SessionEnd") and not data.get("agent_id") and data.get("transcript_path"):
    subprocess.run([sys.executable, os.path.join(HERE, "ctx_report.py"), data["transcript_path"]],
                   capture_output=True, timeout=30)
EOF

cat > .claude/ctx_report.py <<'EOF'
"""Из чего состоит контекст главного агента: разбор его транскрипта по видам сообщений.
Токены — грубая оценка по символам (символы / 3.5); точный размер контекста — по usage последнего ответа."""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1]
chars = collections.Counter()
count = collections.Counter()
names = {}
last_usage = None


def text_of(x):
    if isinstance(x, str):
        return x
    if isinstance(x, list):
        return "".join(text_of(i.get("text", "") if isinstance(i, dict) else i) for i in x)
    return json.dumps(x, ensure_ascii=False)


def add(key, n):
    chars[key] += n
    count[key] += 1


for line in open(path, encoding="utf-8"):
    try:
        e = json.loads(line)
    except Exception:
        continue
    t = e.get("type")
    msg = e.get("message") or {}
    content = msg.get("content")
    if t == "assistant":
        if msg.get("usage"):
            last_usage = msg["usage"]
        for c in content if isinstance(content, list) else []:
            ct = c.get("type")
            if ct == "text":
                add("ответы: текст", len(c.get("text", "")))
            elif ct == "thinking":
                add("ответы: рассуждения", len(c.get("thinking", "")))
            elif ct == "tool_use":
                names[c.get("id")] = c.get("name")
                add("вызовы: " + str(c.get("name")), len(json.dumps(c.get("input"), ensure_ascii=False)))
    elif t == "user":
        if isinstance(content, str):
            kind = "служебные вставки" if content.lstrip().startswith("<") else "сообщения владельца"
            add(kind, len(content))
        for c in content if isinstance(content, list) else []:
            if c.get("type") == "tool_result":
                add("результаты: " + str(names.get(c.get("tool_use_id"), "?")), len(text_of(c.get("content"))))
            elif c.get("type") == "text":
                txt = c.get("text", "")
                kind = "служебные вставки" if txt.lstrip().startswith("<") else "сообщения владельца"
                add(kind, len(txt))
    else:
        add("прочие записи (" + str(t) + "), не всё идёт в контекст", len(line))

total = sum(v for k, v in chars.items() if not k.startswith("прочие"))
lines = ["Транскрипт: " + path]
if last_usage:
    ctx = sum(last_usage.get(k, 0) for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    lines.append("Контекст на последнем ответе (usage): %d токенов" % ctx)
lines.append("Сообщения сессии: %d символов, ~%d токенов" % (total, total / 3.5))
lines.append("")
lines.append("%-55s %8s %8s %5s" % ("вид", "символы", "~токены", "шт"))
for k, v in chars.most_common():
    lines.append("%-55s %8d %8d %5d" % (k[:55], v, v / 3.5, count[k]))
out = "\n".join(lines) + "\n"
open(os.path.join(HERE, "ctx-report.txt"), "w", encoding="utf-8").write(out)
print(out)
EOF

python3 - <<'EOF'
import json, os
path = ".claude/settings.json"
cfg = json.load(open(path)) if os.path.exists(path) else {}
cfg.setdefault("env", {})["CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"] = "2"
cmd = lambda ev: [{"hooks": [{"type": "command", "command": 'python3 "$CLAUDE_PROJECT_DIR/.claude/log_hook.py" ' + ev}]}]
hooks = cfg.setdefault("hooks", {})
for ev in ("SessionStart", "SubagentStart", "SubagentStop", "Stop", "SessionEnd"):
    hooks.setdefault(ev, []).extend(cmd(ev))
for ev in ("PreToolUse", "PostToolUse"):
    hooks.setdefault(ev, []).append({"matcher": "*", "hooks": cmd(ev)[0]["hooks"]})
json.dump(cfg, open(path, "w"), ensure_ascii=False, indent=2)
EOF

# ---------------------------------------------------------------- проверка стенда и коммит
# шаг 0 spec-next: правила владельца в скиллах OpenSpec этого проекта (до коммита, чтобы worktree их получили)
if [ -f "$HOME/.local/bin/openspec-after-update.py" ]; then
  python3 "$HOME/.local/bin/openspec-after-update.py" | tail -2 || echo "openspec-after-update.py завершился с ошибкой, продолжаю" >&2
fi
VALIDATE_OUT="$(mktemp)"
openspec validate --all --strict --no-interactive >"$VALIDATE_OUT" 2>&1 || {
  cat "$VALIDATE_OUT" >&2
  rm -f "$VALIDATE_OUT"
  echo "Стенд не прошёл openspec validate. Папка оставлена: $DIR" >&2
  exit 1
}
rm -f "$VALIDATE_OUT"
python3 -m unittest discover -s tests -q 2>/dev/null || { echo "Базовые тесты не прошли." >&2; exit 1; }

if [ "$TRACKED" = 1 ]; then
  grep -vx 'AGENTS.md' .gitignore > .gitignore.tmp
  mv .gitignore.tmp .gitignore
fi
git add -A
git commit -qm "textkit: стенд диспетчера"

if [ "$BARE_REMOTE" = 1 ]; then
  BARE="$PWD-remote.git"
  git init -q --bare -b main "$BARE"
  git remote add origin "$BARE"
  git push -qu origin main
  git remote set-head origin main
fi

if [ "$GITHUB" = 1 ]; then
  # ------------------------------------------------------------ --github: локальная часть
  cat >> AGENTS.md <<'EOF'

## Поставка

- Режим: pr
- Merge: squash
- Заголовок PR: первая строка коммита change
- Деплой: нет
EOF

  mkdir -p .github/workflows
  cat > .github/workflows/tests.yml <<'EOF'
name: tests
on:
  pull_request:
  push:
    branches: [main]
jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python3 -m unittest discover -s tests -v
EOF

  openspec new change ci-red >/dev/null
  C=openspec/changes/ci-red
  mkdir -p $C/specs/head
  cat > $C/proposal.md <<'EOF'
# Proposal

## Why

Для беглого взгляда на файл нужны его первые строки. Команда `head` показывает начало файла без чтения целиком.

## What Changes

- Новая команда `head N FILE`: печатает первые N строк файла.
- Тестовая фикстура `tests/data/Sample-Head.txt`.

## Capabilities

### New Capabilities
- `head`: первые N строк файла

### Modified Capabilities

Нет.

## Impact

- `textkit/commands/head.py`
- `tests/test_head.py`
- `tests/data/Sample-Head.txt`

## Out of Scope

- Чтение из stdin и нескольких файлов сразу.
- Отрицательные N.

## Depends On

none

## Source

«Добавь команду head N FILE: первые N строк файла. Тест сделай на готовой фикстуре.»
EOF
  cat > $C/specs/head/spec.md <<'EOF'
## Purpose

Первые строки текстового файла для быстрого просмотра.

## ADDED Requirements

### Requirement: Head command
Команда `head N FILE` SHALL печатать в stdout первые N строк файла и завершаться с кодом 0; если строк меньше N, печатаются все; если N не целое положительное число или файла нет — пустой stdout, сообщение в stderr и код 1.

#### Scenario: Первые строки
- **WHEN** файл содержит строки `a`, `b`, `c` и запускается `python3 -m textkit head 2 <файл>`
- **THEN** выводятся строки `a` и `b`, код выхода 0

#### Scenario: Файл не найден
- **WHEN** запускается `python3 -m textkit head 2 нет.txt` для несуществующего файла
- **THEN** stdout пуст, в stderr сообщение с именем файла, код выхода 1
EOF
  cat > $C/verification.md <<'EOF'
## Live Scenario

1. `printf 'a\nb\nc\n' > /tmp/textkit-head.txt && python3 -m textkit head 2 /tmp/textkit-head.txt` → строки `a`, `b`, код 0.
2. `python3 -m textkit head 2 нет.txt; echo "exit $?"` → сообщение с именем файла в stderr, `exit 1`.
3. `python3 -m textkit` → в списке команд есть `head`.

## Needs

none

## Fallback

Не требуется: сценарий целиком локальный.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
EOF
  cat > $C/tasks.md <<'EOF'
## 1. Команда head

- [ ] 1.1 Команда `head N FILE` в `textkit/commands/head.py` (`NAME = "head"`, `run(args)`) по требованию Head command; фикстуру положить в `tests/data/Sample-Head.txt` (пять строк: `one`, `two`, `three`, `four`, `five`); проверка — `python3 -m textkit head 2 tests/data/Sample-Head.txt`
- [ ] 1.2 Тест `tests/test_head.py`: сценарий «Первые строки» на готовой фикстуре — открыть файл по пути `tests/data/sample-head.txt` (путь из имени команды в нижнем регистре, как у остальных тестов), N=2, ожидаются `one` и `two`; плюс сценарий «Файл не найден»; проверка — `python3 -m unittest discover -s tests`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate ci-red --strict`, sync delta specs and archive the change with `openspec archive ci-red --yes`
EOF
  openspec validate --all --strict --no-interactive >/dev/null 2>&1 || { echo "Стенд с ci-red не прошёл openspec validate. Папка: $DIR" >&2; exit 1; }
  git add -A
  git commit -qm "textkit: CI и поставка через PR"

  # ------------------------------------------------------------ --github: сеть
  OWNER="$(gh api user --jq .login)"
  NAME="sdd-dispatch-stand-$(date +%F)"
  if gh repo view "$OWNER/$NAME" >/dev/null 2>&1; then
    echo "Репозиторий $OWNER/$NAME уже есть. Не перезаписываю: удали его (gh repo delete $OWNER/$NAME) или запусти стенд в другой день." >&2
    exit 1
  fi
  gh repo create "$NAME" --private --source . --remote origin --push
  if echo '{"required_status_checks":{"strict":true,"contexts":[]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}' \
    | gh api -X PUT "repos/$OWNER/$NAME/branches/main/protection" --input - >/dev/null; then
    echo "Защита main включена."
  else
    echo "Предупреждение: защита ветки недоступна на тарифе — продолжаю без неё." >&2
  fi

  RUN_ID=""
  for _ in $(seq 1 30); do
    RUN_ID="$(gh run list --branch main --limit 1 --json databaseId,status,conclusion 2>/dev/null \
      | python3 -c 'import json,sys; r=json.load(sys.stdin); print(r[0]["databaseId"] if r else "")' 2>/dev/null || true)"
    [ -n "$RUN_ID" ] && break
    sleep 10
  done
  [ -n "$RUN_ID" ] || { echo "CI main: за 5 минут не появился ни один прогон." >&2; exit 1; }
  if gh run watch "$RUN_ID" --exit-status >/dev/null 2>&1; then
    echo "CI main: success"
  else
    echo "CI main: failure" >&2
    exit 1
  fi
fi

echo "Готово: $DIR"
echo "  change: $(openspec list --json 2>/dev/null | python3 -c 'import json,sys; print(", ".join(c["name"] for c in json.load(sys.stdin).get("changes", [])))' 2>/dev/null || echo 'см. openspec list')"
echo
echo "Запуск:"
echo "  cd $DIR && claude --model sonnet"
echo "  затем команда /spec-dispatch"
echo "  Лог хуков: $DIR/.claude/hooks.log, отчёт о контексте: $DIR/.claude/ctx-report.txt"
if [ "$GITHUB" = 1 ]; then
  echo
  echo "Репозиторий: https://github.com/$OWNER/$NAME (приватный)."
  echo "Удаляет его владелец: gh repo delete $OWNER/$NAME"
fi
if [ "$BARE_REMOTE" = 1 ]; then
  echo
  echo "Remote: $BARE. Раздела «Поставка» нет; AGENTS.md $([ "$TRACKED" = 1 ] && echo 'под git' || echo 'игнорируется git')."
fi
