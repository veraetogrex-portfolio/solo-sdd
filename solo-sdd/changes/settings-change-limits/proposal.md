# Proposal

## Why

The size and rhythm of a change are fixed: at most 10 tasks (`solo_sdd/process_format.py:10`, enforced by `validate`, repeated in `skills/spec-plan/SKILL.md:20`, `skills/spec-analyze/SKILL.md:29`, `ALGORITHM.md:10`), 5 for a bug fix (`skills/spec-plan/SKILL.md:78`), 500 characters per requirement (`solo_sdd/process_format.py:9`), an audit after every 5 archives (`skills/spec-next/SKILL.md:98`), and `spec-analyze` always runs before code (`skills/spec-next/SKILL.md:19`). A project with larger or smaller units cannot set its own bounds.

## What Changes

- Keys in group `process`: `process.max-tasks` (10), `process.bugfix-max-tasks` (5), `process.requirement-max-chars` (500), `process.audit-every` (5), `process.analyze` (`on`, `off`; `on`).
- `solo-sdd validate` takes the task and requirement limits from the project's settings and names the limit and its source in the error.
- `spec-plan`, `spec-analyze`, `spec-next` and `ALGORITHM.md` read the values through `solo-sdd config get`; `process.analyze: off` skips the `spec-analyze` pass and the report says so. An agent changes these keys only on the owner's words; `config set` refuses a task limit below 3 and a length below 100.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Change size limits and Process cadence settings are added.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `solo_sdd/process_format.py`, `ALGORITHM.md`, `skills/spec-plan/SKILL.md`, `skills/spec-plan/creation.md`, `skills/spec-analyze/SKILL.md`, `skills/spec-next/SKILL.md`, `tests/test_process_format.py`, `tests/test_skill_commands.py`, `tests/stands/settings-change-limits.py`

## Out of Scope

- Turning off the independent review or the live check: they are what readiness means here.
- Review rounds: `process.review-rounds` already exists.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-local-merge`, `settings-branch-names`, `settings-agent-models`, `settings-gitignore`, `settings-working-copy`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

none

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
