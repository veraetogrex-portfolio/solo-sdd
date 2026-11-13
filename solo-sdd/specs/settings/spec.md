# settings Specification

## Purpose
Keeps every project setting of solo-sdd in one file with known keys and defaults per mode, and lets the user read and change them with one command.

## Requirements

### Requirement: Settings file
Project settings SHALL live in `solo-sdd/config`, one `key: value` per line, `#` starting a comment, list values separated by commas. A missing file SHALL mean all defaults. A line that is not `key: value` or names an unknown key SHALL make the `config` command and the scripts fail with the file, the line number and the reason; the hooks SHALL use the defaults and log it (fail-open).

#### Scenario: A list value
- **WHEN** a registered key takes a list and the file has it as `staging, main`
- **THEN** `solo-sdd config get` of that key prints `staging, main`

#### Scenario: A broken file in a hook
- **WHEN** the file has a broken line and the `stop` hook runs
- **THEN** the hook uses the defaults and writes the reason to `~/.claude/hook-state/errors.log`

#### Scenario: A broken line
- **WHEN** line 4 is `delivery.mode pr` without a colon
- **THEN** `solo-sdd config list` exits 1 and names `solo-sdd/config:4`

### Requirement: Defaults by mode
Every registered key SHALL have a type, its allowed values and a default; a key MAY have a different default for `mode: team`. The value in effect SHALL be the file value, else for `delivery.mode` and `delivery.merge` the first allowed `Mode:` or `Merge:` item of the `## Delivery` section of `AGENTS.md`, else the mode default, else the built-in default.

#### Scenario: Team default
- **WHEN** the file has only `mode: team`, `AGENTS.md` has no `## Delivery` item, and `delivery.mode` defaults to `local` and to `pr` for a team
- **THEN** `config get delivery.mode` prints `pr`

#### Scenario: File wins
- **WHEN** the file has `mode: team` and `delivery.mode: local`
- **THEN** `config get delivery.mode` prints `local`

#### Scenario: Delivery section kept
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `## Delivery` with `- Mode: pr` and `- Merge: cloud`
- **THEN** `config list` prints `delivery.mode pr AGENTS.md` and `delivery.merge squash default`

### Requirement: Config command
`solo-sdd config list` SHALL print every key, its value in effect and its source (`file`, `AGENTS.md`, `mode`, `default`). `get <key>` SHALL print the value on stdout and `source: <source>` on stderr. `set <key> <value>` and `unset <key>` SHALL change only that line and keep comments and order. A wrong key or value SHALL be refused with exit 1 and the allowed keys or values.

#### Scenario: Set keeps the rest
- **WHEN** the file has a comment line and two keys, and `config set dispatch.limit 3` runs
- **THEN** only the `dispatch.limit` line changes; the comment and the other key keep their bytes

#### Scenario: A wrong value
- **WHEN** `config set delivery.mode cloud` runs
- **THEN** exit 1, the message lists `local, pr`, the file is unchanged

#### Scenario: Get names the source
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `## Delivery` with `- Mode: pr`
- **THEN** `config get delivery.mode` prints `pr` on stdout and `source: AGENTS.md` on stderr

### Requirement: Readers use the settings
The dispatch plan, `spec-dispatch`, `ship`, `spec-next` and the `stop` hook SHALL read the delivery mode and merge method, the orchestrator limit, the review rounds and the reply language from the settings. Without the key in the file they SHALL keep the old source (`## Delivery` of `AGENTS.md`, `SOLO_SDD_REPLY_LANG`) before the default.

#### Scenario: Limit from config
- **WHEN** `solo-sdd/config` has `dispatch.limit: 3` and `AGENTS.md` says `Orchestrators: 2`
- **THEN** the dispatch plan prints `limit: 3`

#### Scenario: Old source kept
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `- Mode: pr`
- **THEN** the dispatch plan uses `pr`
