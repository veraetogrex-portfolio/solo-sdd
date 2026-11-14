# Proposal

## Why

Two kinds of project settings do not fit one key and one value: integrations (`integrations` and `integrations.off` only make sense next to the integrations found in the bundle, the home folder and the project, and enabling one also rewrites the rules block of `AGENTS.md`), and checklists (a pair of pattern keys `checklist.<name>.paths` and `checklist.<name>.file` per name). The settings screen of `settings-tui` shows them as raw keys; the owner asked for everything configurable to be configurable there, conveniently.

## What Changes

- Design Read: integrations and checklists sections of the settings screen for not specified, not specified, ENERGY 1 / RHYTHM 1 / MOTION 1 draft without direction
- An Integrations section on the settings screen: every integration found, with its source (bundled, home, project), state, points and description; a broken or shadowed one is shown with its reason and cannot be toggled. A toggle is saved through the same code as `solo-sdd integrations enable|disable`, so the `AGENTS.md` rules block is rewritten with it; a refusal there writes nothing and is shown.
- The enable and disable path of `solo-sdd integrations` moves into a function both the command and the screen call; the command's output stays.
- A Checklists section: every checklist name with its paths and file, a pair with one key missing marked incomplete, a file that does not exist marked missing; add (name, paths, file), edit and remove (both keys), each value checked by the settings check.

## Capabilities

### New Capabilities
- `settings-ui-lists`: integrations and checklists on the settings screen.

### Modified Capabilities

## Impact

- `solo_sdd/settings_ui.py`, `solo_sdd/integrations.py`
- `docs/settings.md`, `docs/integrations.md`
- `tests/test_settings_ui.py`, `tests/test_integrations.py`, `tests/stands/settings-tui-lists.py` (new), `tests/affected.json`

## Out of Scope

- The screen itself, the plain keys and saving: `settings-tui`.
- Key descriptions: `config-describe`.
- Machine settings: `settings-tui-home`.
- Bare `solo-sdd` opening a menu: `cli-menu`.
- Writing the checklist file's items from the screen: the file is edited in an editor.
- Installing a new integration into the home folder from the screen.

## Depends On

settings-tui

## Source

The owner, 2026-11-14 (translated from Russian): "I want a CLI in which I can configure solo-sdd for each project; everything that can be configured now must be in the CLI; the configuration must be detailed and convenient".
