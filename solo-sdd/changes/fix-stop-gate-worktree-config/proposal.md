# Proposal

## Why

Reproduction (review finding of the settings-* run, 2026-11-17; read in code on 2026-11-18):
1. Repository P tracks `solo-sdd/config` with `hooks.stop.open-pr: on`.
2. Worktree `wt` of `change/x` commits `solo-sdd/config` with `hooks.stop.open-pr: off`.
3. The session in `wt` pushed, and `gh pr view` shows an open PR.
4. Expected: the stop is not blocked, since the gate checks `wt`'s branch and `wt` sets the gate off.
5. Got: "PR …/pull/9 is open and not merged". The reverse case (main `off`, `wt` `on`) is never blocked.

Cause: `global/work_hooks.py:2772`-`2773`. `main = main_checkout(root)`, then `gate_setting(main, "hooks.stop.open-pr")` and `gate_setting(main, "delivery.merge-by")`, while `gh pr view` runs in `root`. The other gates read the edited repository's own root (`by_root`, `ui_file`).

## What Changes

- The open PR gate reads `hooks.stop.open-pr` and `delivery.merge-by` from the working copy whose branch it checks (`root`). When that copy has no `solo-sdd/config` file, it reads the main checkout's file, as an ignored config is kept only there.

## Capabilities

### New Capabilities

### Modified Capabilities
- `settings`: MODIFIED requirement Stop gate switches (new scenarios A worktree with its own config, A worktree without a config file).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/settings-stop-hooks.py`

## Out of Scope

- A session that pushed a branch of another repository: the gate checks only the session's own repository. That is a separate gap, not this cause.
- Neighbouring changes of this plan: `test-runner-deps-check`, `dispatched-status-self-check`, `fix-settings-entry-scroll`, `fix-worktree-ignored-overwrite`, `fix-ci-wait-unread-checks`, `fix-setup-links-exclude`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create a change" (on the follow-up list after the settings-* run, item: the open-PR stop gate reads the main checkout's config)
