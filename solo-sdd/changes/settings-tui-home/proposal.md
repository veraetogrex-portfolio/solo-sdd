# Proposal

## Why

Part of what a person configures is not in `solo-sdd/config` but on the machine: which agents get the skills (`install --agents`), whether the Claude Code hooks are connected (`install --hooks`) and whether the global rules block is written (`install --global-rules`). The owner asked for everything configurable to be configurable from the CLI screen. Today the hooks can be connected but not disconnected alone: only `uninstall`, which removes every copy, takes them out.

## What Changes

- Design Read: machine section of the settings screen for not specified, not specified, ENERGY 1 / RHYTHM 1 / MOTION 1 draft without direction
- `solo-sdd uninstall --hooks`: disconnects only what `install --hooks` recorded in `_hooks`, keeps every copy and every setting a person added, the way `uninstall --global-rules` removes only the rules block.
- A Machine section on the settings screen, also opened outside a project: the chosen agents as checkboxes (registered providers, `other` always on, detected ones marked), hooks on or off, global rules on or off, the deployment source and version, the count of copies by `status` state, and the `warn` and `fail` lines of `doctor`.
- Applying machine edits shows the commands it will run (`solo-sdd install --agents … [--hooks] [--global-rules]`, `solo-sdd uninstall --hooks`, `solo-sdd uninstall --global-rules`) and the folders they change, runs them in process only after confirmation, and shows their output and exit codes; a refused one (hooks without `claude`) changes nothing.

## Capabilities

### New Capabilities
- `settings-ui-home`: the machine section of the settings screen.

### Modified Capabilities
- `cli`: Uninstall hooks only is added.

## Impact

- `solo_sdd/settings_ui.py`, `solo_sdd/cli.py`, `solo_sdd/hooks.py`
- `docs/cli.md`, `docs/hooks.md`, `docs/settings.md`
- `tests/test_settings_ui.py`, `tests/test_cli.py`, `tests/stands/settings-tui-home.py` (new), `tests/affected.json`

## Out of Scope

- Project settings, integrations and checklists on the screen: `settings-tui`, `settings-tui-lists`.
- Bare `solo-sdd` opening a menu: `cli-menu`.
- Fixing what `doctor` reports from the screen: the lines are shown with their own fix text.
- `sync pull` and `update` from the screen.

## Depends On

settings-tui

## Source

The owner, 2026-11-14 (translated from Russian): "I want a CLI in which I can configure solo-sdd for each project; everything that can be configured now must be in the CLI; the configuration must be detailed and convenient".
