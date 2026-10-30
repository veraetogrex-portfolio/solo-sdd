# solo-sdd

Процесс разработки через спецификации для тех, кто ведёт проект вдвоём с ИИ-агентами (Claude Code и Codex): OpenSpec со схемой `solo`, скиллы, глобальные правила агентов, хуки и шаблоны для новых проектов. `sync.py` раскладывает всё это по папкам агентов.

## Требования

- Python 3.9+, Node 20+, [OpenSpec](https://github.com/Fission-AI/OpenSpec) 1.14+, git.
- Claude Code и/или Codex.

Отдельные скиллы пользуются дополнительным (всё необязательно, нужно только для своего скилла):

- `gh` (GitHub CLI) — режим `pr` у `spec-dispatch` и `sdd_pr.py`, PR в `ship`;
- `codex` (Codex CLI) — `codex-orchestration`;
- superpowers (скилл `systematic-debugging`) — `debug-profile`, `relay`;
- браузер для автоматизации — `ui-check`;
- `docker compose` — `health` и `debug-profile`, если проект запускается через него;
- Obsidian — необязательный источник памяти в `context-resume`;
- `opus-sonnet-orchestration` — необязательный скилл (см. «Чего здесь нет»).

## Установка

Первая раскладка заменяет целиком существующие `~/.claude/CLAUDE.md`, `~/.codex/AGENTS.md` и `~/AGENTS.md`. Прежний текст лежит только в `~/.local/share/solo-sdd/backup/`. Если там есть ваши правила, сначала сохраните их или попробуйте на временной домашней папке (`sync.py` берёт её из `HOME`):

```bash
git clone https://github.com/veraetogrex-portfolio/solo-sdd
cd solo-sdd
T=$(mktemp -d)
HOME="$T" python3 sync.py push
HOME="$T" python3 sync.py status
```

Все строки `status` должны быть `ok`. Затем настоящая раскладка:

```bash
cd solo-sdd
python3 sync.py push
```

Хуки Claude Code подключаются отдельно, один раз:

```bash
cd solo-sdd
python3 global/work_hooks_settings.py
```

Скрипт дописывает существующий `~/.claude/settings.json`: файла ещё нет — создайте его с содержимым `{}`. Кроме хуков он добавляет `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` и правило `autoMode.allow` (см. «Что и куда ставится»).

## Что и куда ставится

Карта раскладки — `targets.json`. Скиллов 19: 14 алгоритма и 5 ручных команд (`relay`, `blockers`, `report`, `health`, `changes`).

| Что | Куда |
|---|---|
| `skills/<имя>/SKILL.md`: `spec-plan`, `spec-analyze`, `spec-next`, `spec-audit`, `project-init`, `context-resume`, `work-status`, `ship`, `ui-check`, `debug-profile`, `evidence-research`, `agent-quality`, `relay`, `blockers`, `report`, `health`, `changes` | `~/.agents/skills`, `~/.codex/skills`, `~/.claude/skills` |
| `skills/codex-orchestration/SKILL.md` | `~/.agents/skills`, `~/.claude/skills` |
| `skills/spec-dispatch/SKILL.md` (раздача change Opus-оркестраторам, только Claude Code) | `~/.claude/skills` |
| `global/AGENTS.md` (глобальные правила обоих агентов) | `~/AGENTS.md`, `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md` |
| `global/process-guard.py` (хук запрета прямой остановки процессов) | `~/.claude/hooks/process-guard.py` |
| `global/work_hooks.py`, `global/model-policy.json` (хуки рабочего процесса и политика моделей) | `~/.claude/hooks/` |
| `global/sdd_worktree.py` (Подготовка worktree для `spec-dispatch`: `setup` копирует игнорируемые git `openspec/`, `AGENTS.md` и пути раздела «Рабочая копия», ставит ссылки на `node_modules` и `.venv`; `transport` переносит их обратно трёхсторонним слиянием, `undo` отменяет перенос, `remove` убирает worktree, `discard` убирает worktree без своих коммитов вместе с веткой после неудачной подготовки) | `~/.local/bin/sdd-worktree.py` |
| `global/sdd_dispatch_plan.py` (Очередь для `spec-dispatch`: считает готовые открытые change (нет `CLAIM`, `WAITING`, ветки `change/<id>`, папка change закоммичена, зависимости в архиве), порядок по критическому пути и жёсткие конфликты по требованиям и файлам `Impact`, кроме общих путей; выдаёт, кого запустить, кто ждёт и какие пары идут вместе при общем пути; печатает, какие из `openspec/`, `AGENTS.md`, `CLAUDE.md` игнорируются git) | `~/.local/bin/sdd-dispatch-plan.py` |
| `global/sdd_pr.py` (PR для `spec-dispatch`: `open` пушит ветку worktree и открывает PR (или берёт уже открытый), `wait` ждёт CI и отвечает `green`, `red` или `infra` с хвостом журнала, `merge` сливает PR запросом REST API по хешу проверенного коммита после сверки проверок) | `~/.local/bin/sdd-pr.py` |
| `schema/openspec-after-update.py` (сборка схемы `solo`, правила в скиллах OpenSpec, вызов `sync.py`) | `~/.local/bin/openspec-after-update.py` |
| `schema/test_openspec_after_update.py` (его тест) | `~/.local/bin/test_openspec_after_update.py` |

Вручную запускается `global/work_hooks_settings.py`: он подключает хуки в `~/.claude/settings.json` и ставит глубину субагентов 2 (`env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`; заданное вами значение не меняет), а в `autoMode.allow` держит одно правило о merge своих PR (`sdd-pr.py merge`, `land`, `gh pr merge` из `/ship`) и обновлении ветки change: повторный запуск заменяет его по постоянному префиксу. `sync.py` настройки не трогает.

Не раскладываются, лежат в репозитории: `templates/` (`openspec/config.yaml`, `openspec/analyze.md`, `docs/waiting.md`, `DESIGN.md` для нового проекта; копируются вручную или скиллом `project-init`), `tests/` (`tests/stands/` — стенды живых сценариев), `scripts/publish-first.sh` (первая публикация, разовый), `.github/workflows/test.yml` (CI). `AGENTS.md` и `CLAUDE.md` в корне — внутренняя работа над самим solo-sdd; `openspec/` и `docs/waiting.md` лежат только в рабочей папке автора и в репозиторий не входят.

## Первый шаг в проекте

В папке своего проекта запустите `/project-init`, затем `/spec-plan` (план в очередь маленьких change) и `/spec-next` (реализация change от выбора до архива).

Алгоритм целиком — [ALGORITHM.md](ALGORITHM.md). Уроки, из которых выросли правила, — [LESSONS.md](LESSONS.md). Что взято у OpenSpec, Spec Kit, Kiro и GSD 2 и что нет — [SOURCES.md](SOURCES.md).

## Как обновлять раскладку

Правка скилла или правил — в репозитории, затем раскладка:

```bash
cd solo-sdd
python3 sync.py status
python3 sync.py push
```

`push` не затирает копию, которую правили на месте после прошлой раскладки (например, Codex дописал скилл прямо в `~/.codex/skills`). Такая копия помечается `drift` и пропускается. Забрать правку в репозиторий:

```bash
cd solo-sdd
python3 sync.py pull spec-next
git diff
python3 sync.py push
```

Если копии в разных папках правили по-разному, `pull` попросит указать источник: `--from ~/.codex/skills`. `push --force` перезаписывает и правки на месте. Перед любой перезаписью прежний текст сохраняется в `~/.local/share/solo-sdd/backup/`.

Раскладку делает и сам процесс: шаг 0 скилла `spec-next` запускает `openspec-after-update.py`, а тот — `sync.py push`.

## Проверка

```bash
cd solo-sdd
python3 -m pip install --user hypothesis
python3 tests/test_sync.py
python3 schema/test_openspec_after_update.py
python3 tests/test_process_guard.py
python3 tests/test_work_hooks.py
python3 tests/test_sdd_worktree.py
python3 tests/test_sdd_dispatch_plan.py
python3 tests/test_sdd_pr.py
python3 tests/test_public_tree.py
```

## Хуки рабочего процесса Claude Code

Хуки закрывают самые частые повторы в работе с агентом: чтение правил проекта, продолжение, архив, мёрдж, статус. Один скрипт `global/work_hooks.py`, подкоманды:

| Подкоманда | Событие | Что делает |
|---|---|---|
| `context` | SessionStart | Кладёт в контекст AGENTS.md, `openspec/config.yaml`, `docs/status.md`, ветку, `git status`, change с прогрессом и метками CLAIM/WAITING |
| `guard` | PreToolUse | Блокирует вывод `.env` и секретных переменных, перезапись `.env`, второй `.env`, `git add` секретов; модели субагентов по тегу роли в начале `description` (`model-policy.json`: `Review:`/`Ревью:` — ревью, `Orchestrator` — оркестратор, `Implement:`/`Исполнитель:` — исполнитель; слова без тега роль не задают): приёмка и ревью — только дешёвые, оркестратор — только из главной сессии, исполнитель из субагента — с явной недорогой моделью; дорогие модели в тестах Bash; обход разрешает владелец через `SOLO_SDD_EXPENSIVE_OK=1` в окружении, а запись этой переменной в настройки и профиль оболочки агенту запрещена; правку чужого change по CLAIM и change с WAITING; worktree вне временной папки, в том числе встроенные: `claude --worktree`, `codex --worktree`, `EnterWorktree` с новым именем, `isolation: worktree` у субагента; первую запись вне проекта; те же правила тела heredoc и шаблона поиска, что у `process-guard`, в проверках секретов и моделей в Bash; сдачу статуса оркестратора (`SubagentHandback` с блоком `STATUS:`; код выхода в `VALIDATE` и `TESTS` допускает пояснение: `-> exit 0 (250 tests)`), если поля, коммит `HEAD`, архив change или снятый CLAIM не сходятся с git и файлами |
| `subagent-context` | SubagentStart | Даёт субагенту путь к `AGENTS.md` основной папки и открытые change с метками CLAIM/WAITING, не длиннее 4000 знаков |
| `stop` | Stop | Пока у сессии есть фоновые задачи `running`, молчит. Иначе один раз возвращает агента, если остались незакоммиченные правки этой сессии, готовый change не в архиве, открыт несмёрдженный PR, интерфейс не проверен в браузере (засчитывается проверка любого субагента сессии по его транскрипту в `<id>/subagents/`) или ответ не на русском |
| `beat`, `status` | все события, строка статуса | Текущее действие, время, число субагентов |
| `end` | SessionEnd | Снимает CLAIM, которые поставил хук |

Внутренняя ошибка пропускает действие и пишется в `~/.claude/hook-state/errors.log`. Подключение в настройках делается один раз: `python3 global/work_hooks_settings.py` (сохраняет резервную копию, повторный запуск записи не дублирует). Хуки работают только в Claude Code: у Codex другой механизм хуков.

## Защита процессов Claude Code

`sync.py push` кладёт хук `global/process-guard.py` в `~/.claude/hooks/`. В `~/.claude/settings.json` он подключается вручную: хук PreToolUse на `Bash|Monitor` и deny-правила для `pkill`, `killall`, `kill`, `osascript`, `launchctl`, `shutdown` (`work_hooks_settings.py` их не добавляет). Команда хука: `exec /usr/bin/python3 "$HOME/.claude/hooks/process-guard.py"`, `timeout: 5`, `onFailure: "block"`. Хук проверяет текст команды, включая обычные обёртки и подстановки; тело heredoc, которое уходит не в оболочку (`cat > f <<'EOF'`, `python3 - <<'EOF'`), и шаблон поиска `grep`/`rg`/`git grep`/`ag` командой не считаются, а тело для любого другого получателя (оболочка, оболочка за обёрткой, незнакомая программа, в том числе через `|`) проверяется; содержимое запускаемых программ и вычисляемые имена не анализирует. Это защита от случайных прямых команд, а не изоляция процессов на уровне ОС.

## Чего здесь нет

- `opus-sonnet-orchestration`, `model-council` и `demo-brief` в репозиторий не входят, хотя правила и скиллы на них ссылаются: `spec-next` в Claude Code по умолчанию ведёт реализацию через первый, `ALGORITHM.md` предлагает второй для спорных решений. Скилла нет — агент выполняет этот шаг сам.
- Скиллы конкретного проекта лежат в самом проекте.
- Скиллы, не относящиеся к разработке, остаются в папках агентов, `sync.py` их не трогает.
