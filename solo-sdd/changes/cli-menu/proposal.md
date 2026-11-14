# Proposal

## Why

The owner expects to type `solo-sdd` and get an interface, as with other agent tools. Today bare `solo-sdd` prints the command list and exits with code 2, so the settings screens of `settings-tui`, `settings-tui-lists` and `settings-tui-home` are reachable only by a command name a person must already know, and a folder not yet prepared has no way in but `solo-sdd init`.

## What Changes

- Design Read: home menu of the solo-sdd CLI for not specified, not specified, ENERGY 1 / RHYTHM 1 / MOTION 1 draft without direction
- Bare `solo-sdd` with a terminal on stdin and stdout opens a full-screen home menu; without a terminal it keeps printing the command list with exit code 2, so scripts and agents see no change.
- The menu header names the folder, the version, the project mode and the count of open changes; its entries are Project settings, Integrations and checklists, Machine, Changes (the `solo-sdd list` rows with progress, `CLAIM` and `WAITING`, read-only), Doctor, Commands (the command list) and Quit.
- A folder without `solo-sdd/` gets the entry Prepare this folder, which leaves the full screen, runs the questions of `solo-sdd init` and comes back to the menu with the project entries; a folder with only `openspec/` gets the import hint instead and nothing is written.
- `docs/cli.md` and the README quick start name the menu.

## Capabilities

### New Capabilities

### Modified Capabilities
- `cli`: Entry point changes (bare `solo-sdd` on a terminal opens the menu); Home menu is added.

## Impact

- `solo_sdd/cli.py`, `solo_sdd/settings_ui.py`
- `README.md`, `docs/cli.md`
- `tests/test_cli.py`, `tests/test_settings_ui.py`, `tests/stands/cli-menu.py` (new), `tests/affected.json`

## Out of Scope

- The settings screens themselves: `settings-tui`, `settings-tui-lists`, `settings-tui-home`.
- Key descriptions: `config-describe`.
- Running agents, skills or changes (`spec-next`, `spec-dispatch`) from the menu: they run in the agent.
- Archiving or creating changes from the menu.

## Depends On

settings-tui, settings-tui-lists, settings-tui-home

## Source

The owner, 2026-11-14 (translated from Russian): "But I want to open a CLI interface like openspec or claude code or Vesna", then "I want a CLI in which I can configure solo-sdd for each project; everything that can be configured now must be in the CLI; the configuration must be detailed and convenient".
