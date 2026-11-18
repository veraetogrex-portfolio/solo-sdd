# Proposal

## Why

Reproduction (review finding of the settings-* run, 2026-11-17; read in code on 2026-11-18):
1. `MAIN` has `node_modules/p/i.js` and `.venv/`, under the default `worktree.links`.
2. `sdd-worktree.py setup` makes the `node_modules` link and then fails on the second link, for example when `os.symlink` raises.
3. Expected: `info/exclude` holds `node_modules`, and a later `remove` refuses only for real work.
4. Got: `setup` exits 1, `info/exclude` holds neither pattern, `git status` shows `?? node_modules`, and `remove` exits 1 with "the worktree has uncommitted changes". `discard` still works, and a second `setup` heals it.

Cause: `global/sdd_worktree.py:794`-`797` makes the links in a loop. `add_exclude(main, linked)` at `global/sdd_worktree.py:799` runs only after the whole loop, so an exception inside the loop skips it. The `<WORKTREE>.links` record is written per link and is not the cause.

## What Changes

- `setup` adds the exclusion pattern of every link it has made, also when a later link fails, so `git status` and `remove` do not see the links.

## Capabilities

### New Capabilities

### Modified Capabilities
- `worktree-env`: MODIFIED requirement Worktree venv link (the failure case added, a new scenario A later link fails).

## Impact

- `global/sdd_worktree.py`
- `tests/test_sdd_worktree.py`
- `tests/stands/setup-links-exclude.py`

## Out of Scope

- A half-built `node_modules` folder of links when `link_modules` raises midway: it stays for `discard`, which already removes it.
- The dispatcher's handling of a failed setup: `discard` stays the step.
- Neighbouring changes of this plan: `test-runner-deps-check`, `dispatched-status-self-check`, `fix-settings-entry-scroll`, `fix-worktree-ignored-overwrite`, `fix-ci-wait-unread-checks`, `fix-stop-gate-worktree-config`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create a change" (on the follow-up list after the settings-* run, item: a setup that fails inside the link loop leaves its links unexcluded so remove refuses)
