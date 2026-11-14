## Purpose

An interactive full-screen terminal screen where a person reads and changes every setting of a project's solo-sdd, with each key explained, without knowing the keys by heart.

## ADDED Requirements

### Requirement: Settings screen
`solo-sdd settings [folder]` on a terminal SHALL open a full-screen screen on the standard library listing every registered key by group with its value in effect and source, and for the selected key its description, allowed values, default and team default. Without a terminal on stdin and stdout, or without a `solo-sdd/` tree, it SHALL print the command to use instead and exit 1, changing no file.

#### Scenario: Opened in a project
- **WHEN** `solo-sdd settings` runs on a terminal in a project with `solo-sdd/config`
- **THEN** the screen lists the groups and keys with values and sources, and the bottom shows the selected key's description

#### Scenario: No terminal
- **WHEN** `solo-sdd settings < /dev/null` runs
- **THEN** a line naming `solo-sdd config` is printed, exit 1, no file changes

#### Scenario: No tree
- **WHEN** `solo-sdd settings` runs on a terminal in a folder without `solo-sdd/`
- **THEN** a line naming `solo-sdd init` is printed, exit 1

#### Scenario: A terminal curses cannot drive
- **WHEN** `solo-sdd settings` runs on a terminal with `TERM=dumb` or a `TERM` the terminal database lacks
- **THEN** the same line naming `solo-sdd config` is printed, exit 1, and no file changes

### Requirement: Edit by type
Editing a key SHALL offer a pick list for a choice, a number entry for a whole number, checkboxes for a list with known values, and a text entry for other lists, names and paths. Every entered value SHALL pass the same check as `config set`; a refused value SHALL keep the old one and show the reason. Reset SHALL put the key back to the value below the file.

#### Scenario: A choice
- **WHEN** the person selects `delivery.mode`, presses Enter and picks `pr`
- **THEN** the key shows `pr` marked as unsaved

#### Scenario: A wrong number
- **WHEN** the person enters `0` for `dispatch.limit`
- **THEN** the reason from the settings check is shown and the old value stays

#### Scenario: Checkboxes
- **WHEN** the person unticks `codex` on `agents`
- **THEN** the value becomes the other ticked agents in registry order

#### Scenario: Reset
- **WHEN** the file has `dispatch.limit: 4` and the person resets the key
- **THEN** the key shows `2` with source `default`, marked as unsaved

### Requirement: Save only edited lines
Edits SHALL stay in memory until save. Save SHALL list each edited key with its old and new value and write only after confirmation, changing only the lines of edited keys the way `config set` and `unset` do. A file whose bytes changed since the screen read it SHALL NOT be written; the screen says so. Quit with unsaved edits SHALL ask; Ctrl-C SHALL leave without writing and restore the terminal.

#### Scenario: Comments kept
- **WHEN** the file has comments and five keys, and the person edits two keys and saves
- **THEN** only the lines of the two keys differ; every comment and other line keeps its bytes

#### Scenario: Changed on disk
- **WHEN** another process edits `solo-sdd/config` after the screen opened, and the person saves
- **THEN** nothing is written and the screen names the change on disk

#### Scenario: Quit asks
- **WHEN** there is an unsaved edit and the person presses `q`
- **THEN** the screen asks to save, discard or go back

### Requirement: Guidance on the screen
The screen SHALL keep a footer naming the keys of the current view. A key whose `## Delivery` item in `AGENTS.md` differs from its file value SHALL be marked as overriding it with the `AGENTS.md` value shown. Choosing `delivery.mode: pr` in a project without a CI workflow SHALL show the warning `solo-sdd init` prints for it before save.

#### Scenario: Footer
- **WHEN** the key list is shown
- **THEN** the footer names the keys for move, edit, reset, save and quit

#### Scenario: AGENTS.md overridden
- **WHEN** `AGENTS.md` has `- Mode: local` under `## Delivery` and the file has `delivery.mode: pr`
- **THEN** the key is marked as overriding `AGENTS.md: local`

#### Scenario: pr without CI
- **WHEN** the project has no `.github/workflows/*.yml` and the person picks `pr` for `delivery.mode`
- **THEN** the warning that `pr` needs a CI workflow is shown, and the edit stays possible

### Requirement: Broken config read-only
A `solo-sdd/config` that does not parse SHALL open read-only: the screen SHALL show the file, line and reason from the settings check and SHALL offer no edit or save.

#### Scenario: A broken line
- **WHEN** line 4 of `solo-sdd/config` is `delivery.mode pr` without a colon
- **THEN** the screen shows `solo-sdd/config:4` and the reason, and Enter edits nothing

### Requirement: Safe display
Text read from the config or the registry SHALL be shown with control characters escaped. A terminal under 40 columns or 12 rows SHALL show a request to enlarge it; a wider one SHALL cut long lines to its width without breaking the layout.

#### Scenario: An escape in a value
- **WHEN** a comment or a value holds an ESC character
- **THEN** the screen shows it as `\x1b` and the terminal state does not change

#### Scenario: A small terminal
- **WHEN** the terminal is 30 columns wide
- **THEN** the screen shows only the request to enlarge it, and redraws the list after a resize to 80
