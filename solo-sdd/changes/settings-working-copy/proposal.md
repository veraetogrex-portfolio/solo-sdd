# Proposal

## Why

How a worktree is prepared for an orchestrator lives in prose items of the AGENTS.md section "Working copy": "Paths:", "Prepare:", "After refresh:", "Shared:" and "Loopback: needed" (`global/sdd_worktree.py:372-376`, `global/sdd_dispatch_plan.py:31,44`), while the linked folders `node_modules`, `.venv` (`global/sdd_worktree.py:54`) and the 600 s check timeout (`global/sdd_dispatch.py:21`, only the `SDD_DISPATCH_TIMEOUT` variable) are fixed in code. `project-init` still computes the test thread split from the old "Orchestrators:" item (`skills/project-init/SKILL.md:83`), not from `dispatch.limit`.

## What Changes

- Keys `worktree.paths` (paths), `worktree.prepare` and `worktree.after-refresh` (text), `worktree.links` (paths, default `node_modules, .venv`), `dispatch.shared` (paths), `dispatch.loopback` (`on`, `off`; `off`), `dispatch.check-timeout` (int, 600); without a file value each takes its "Working copy" item ("Loopback: needed" also from "Commands"), source `AGENTS.md`; `dispatch.limit` takes the "Orchestrators:" item the same way, so `config get` and the dispatch plan agree. An item value the key refuses is named on stderr and not taken. A `worktree.links` item other than `node_modules` is linked at its path from the root.
- `sdd-worktree.py`, `sdd-dispatch-plan.py` and `sdd-dispatch.py` read them; `SDD_DISPATCH_TIMEOUT` still wins over `dispatch.check-timeout`.
- `project-init` divides the cores by `dispatch.limit` and writes new working copy values with `solo-sdd config set` instead of a new "Working copy" section.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: Working copy settings and Working copy items as the old source are added.
- `project-init`: Test command under dispatcher is modified (N is `dispatch.limit`); Working copy values in the settings is added.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `global/sdd_dispatch.py`, `skills/project-init/SKILL.md`, `skills/spec-dispatch/SKILL.md`, `tests/test_sdd_worktree.py`, `tests/test_sdd_dispatch_plan.py`, `tests/test_sdd_dispatch.py`, `tests/test_skill_commands.py`, `tests/stands/settings-working-copy.py`

## Out of Scope

- The `text` settings kind: `settings-delivery-items`.
- The copied document extensions and their 1 MiB limit: stay fixed.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-local-merge`, `settings-branch-names`, `settings-agent-models`, `settings-change-limits`, `settings-gitignore`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

settings-delivery-items

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
