# Proposal

## Why

The `stop` hook blocks the end of a turn for four reasons that a project cannot switch: uncommitted session edits (`global/work_hooks.py:2479-2483`), all tasks checked but not archived (`:2485-2489`), an open PR (`:2492-2500`, only `delivery.merge-by: human` turns it off) and an interface edit without a browser check (`:2503-2505`). Which files count as interface is a fixed list (`:28`), the `ui-check` widths 1280 and 390 are fixed in four skill places (`skills/ui-check/SKILL.md:56`), and a `tasks.md` tick always creates `CLAIM` (`:953-985`).

## What Changes

- Keys in a new group `hooks`: `hooks.stop.uncommitted`, `hooks.stop.unarchived`, `hooks.stop.open-pr`, `hooks.stop.ui-check`, `hooks.auto-claim` (each `on`, `off`; `on`).
- Keys `ui.extensions` (extensions, default the hook's current `.html, .htm, .css, .scss, .sass, .less, .tsx, .jsx, .vue, .svelte`) and `ui.widths` (whole numbers, default `1280, 390`) in group `ui`; a malformed extension or width is refused.
- The hook skips a switched-off gate and lets the stop through, each gate by the settings of the repository it checks; `delivery.merge-by: human` keeps the open PR gate off as today; `hooks.auto-claim: off` only stops creating `CLAIM`, a foreign `CLAIM` or `WAITING` is still refused; a broken config keeps every gate on (fail-open writes `errors.log`, the gates themselves stay).
- `ui-check` and `spec-plan` take the widths, `project-init` the extensions, through `solo-sdd config get`.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Stop gate switches and Interface settings are added.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `skills/ui-check/SKILL.md`, `skills/spec-plan/creation.md`, `skills/spec-plan/SKILL.md`, `skills/project-init/SKILL.md`, `ALGORITHM.md`, `docs/hooks.md`, `docs/stop-conditions.md`, `tests/test_work_hooks.py`, `tests/test_skill_commands.py`, `tests/stands/settings-stop-hooks.py`

## Out of Scope

- The guard hooks (secrets, process stops, models): not switchable per project.
- The context limits of the session start hook: stay fixed.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-local-merge`, `settings-branch-names`, `settings-agent-models`, `settings-change-limits`, `settings-gitignore`, `settings-working-copy`, `settings-project-rules`.

## Depends On

none

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
