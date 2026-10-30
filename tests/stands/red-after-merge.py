#!/usr/bin/env python3
"""Красная проверка диспетчера: добавляет в стенд два change, каждый из которых зелёный в своей ветке,
а после merge обоих тест падает (стык).

Использование: python3 tests/stands/red-after-merge.py <папка стенда>
Стенд — результат dispatch-stand.sh после основного прогона: команда words уже в основной спеке и коде.
openspec/ игнорируется git, поэтому change лежат в папке и не коммитятся."""
import subprocess
import sys
from pathlib import Path

HEADER = "### Requirement: Word count command"
JSON_SCENARIO = """#### Scenario: Режим JSON
- **WHEN** запускается `python3 -m textkit words --json <файл>` для того же файла
- **THEN** выводится `{"words": 3}`, код выхода 0
"""

TAIL = """## Needs

none

## Fallback

Не требуется: сценарий целиком локальный.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
"""
ACCEPT = """## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `openspec validate {id} --strict`, sync delta specs and archive the change with `openspec archive {id} --yes`
"""

JSON = {
    "proposal": """# Proposal

## Why

Скриптам удобнее разбирать вывод `words` как JSON, а человеку понятнее подписанное число. Формат по умолчанию меняется на `words: N`.

## What Changes

- Формат вывода `words` по умолчанию: `words: N` вместо голого числа.
- Флаг `--json`: `words` печатает `{"words": N}`.
- Тесты `tests/test_words.py` переходят на новый формат.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities
- `words`: требование «Word count command» — новый формат вывода и флаг `--json`

## Impact

- `textkit/commands/words.py`
- `tests/test_words.py`
- `tests/test_words_json.py`

## Out of Scope

- Новая команда `report` (change `words-report`).
- JSON для других команд.

## Depends On

none

## Source

«Сделай words --json, а по умолчанию печатай `words: N`.»
""",
    "tasks": """## 1. Формат words

- [ ] 1.1 Формат по умолчанию `words: N` и флаг `--json` в `textkit/commands/words.py` по требованию Word count command; проверка — unittest в `tests/test_words_json.py` на оба сценария
- [ ] 1.2 Обновить `tests/test_words.py` под новый формат (`words: 3` вместо `3`); проверка — `python3 -m unittest discover -s tests` в ветке change зелёный

""" + ACCEPT.format(id="words-json"),
    "verification": """## Live Scenario

1. `printf 'Привет, мир! 42\\n' > /tmp/textkit-wj.txt && python3 -m textkit words /tmp/textkit-wj.txt` → выводится `words: 3`, код 0.
2. `python3 -m textkit words --json /tmp/textkit-wj.txt` → выводится `{"words": 3}`.
3. `python3 -m unittest discover -s tests` → в ветке change зелёный.

Красная проверка диспетчера: после merge этого change вместе с `words-report` падает тест `tests.test_report.ReportTest.test_report_prints_words_line` (ожидает старый формат `3`, а `words` теперь печатает `words: 3`). В ветке этого change тест `report` ещё не существует, поэтому она зелёная.

""" + TAIL,
}

REPORT = {
    "proposal": """# Proposal

## Why

Нужна сводка по файлу одной командой. Для первой версии она показывает строку, которую печатает `words`.

## What Changes

- Новая команда `report FILE`: печатает ту же строку, что `words FILE`.

## Capabilities

### New Capabilities
- `report`: сводка по файлу

### Modified Capabilities

Нет.

## Impact

- `textkit/commands/report.py`
- `tests/test_report.py`

## Out of Scope

- Другие метрики в сводке.
- Правка команды `words` (change `words-json`).

## Depends On

none

## Source

«Сделай report: сводка по файлу, пока только слова — как печатает words.»
""",
    "spec": """## Purpose

Сводка по текстовому файлу одной командой.

## ADDED Requirements

### Requirement: Report command
Команда `report FILE` SHALL печатать в stdout ту же строку, что печатает `words FILE`, и завершаться с кодом возврата `words`.

#### Scenario: Файл со словами
- **WHEN** файл содержит `Привет, мир! 42` и запускается `python3 -m textkit report <файл>`
- **THEN** выводится то же, что печатает `words` для этого файла (в текущем формате — `3`), код выхода 0
""",
    "tasks": """## 1. Команда report

- [ ] 1.1 Команда `report FILE` в `textkit/commands/report.py` (`NAME = "report"`, `run(args)`) по требованию Report command: вызывает `run` команды `words` из реестра `textkit.__main__.load()` и возвращает её код; проверка — unittest
- [ ] 1.2 Тест `tests/test_report.py::ReportTest.test_report_prints_words_line` опирается на текущий формат `words`: ожидает вывод `3` для файла `Привет, мир! 42`; проверка — `python3 -m unittest discover -s tests` в ветке change зелёный

""" + ACCEPT.format(id="words-report"),
    "verification": """## Live Scenario

1. `printf 'Привет, мир! 42\\n' > /tmp/textkit-wr.txt && python3 -m textkit report /tmp/textkit-wr.txt` → выводится `3`, код 0.
2. `python3 -m textkit` → в списке команд есть `report`.
3. `python3 -m unittest discover -s tests` → в ветке change зелёный.

Красная проверка диспетчера: тест `tests.test_report.ReportTest.test_report_prints_words_line` опирается на текущий формат `words` (голое число). После merge этого change вместе с `words-json` команда `words` печатает `words: 3`, и этот тест падает; в ветке этого change он зелёный.

""" + TAIL,
}


def modified_block(spec_text):
    """MODIFIED-блок words-json из текущего блока требования в основной спеке."""
    i = spec_text.index(HEADER)
    j = spec_text.find("\n### Requirement:", i + 1)
    block = spec_text[i:j if j >= 0 else len(spec_text)].strip("\n")
    if "одно число" not in block:
        fail("В требовании «Word count command» нет фразы «одно число»: не знаю, что заменить.")
    old = "- **THEN** выводится `3`, код выхода 0"
    if old not in block:
        fail("В требовании «Word count command» нет сценария с выводом `3`.")
    block = block.replace("одно число", "строку `words: N` (с флагом `--json` — `{\"words\": N}`), где N", 1)
    block = block.replace(old, "- **THEN** выводится `words: 3`, код выхода 0", 1)
    return "## MODIFIED Requirements\n\n" + block + "\n\n" + JSON_SCENARIO


def fail(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main(argv):
    if len(argv) != 1:
        fail("Использование: python3 tests/stands/red-after-merge.py <папка стенда>")
    stand = Path(argv[0]).expanduser()
    changes = stand / "openspec" / "changes"
    if not changes.is_dir():
        fail(f"Стенд не найден: нет {changes}. Создай его: bash tests/stands/dispatch-stand.sh")
    for cid in ("words-json", "words-report"):
        if (changes / cid).exists() or list((changes / "archive").glob(f"*-{cid}")):
            fail(f"В стенде уже есть change {cid}.")
    words_spec = stand / "openspec" / "specs" / "words" / "spec.md"
    words_text = words_spec.read_text(encoding="utf-8") if words_spec.is_file() else ""
    if HEADER not in words_text:
        fail("Команды words нет в основной спеке стенда: сначала прогони основной сценарий (add-words смёрджен и заархивирован).")
    for cid, d, cap in (("words-json", JSON, "words"), ("words-report", REPORT, "report")):
        subprocess.run(["openspec", "new", "change", cid], cwd=stand, check=True, stdout=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
        base = changes / cid
        write(base / "proposal.md", d["proposal"])
        write(base / "specs" / cap / "spec.md", d.get("spec") or modified_block(words_text))
        write(base / "tasks.md", d["tasks"])
        write(base / "verification.md", d["verification"])
    check = subprocess.run(["openspec", "validate", "--all", "--strict", "--no-interactive"], cwd=stand,
                           capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if check.returncode:
        fail(check.stdout + check.stderr + "openspec validate не прошёл.")
    print("Добавлено: words-json, words-report")
    print(f"Дальше: cd {stand} и запусти /spec-dispatch")


main(sys.argv[1:])
