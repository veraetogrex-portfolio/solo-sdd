# Proposal

## Why

The owner wants to configure each project's solo-sdd from an interactive CLI screen, like the full-screen interfaces of other agent tools, with every setting reachable and explained. Today the only ways are `solo-sdd config set <key> <value>` with the key and its values known by heart, or `init --reconfigure`, which walks every key in a fixed order and cannot go back.

## What Changes

- Design Read: project settings screen for not specified, not specified, ENERGY 1 / RHYTHM 1 / MOTION 1 draft without direction
- `solo-sdd settings [folder]`: a full-screen terminal screen on the standard library `curses` (no new dependency) over the project's `solo-sdd/config`: the keys by group with the value in effect and its source, and for the selected key the description, allowed values, default and team default from `config-describe`.
- Editing by type: a choice from a list, a whole number checked on entry, a list with known values as checkboxes, a branch, name or path list as text checked by the same rule as `config set`; reset puts a key back to the value below the file (`unset`).
- Edits stay in memory until save; save shows every changed key as old and new value and writes after confirmation, changing only those lines the way `config set`/`unset` do; a file changed on disk since the screen opened is not overwritten; quit with unsaved edits asks; Ctrl-C leaves without writing.
- Guidance: a footer with the keys of the current view; a key whose file value overrides a `## Delivery` item of `AGENTS.md` is marked with that item's value; picking `delivery.mode: pr` without a CI workflow shows the warning `init` prints.
- A broken `solo-sdd/config` opens read-only with the file, line and reason; no terminal or no `solo-sdd/` tree prints what to run instead and exits 1.
- Values are shown with control characters escaped; a terminal under 40 columns or 12 rows shows a request to enlarge it instead of a broken layout.
- The screen state and drawing are a pure model tested by key sequences; `curses` is a thin loop around it.

## Capabilities

### New Capabilities
- `settings-ui`: the interactive settings screen of a project.

### Modified Capabilities

## Impact

- `solo_sdd/settings_ui.py` (new), `solo_sdd/settings.py`, `solo_sdd/cli.py`
- `docs/cli.md`, `docs/settings.md`
- `tests/test_settings_ui.py` (new), `tests/stands/settings-tui.py` (new), `tests/affected.json`

## Out of Scope

- Key descriptions and `config describe`: `config-describe`.
- Integrations and checklists on the screen: `settings-tui-lists`.
- Machine settings (agents, hooks, global rules): `settings-tui-home`.
- Bare `solo-sdd` opening a menu: `cli-menu`.
- Windows: `curses` is not in its standard library, and the package names macOS and Linux only.
- Mouse input and colour themes of its own: the screen uses the terminal's colours.

## Depends On

config-describe

## Source

The owner, 2026-11-14 (translated from Russian): "I want a CLI in which I can configure solo-sdd for each project; everything that can be configured now must be in the CLI; the configuration must be detailed and convenient". Earlier in the same conversation: "But I want to open a CLI interface like openspec or claude code or Vesna".
