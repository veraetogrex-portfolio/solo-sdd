# Proposal

## Why

Reproduction (review finding of the settings-* run, 2026-11-17; read in code and in git's `builtin/reset.c` on 2026-11-18):
1. `MAIN` has `solo-sdd/config` in `info/exclude`.
2. WORKTREE of `change/b` holds an ignored `solo-sdd/config` with its own value and `delivery.local-merge: rebase`, and has one own commit.
3. Then `MAIN` commits `solo-sdd/config` with `git add -f`, and `sdd-dispatch.py land-local MAIN WORKTREE b` runs.
4. Expected: a refusal that names the file, or WORKTREE keeps its value.
5. Got: code 0. WORKTREE's file silently takes `MAIN`'s text, and the transfer does not carry it either, so the worktree edit is lost.

Cause: `global/sdd_dispatch.py:425` moves WORKTREE with `git reset --keep`. For an ignored untracked file git takes it as expendable (`preserve_ignored = 0` for KEEP). The guard `overwritten()` (`global/sdd_dispatch.py:386`) checks only the untracked files of `MAIN` against the branch, not the ignored files of WORKTREE.

The same class sits in `global/sdd_pr.py:1120`. There `cmd_ship` runs `git -C <WORKTREE> merge origin/<main>`, and a merge also overwrites ignored files that the incoming commits track.

## What Changes

- `land-local` with `delivery.local-merge: rebase` compares the paths the move of WORKTREE writes (the diff between WORKTREE's `HEAD` and the rebased commit) with the files WORKTREE holds untracked, as `overwritten()` does for `MAIN`, before `reset --keep`. Any match gives code 1 with `not merged: rebase would overwrite ignored files in WORKTREE: <paths>`, and nothing moves.
- `sdd-pr.py ship` makes the same comparison, over the paths `origin/<main>` changed since its merge base with WORKTREE's `HEAD`, before it merges `origin/<main>` into WORKTREE. A match stops with code 1 and `not shipped: merge would overwrite ignored files in WORKTREE: <paths>`. No push or PR follows.
- The dispatcher's merge step names both lines: each is "not merged" for the report with no return to the orchestrator, since the return's `git merge <main branch>` would overwrite the same files.

## Capabilities

### New Capabilities

### Modified Capabilities
- `dispatch-tool`: ADDED requirement Rebase keeps worktree ignored files.
- `pr-tool`: ADDED requirement Ship keeps worktree ignored files.

## Impact

- `global/sdd_dispatch.py`
- `global/sdd_pr.py`
- `tests/test_sdd_dispatch.py`
- `tests/test_sdd_pr.py`
- `skills/spec-dispatch/merge.md`
- `tests/stands/worktree-ignored-overwrite.py`

## Out of Scope

- `global/sdd_worktree.py:562`: the `reset --keep` of `setup` (`start_at_base`) runs before anything is copied into a new worktree, so there is nothing to lose.
- The rollbacks of `MAIN` at `global/sdd_dispatch.py:360` and `:521`: they act on `MAIN`, whose untracked files the existing guard covers.
- The `git -C <WORKTREE> merge <main branch>` the "Return on conflict" of `skills/spec-dispatch/merge.md` tells the orchestrator to run: it can overwrite an ignored file the same way after an ordinary conflict; a separate change.
- Neighbouring changes of this plan: `test-runner-deps-check`, `dispatched-status-self-check`, `fix-settings-entry-scroll`, `fix-ci-wait-unread-checks`, `fix-stop-gate-worktree-config`, `fix-setup-links-exclude`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create a change" (on the follow-up list after the settings-* run, item: `reset --keep` overwrites an ignored WORKTREE file that the rebased commit tracks)
