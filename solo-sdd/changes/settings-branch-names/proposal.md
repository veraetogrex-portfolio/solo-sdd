# Proposal

## Why

The names the process gives to branches and commits are fixed in many places: `change/<id>` in four scripts and the `spec-dispatch` skill files (`global/sdd_dispatch.py:396`, `global/sdd_pr.py:870`, `global/sdd_dispatch_plan.py:10`, `global/sdd_eval.py:496`, `skills/spec-dispatch/SKILL.md:49`), `plan/<first id>` in `skills/spec-plan/plan-commit.md:5`, and the `light:` commit prefix written by the global rules and read by `work-status`, `report` and `spec-plan`. A team with its own branch convention (`feat/`, a ticket prefix) cannot follow it.

## What Changes

- Keys `delivery.branch-prefix` (default `change/`), `delivery.plan-prefix` (default `plan/`) and `commit.light-prefix` (text, default `light:`).
- Every script and skill that makes or reads these names takes the setting; the defaults keep every name of today.
- `config set`, `config unset` and `solo-sdd settings` refuse a new branch prefix while a local branch of an open change under the old one exists, and name those branches: the dispatcher would no longer see them. Equal branch and plan prefixes, and a prefix git cannot take, are refused.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Branch and commit prefixes and Prefix change guard are added.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `global/sdd_dispatch.py`, `global/sdd_eval.py`, `global/AGENTS.md`, `ALGORITHM.md`, `docs/layout.md`, `solo_sdd/settings_ui.py`, `tests/test_settings_ui.py`, `tests/test_sdd_eval.py`, `skills/spec-dispatch/SKILL.md`, `skills/spec-dispatch/merge.md`, `skills/spec-dispatch/report.md`, `skills/spec-dispatch/orchestrator-prompt.md`, `skills/spec-plan/SKILL.md`, `skills/spec-plan/plan-commit.md`, `skills/work-status/SKILL.md`, `skills/report/SKILL.md`, `tests/test_sdd_dispatch.py`, `tests/test_sdd_dispatch_plan.py`, `tests/test_sdd_pr.py`, `tests/test_skill_commands.py`, `tests/stands/settings-branch-names.py`

## Out of Scope

- The merge method of local delivery: `settings-local-merge`.
- Commit message templates other than the light prefix: the commit subject stays the change's own.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-local-merge`, `settings-agent-models`, `settings-change-limits`, `settings-gitignore`, `settings-working-copy`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

settings-delivery-items, settings-local-merge, settings-ci-wait

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
