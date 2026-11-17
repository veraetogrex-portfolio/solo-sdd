# Proposal

## Why

How `sdd-pr.py` waits for CI and what it does around the merge is fixed in code: the wait gives up after 1200 s and polls every 15 s (`global/sdd_pr.py:580`, `:943`), checks stuck for 300 s or absent for 180 s count as failures (`:34-35`), a PR without checks is never merged (`:775`), code scanning alerts always block (`:597-603`), the branch is always deleted after the merge (`:782-787`) and a PR is never a draft (`:457`). A project with a slow CI, no CI, or a review habit on drafts cannot change any of it.

## What Changes

- Keys `delivery.ci-timeout` (1200), `delivery.ci-stuck` (300), `delivery.ci-no-checks` (180): whole seconds; `sdd-pr.py wait` and `ship` take them, a `--timeout` or `--stuck` flag still wins.
- `delivery.require-ci` (`on`, `off`; `on`): `off` lets `merge` and `land` merge a PR that has no checks at all while the base branch requires none, with the line `CI: none` and code 0; a red, pending or missing required check still blocks.
- `delivery.code-scanning` (`gate`, `warn`, `off`; `gate`): `warn` prints the alerts and merges, `off` does not ask for them.
- `delivery.delete-branch` (`on`, `off`; `on`) and `delivery.draft` (`on`, `off`; `off`): keep the branch after the merge; open the PR as a draft and mark it ready right before the merge.
- `skills/ship/SKILL.md` names the settings instead of the fixed 1200 s; `skills/spec-dispatch/merge.md` lands on `none` as on `green` and `report.md` shows it in the CI column.
- Every key is read from the main folder's `solo-sdd/config`; a PR that edits it waits for the owner by `settings-delivery-items`.

## Capabilities

### New Capabilities


### Modified Capabilities
- `settings`: CI wait settings, Merge gate settings, PR shape settings and Delivery settings from the main folder are added.
- `pr-tool`: PR merge, Required checks in CI wait, Ship and land, Land after green and Code scanning in CI wait are modified (the fixed limits, the no-checks refusal, the alert gate and the branch deletion follow the settings).

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `skills/ship/SKILL.md`, `skills/spec-dispatch/merge.md`, `skills/spec-dispatch/report.md`, `tests/test_sdd_pr.py`, `tests/test_skill_commands.py`, `tests/stands/settings-ci-wait.py`

## Out of Scope

- Owner paths and the PR title rule: `settings-delivery-items`.
- A retry count for red CI in `spec-dispatch`: the dispatcher's one return stays fixed; a later change if asked.
- Auto-merge on GitHub: `ship` forbids it and keeps forbidding it.
- The other units of the same plan: `settings-delivery-items`, `settings-local-merge`, `settings-branch-names`, `settings-agent-models`, `settings-change-limits`, `settings-gitignore`, `settings-working-copy`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

settings-delivery-items

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
