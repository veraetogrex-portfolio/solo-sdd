# Proposal

## Why

Which model and effort each subagent role gets is fixed in skill text and in one machine-wide policy: orchestrators are `opus` (`skills/spec-dispatch/SKILL.md:3,8,60`), the dispatcher runs at `/effort low` (`:10`), reviewers inherit the main model (`skills/spec-next/acceptance.md:1`), lookups are cheap (`skills/spec-next/SKILL.md:20`), paid product calls in tests use the cheapest (`global/AGENTS.md:73`), and the lists live in `~/.claude/hooks/model-policy.json` for every project at once (`global/work_hooks.py:1043`). Code is written by the lead agent, Codex only when the user names the skill (`global/AGENTS.md:95-96`). A project cannot pick its own models or executor.

## What Changes

- Keys in group `agents`: `agents.orchestrator-model` (default `opus`), `agents.review-model` (default empty: the session's main model), `agents.lookup-model` (default `haiku`), `agents.test-model` (default `haiku`, paid product calls in tests), `agents.dispatcher-effort` (`low`, `medium`, `high`; `low`), `agents.executor` (`self`, `codex`; `self`).
- `spec-dispatch`, `spec-next`, `spec-audit` and the global rules read them through `solo-sdd config get`; `agents.executor: codex` counts as the owner naming `codex-orchestration`, and an agent changes it only on the owner's words.
- The guard hook refuses a launch on a project role model outside the machine policy list of its role (`main` for review and orchestrator, `cheap` for lookup), naming the key and the list: a project can narrow the choice, never widen it. The test model stays bound by the existing test model allowlist. `SOLO_SDD_EXPENSIVE_OK` keeps its meaning.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Subagent model settings, Executor setting from the owner and Project models within the machine policy are added.
- `model-guard`: Models allowed per role and caller names the project refusal.
- `spec-next`: Lead writes code takes `agents.executor`; Reviewer on the main model takes `agents.review-model`.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `global/AGENTS.md`, `ALGORITHM.md`, `skills/spec-dispatch/SKILL.md`, `skills/spec-next/SKILL.md`, `skills/spec-next/acceptance.md`, `skills/spec-audit/SKILL.md`, `tests/test_work_hooks.py`, `tests/test_skill_commands.py`, `tests/stands/settings-agent-models.py`

## Out of Scope

- Editing the machine model lists (`model-policy.json`) from `solo-sdd settings`: they stay one file per machine.
- Turning off the fresh-context reviewer: an independent review stays required by the global rules.
- Codex sandbox modes: stay in `codex-orchestration`.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-local-merge`, `settings-branch-names`, `settings-change-limits`, `settings-gitignore`, `settings-working-copy`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

none

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
