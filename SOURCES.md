# Источники

Что взято из чужих систем, что изменено под одного владельца и что сознательно не взято. Сравнение сделано 09.10.2026, дополнено 20.10.2026.

## OpenSpec — основа

[Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec), версия 1.14.0.

**Взято:** основные спеки в `openspec/specs/`, change с delta-спеками (ADDED, MODIFIED, REMOVED), архив, который сам синхронизирует спеки, CLI (`validate`, `archive`, `instructions`).

**Изменено** — схема `solo`, её собирает [schema/openspec-after-update.py](schema/openspec-after-update.py) из штатной `spec-driven` при каждом обновлении OpenSpec:
- в proposal обязательны Out of Scope, Depends On и дословный Source;
- `design.md` необязателен;
- новый артефакт `verification.md` с живым сценарием до кода;
- не больше 10 задач, последняя группа — Acceptance;
- apply идёт без пауз и вопросов, перед первой задачей запускается `spec-analyze`;
- задача на property-тест для требований-инвариантов.

Штатные скиллы OpenSpec получают блок правил владельца.

## GitHub Spec Kit

[github/spec-kit](https://github.com/github/spec-kit), [speckit.org](https://speckit.org/).

**Взято:**
- `/analyze`, сверка артефактов между собой до реализации, стал `spec-analyze`;
- из `/clarify` взята таксономия неясностей, это проход 5 в `spec-analyze`. Вопросы владельцу заменены самостоятельным решением с записью в `Decisions Without Owner`.
- из процесса Bug fixing (Spec Kit 1.1): причина до исправления, ограниченный фикс, записанная проверка. Стал разделом «Багфикс» в `spec-plan`; проверка — сценарий бага в спеке и падающий тест на него.

**Не взято:**
- `/constitution` — его роль играют «Замысел» в `openspec/config.yaml` и «Границы и инварианты» в `AGENTS.md`;
- `/checklist` пересекается с `spec-analyze` и уроками из `LESSONS.md`;
- маркеры `[P]` и группировку задач по user stories заменяет разбиение по владению файлами;
- `quickstart.md` заменён на `verification.md`;
- поддержка Codex CLI в Spec Kit ограничена: аргументы слэш-команд не передаются.
- процесс Idea assessment (go, clarify, stop): его роль играют `evidence-research` и `model-council`;
- workflows, presets, bundles и каталоги: процесс один, и держит его этот репозиторий.

## Kiro: исполняемые свойства и сверка требований

[Does your code match your spec?](https://kiro.dev/blog/property-based-testing/), [Correctness](https://kiro.dev/docs/specs/correctness/).

**Взято:** требование-свойство («для любого»: инвариант, round-trip, идемпотентность) проверяется property-based тестом, названным по Requirement. Это проход 3a в `spec-analyze` и правило в инструкции tasks схемы `solo`.

**Добавлено от себя:** тест обязан падать хотя бы на одной мутации кода, а генератор — доходить до граничных состояний (см. `LESSONS.md`, раздел «Property-based тесты»).

**Взято 20.10.2026** ([Analyze Requirements](https://kiro.dev/docs/specs/analyze-requirements/), [Workflows](https://kiro.dev/blog/introducing-workflows/)):
- поиск требований, верных по отдельности и невыполнимых вместе, по всему набору сразу. В Kiro это делает SMT-решатель после перевода требований в формальную логику; здесь — таблица «условие → поведение» в проходе 7a `spec-analyze`, без решателя;
- ревью в отдельной сессии, которая видит только то, что ей передали, а не рассуждения автора. Стало шагом 7a «Независимая приёмка» в `spec-next`.

**Не взято:** формат требований EARS и связку «требование ↔ тест» в IDE. Связь держится через имя Requirement в названии теста. Графы workflow и память между сессиями — работа самого приложения и памяти агентов, а не процесса.

## GSD 2 (Get Shit Done)

[Обзор](https://discuss.pytorch.kr/t/gsd-2-ai/9436), [release notes](https://releasebot.io/updates/gsd-build/gsd-2).

**Не взято:** GSD 2 — это отдельный CLI, который сам ведёт агентов: свежий контекст на каждую единицу, восстановление после падения, учёт стоимости, worktree. Почти всё это делает само приложение проекта-потребителя, поэтому GSD 2 — кандидат в baseline для сравнения, а не источник для процесса. Бюджетный потолок противоречит Non-Goals проекта-потребителя, где числовых бюджетов у пользователя нет.

**Возможно позже:** детектор зацикливания (повтор одного и того же в скользящем окне → одна попытка диагностики → стоп). Это кандидат в change для проекта-потребителя, а не для процесса.

## Свои наработки

- Скиллы `spec-plan`, `spec-next`, `spec-audit`, `project-init`, `context-resume`, `work-status`, `ship`, `ui-check`, `debug-profile`, `evidence-research`, `agent-quality`, `model-council`, `codex-orchestration`. Глобальные правила `global/AGENTS.md`.
- `opus-sonnet-orchestration` хранится в скиллах аккаунта Claude и синхронизируется оттуда. Здесь он только упоминается.
- `debug-profile` опирается на скилл `systematic-debugging` из superpowers.
- Уроки проекта-потребителя (разборы дефектов и прогонов) обобщены в `LESSONS.md`.
