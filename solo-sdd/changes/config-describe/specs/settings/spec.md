## ADDED Requirements

### Requirement: Key descriptions
Every key of the settings registry and every pattern key SHALL have a group and a one-sentence description in the package. A key without them SHALL fail the test suite.

#### Scenario: A new key without a description
- **WHEN** a key is added to the registry without a description
- **THEN** the settings test fails and names the key

#### Scenario: A new pattern key without a description
- **WHEN** a pattern key is added without a group
- **THEN** the settings test fails and names the pattern

### Requirement: Describe a setting
`solo-sdd config describe [<key>]` SHALL print for each registered key, then each pattern and each pattern key set in the file, or for the one named, its group, description, type with allowed values, default, team default, value in effect and source; `config list --json` the same fields as a list of objects, plain `config list` unchanged. An unknown key, or a broken file as `config list` refuses it, SHALL give exit 1.

#### Scenario: One key
- **WHEN** `solo-sdd config describe delivery.mode` runs with no `solo-sdd/config` and no `## Delivery` in `AGENTS.md`
- **THEN** the output names the group `delivery`, its description, `local, pr`, default `local`, team default `pr`, value `local`, source `default`

#### Scenario: JSON list
- **WHEN** `solo-sdd config list --json` runs
- **THEN** a list with one object per registered key, each with `key`, `group`, `about`, `type`, `allowed`, `default`, `team_default`, `value` and `source`

#### Scenario: Unknown key
- **WHEN** `solo-sdd config describe delivery.color` runs
- **THEN** exit 1, the message lists the known keys

#### Scenario: Pattern keys
- **WHEN** the file has `checklist.money.paths: billing/**` and `config describe` runs
- **THEN** after the registered keys come `checklist.<name>.paths` and `checklist.<name>.file` with their descriptions, then `checklist.money.paths` with value `billing/**` and source `file`

#### Scenario: A broken file
- **WHEN** line 4 of `solo-sdd/config` is `delivery.mode pr` without a colon
- **THEN** `config describe` exits 1 and names `solo-sdd/config:4`, as `config list` does
