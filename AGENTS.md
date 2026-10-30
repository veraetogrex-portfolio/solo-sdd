# solo-sdd

## Назначение и режим

Собственный процесс разработки через спецификации: алгоритм, скиллы, глобальные правила агентов, хуки Claude Code, сборка схемы `solo` и шаблоны проектов. Репозиторий — источник истины; по местам файлы раскладывает `sync.py push`.
Режим: prod. Прод здесь — папки агентов на этом компьютере (`~/.claude`, `~/.codex`, `~/.agents`, `~/.local/bin`): после `sync.py push` правка сразу действует во всех сессиях.

## Источники истины

- Контракт поведения — `openspec/specs/`; активная работа — `openspec/changes/`.
- Алгоритм — `ALGORITHM.md`; уроки, из которых выросли правила, — `LESSONS.md`.
- `README.md` — что где лежит и как раскладывается. `targets.json` — карта раскладки.
- Скопированные в папки агентов файлы — не источник: правка на месте забирается `sync.py pull`.
- После первой публикации `openspec/` и `docs/waiting.md` в git не входят, лежат только в рабочей папке.

## Работа по спекам

- За один заход один change, до архива.
- Без уточняющих вопросов: обоснованное решение, запись в отчёт.
- Работа вне текущей спеки оформляется новым change.
- После закрытия `tasks.md` — самостоятельный живой тест до отчёта о готовности.

## Команды

| Что | Команда |
|---|---|
| Установка | Python 3 из системы; для тестов — `python3 -m pip install --user hypothesis` |
| Тесты | `python3 tests/test_sync.py && python3 schema/test_openspec_after_update.py && python3 tests/test_process_guard.py && python3 tests/test_work_hooks.py && python3 tests/test_public_tree.py && python3 tests/test_sdd_worktree.py && python3 tests/test_sdd_dispatch_plan.py && python3 tests/test_sdd_pr.py && python3 tests/test_publish_first.py` |
| Что разложено и где расходится | `python3 sync.py status` |
| Раскладка | `python3 sync.py push` |
| Спеки | `openspec validate --all --strict --no-interactive` |

## Карта проекта

| Путь | Роль |
|---|---|
| `skills/<имя>/SKILL.md` | Скиллы алгоритма и ручные команды; раскладываются по `targets.json` |
| `global/AGENTS.md` | Глобальные правила обоих агентов |
| `global/work_hooks.py`, `global/model-policy.json` | Хуки рабочего процесса Claude Code и политика моделей |
| `global/work_hooks_settings.py` | Разовое подключение хуков в `~/.claude/settings.json` |
| `global/process-guard.py` | Хук запрета прямой остановки процессов |
| `schema/openspec-after-update.py` | Сборка схемы `solo`, правила владельца в скиллах OpenSpec, вызов `sync.py push` |
| `templates/` | Шаблоны для новых проектов |
| `openspec/` | Спеки и change этого репозитория |
| `scripts/publish-first.sh` | Первая публикация: новая `main` без истории и без `openspec/`, разовый |
| `.github/workflows/test.yml` | CI на всех тестах дерева |
| `tests/` | Тесты и пробы; `tests/stands/` — стенды живых сценариев |

## Рабочая копия

- Пути: `docs/waiting.md`, `docs/debug-profile.md`, `docs/process-safety-verification.md`, `global/claude-gui.py`, `global/claude-process-safety-settings.json`, `global/claude-safe.py`, `skills/model-council/`, `tests/probe_claude_development.py`, `tests/probe_claude_process_safety.py`, `tests/test_claude_gui.py`, `tests/test_claude_safe.py`

## Границы и инварианты

- Правка — только здесь, затем `sync.py push`. Файлы в папках агентов руками не правятся.
- `sync.py push` не затирает копию, изменённую на месте (`drift`); перед перезаписью сохраняет прежний текст в `~/.local/share/solo-sdd/backup/`.
- Хуки работают по принципу fail-open: внутренняя ошибка пропускает действие и пишется в `~/.claude/hook-state/errors.log`.
- Скиллы и правила пишутся по-русски; структурные заголовки OpenSpec и SHALL/MUST — по-английски.

## Проверка

Перед «готово»: все тесты из таблицы, `openspec validate --all --strict --no-interactive`, `python3 sync.py status` без неожиданных `drift`, живой сценарий change.

## Поставка

- Режим: pr
- Merge: squash
- Заголовок PR: имя change
- Деплой: нет — раскладка по папкам агентов делается отдельно (`sync.py push`).

## Безопасность

- Платные вызовы моделей в тестах — только самые дешёвые (`global/model-policy.json`).
- `sync.py push` меняет рабочие папки агентов на этом компьютере: это действие на проде, после него проверь `sync.py status`.
- Секретов в репозитории нет и не должно быть.
