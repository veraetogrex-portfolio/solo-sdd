## Purpose

Integrations and checklists on the project settings screen: the settings that are a set of found items or a pair of keys per name, shown and changed as such instead of as raw keys.

## ADDED Requirements

### Requirement: Integrations section
The settings screen SHALL list every integration `solo-sdd integrations list` finds, with source, state, points and description; a broken or shadowed one SHALL show its reason and SHALL NOT toggle. A saved toggle SHALL go through the same function as `solo-sdd integrations enable` and `disable`, including the `AGENTS.md` rules block; when that function refuses, no file SHALL change and the reason SHALL be shown.

#### Scenario: A bundled one off
- **WHEN** the person toggles the enabled bundled integration `antislop` and saves
- **THEN** `solo-sdd/config` has `integrations.off: antislop` and `solo-sdd integrations list` shows it disabled

#### Scenario: A broken one
- **WHEN** a project integration has a broken description
- **THEN** the section shows it with the reason, and toggling it does nothing

#### Scenario: Rules block refused
- **WHEN** `AGENTS.md` is not writable and the person saves a toggle
- **THEN** neither `solo-sdd/config` nor `AGENTS.md` changes, and the screen shows the reason

### Requirement: Integration keys through the section
On the settings screen the keys `integrations` and `integrations.off` SHALL be changed only through the Integrations section, never as text, so every change of them rewrites the `AGENTS.md` rules block.

#### Scenario: No raw edit
- **WHEN** the person selects the key `integrations` in the key list and presses Enter
- **THEN** the Integrations section opens instead of a text entry

### Requirement: Same result as the command
Saving an integration toggle on the screen SHALL leave `solo-sdd/config` and `AGENTS.md` with the same bytes as running `solo-sdd integrations enable` or `disable` with that name on the same project.

#### Scenario: Screen and command agree
- **WHEN** one copy of a project gets the toggle on the screen and another copy gets `solo-sdd integrations disable antislop`
- **THEN** both copies have the same `solo-sdd/config` and `AGENTS.md`

### Requirement: Checklists section
The settings screen SHALL list each checklist name with its paths and file, mark a name with only one of its two keys as incomplete and a file that does not exist as missing, and SHALL add, edit and remove a checklist: add asks for a name, paths and a file, remove unsets both keys. Each value SHALL pass the settings check; a refused one SHALL change nothing and show the reason.

#### Scenario: Add
- **WHEN** the person adds `money-safety` with paths `billing/**` and file `docs/checklists/money.md`, and saves
- **THEN** the config has `checklist.money-safety.paths: billing/**` and `checklist.money-safety.file: docs/checklists/money.md`

#### Scenario: A wrong name
- **WHEN** the person adds a checklist named `Money Safety`
- **THEN** the reason names the allowed characters and nothing is added

#### Scenario: Remove
- **WHEN** the person removes `money-safety` and saves
- **THEN** neither key of `money-safety` is in the config

#### Scenario: Incomplete
- **WHEN** the config has only `checklist.docs.paths`
- **THEN** the section marks `docs` incomplete and names the missing `file`
