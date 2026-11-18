# Proposal

## Why

Reproduction (review finding of the settings-* run, 2026-11-17; read in code on 2026-11-18):
1. Open `solo-sdd settings`, select `delivery.deploy`, press Enter, then type 150 characters on an 80-column screen.
2. Expected: the entry line shows the end of the text with the `_` cursor.
3. Got: the line is `> ` and the first 77 characters (`fit` cuts to `width - 1` = 79 columns). The tail and `_` are cut off. The terminal cursor is hidden (`curs_set(0)`), so `_` is the only cursor and the person types blind.

Cause: `solo_sdd/settings_ui.py:706` builds the whole line `"> " + shown(self.buffer) + "_"`. Then `solo_sdd/settings_ui.py:644` cuts every line with `fit(ln, width - 1)`, and `fit` (`solo_sdd/settings_ui.py:39`) keeps the head of a text.

## What Changes

- The entry line keeps its tail: when `> `, the value and `_` are wider than the screen, the line shows the end of the value and the cursor. The saved value is not cut.

## Capabilities

### New Capabilities

### Modified Capabilities
- `settings-ui`: MODIFIED requirement Edit by type (a new scenario A long text entry).

## Impact

- `solo_sdd/settings_ui.py`
- `tests/test_settings_ui.py`
- `tests/stands/settings-tui.py`

## Out of Scope

- Moving the cursor inside the value (left/right arrows): the entry stays append and erase at the end.
- Other long lines of the screen: they keep the Safe display cut.
- Neighbouring changes of this plan: `test-runner-deps-check`, `dispatched-status-self-check`, `fix-worktree-ignored-overwrite`, `fix-ci-wait-unread-checks`, `fix-stop-gate-worktree-config`, `fix-setup-links-exclude`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create a change" (on the follow-up list after the settings-* run, item: the TUI entry line does not scroll)
