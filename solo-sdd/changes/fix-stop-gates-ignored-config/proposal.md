# Proposal

## Why

Reproduction (review finding of 2026-11-18, read in code the same day):
1. A repository ignores `solo-sdd/config`, and the main checkout's file has `hooks.stop.uncommitted: off`.
2. In a worktree made by plain `git worktree add` (no config file there), the session leaves an edit uncommitted.
3. Expected: the gate is off, as for the open PR gate after fix-stop-gate-worktree-config.
4. Got: "has uncommitted edits". The `unarchived` and `ui-check` gates behave the same way.

Cause: only the open PR gate falls back to the main checkout (`global/work_hooks.py:2773`-`2775`, the `lacks` check with `git check-ignore`). The other gates read the edited repository's root directly: `gate_setting(root, "hooks.stop.uncommitted")` at `global/work_hooks.py:2756`, `gate_setting(change_project(cdir), "hooks.stop.unarchived")` at `:2767`, and `gate_settings(git_root(path))` in `ui_file` at `:2729`. `read_settings_text` (`:322`) returns the defaults when the file is missing.

## What Changes

- One helper picks the config folder for a checked copy: the copy itself, or its main checkout when the copy has no `solo-sdd/config` and git ignores that path there.
- All four stop gates use it.

## Capabilities

### New Capabilities

### Modified Capabilities
- `settings`: MODIFIED requirement Stop gate switches (a new scenario Other gates in a worktree without a config file).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/settings-stop-hooks.py`

## Out of Scope

- Worktrees made by `sdd-worktree.py setup`: they already get the config copied.
- The double `errors.log` line for a broken file: a separate pre-existing finding.
- Neighbouring changes of this plan: `dispatch-skill-ci-and-return`, `fix-venv-exclude-line`, `fix-settings-fit-zero-width`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create them" (on the list of new review findings after the 2026-11-18 dispatcher run, item: the other stop gates do not fall back to an ignored main checkout config the way the open-PR gate does)
