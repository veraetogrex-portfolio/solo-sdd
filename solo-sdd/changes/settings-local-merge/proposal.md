# Proposal

## Why

Under `delivery.mode: local` the change branch is always merged with `git merge --no-ff --no-edit` (`global/sdd_dispatch.py:433`, requirement Local land command of `dispatch-tool`), while the description of `delivery.merge` says it covers "a pull request or a local change" (`solo_sdd/settings.py` ABOUT). A solo owner who wants a linear main or one commit per change in local mode has no way to get it. Switching land-local to `delivery.merge` itself would change every existing local project, because that key defaults to `squash`.

## What Changes

- A key `delivery.local-merge` (`merge`, `squash`, `rebase`; default `merge`, the behaviour of today).
- `sdd-dispatch.py land-local` merges by it: `merge` as now; `squash` makes one commit with the first line of the branch's last own commit, the rule `land` uses for a PR title (no such commit: code 1, nothing merged); `rebase` rebases the branch onto the main branch in the worktree and fast-forwards. A conflict in any of them aborts (`merge --abort`, a reset of the squash, `rebase --abort` in the worktree) and gives code 6 as now; rollback after a red check is the same `reset --keep`.
- After `squash` and `rebase` the cleanup deletes the branch with `-D`, since git does not see it as merged.
- The description of `delivery.merge` names only pull requests.

## Capabilities

### New Capabilities


### Modified Capabilities
- `dispatch-tool`: Local land command (the merge method from `delivery.local-merge`, a rebase conflict, a squash without an own commit) and Local land checks and cleanup (`branch -D` after squash and rebase) are modified.
- `settings`: Local merge method is added.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`, `docs/settings.md`, `tests/test_settings.py`, `tests/stands/settings-tui.py`, `global/sdd_dispatch.py`, `skills/spec-dispatch/merge.md`, `tests/test_sdd_dispatch.py`, `tests/stands/settings-local-merge.py`

## Out of Scope

- Branch prefixes: `settings-branch-names`.
- The PR merge method: `delivery.merge` keeps it.
- Keeping the branch after a merge: `delivery.delete-branch` of `settings-ci-wait` covers PR delivery only; `land-local` keeps deleting the branch.
- The other units of the same plan: `settings-delivery-items`, `settings-ci-wait`, `settings-branch-names`, `settings-agent-models`, `settings-change-limits`, `settings-gitignore`, `settings-working-copy`, `settings-stop-hooks`, `settings-project-rules`.

## Depends On

none

## Source

The owner, 2026-11-17 (translated from Russian): "I see we made a CLI, but I do not see the settings of our project inside; I want to edit everything that can be edited: how we work with PRs, how we work with subagents, how we work with the project, what we put into gitignore, and so on. A super precise configuration is needed."
