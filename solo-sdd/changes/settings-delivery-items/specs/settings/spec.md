## ADDED Requirements

### Requirement: Text settings
A registry key of kind `text` SHALL take one line of printable characters, at most 200, with the ends trimmed; a line break, a control character or a longer value SHALL be refused with exit 1 and the reason, the file unchanged. `config describe` SHALL name the kind as `text: one line, at most 200 characters`; `solo-sdd settings` SHALL edit it as a one-line input that Esc leaves unchanged.

#### Scenario: A title rule with spaces
- **WHEN** `solo-sdd config set delivery.pr-title "<id>: <summary>"` runs
- **THEN** `config get delivery.pr-title` prints `<id>: <summary>` with `source: file`

#### Scenario: A too long value
- **WHEN** `config set delivery.deploy` gets 201 characters
- **THEN** exit 1 names `at most 200 characters`, the file is unchanged

### Requirement: Delivery items in config
The keys `delivery.pr-title` (default `the change name`), `delivery.deploy` (default `no`) and `delivery.owner-only` (paths, default empty) SHALL take, without a file value, the text after the "PR title:" and "Deploy:" labels of the "Delivery" section of `AGENTS.md`, trimmed and as is, and the backquoted patterns of every "Owner only:" item there, source `AGENTS.md`. `ship`, `spec-dispatch` and `project-init` SHALL read the three through `solo-sdd config get`.

#### Scenario: The old item
- **WHEN** there is no `solo-sdd/config`, and "Delivery" has "Owner only: `global/work_hooks.py`, `docs/**`"
- **THEN** `config get delivery.owner-only` prints `global/work_hooks.py, docs/**` with `source: AGENTS.md`

#### Scenario: The file wins
- **WHEN** the file has `delivery.deploy: on merge into main, Cloudflare Pages` and "Delivery" has "Deploy: no"
- **THEN** `config get delivery.deploy` prints the file value with `source: file`

#### Scenario: A long old item
- **WHEN** there is no file value, and "Delivery" has a "Deploy:" item of 240 characters with backquotes
- **THEN** `config get delivery.deploy` prints the 240 characters as written with `source: AGENTS.md`: the 200-character limit holds for a value set in the file

## MODIFIED Requirements

### Requirement: Defaults by mode
Every registered key SHALL have a type, its allowed values and a default; a key MAY have a different default for `mode: team`. The value in effect SHALL be the file value, else the key's old source: for `delivery.mode` and `delivery.merge` the first allowed `Mode:` or `Merge:` item of the `## Delivery` section of `AGENTS.md`, for another key the item its requirement names, source named after that file; else the mode default, else the built-in default.

#### Scenario: Team default
- **WHEN** the file has only `mode: team`, `AGENTS.md` has no `## Delivery` item, and `delivery.mode` defaults to `local` and to `pr` for a team
- **THEN** `config get delivery.mode` prints `pr`

#### Scenario: File wins
- **WHEN** the file has `mode: team` and `delivery.mode: local`
- **THEN** `config get delivery.mode` prints `local`

#### Scenario: Delivery section kept
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `## Delivery` with `- Mode: pr` and `- Merge: cloud`
- **THEN** `config list` prints `delivery.mode pr AGENTS.md` and `delivery.merge squash default`
