# integrations Specification

## Purpose
Lets a project or its owner plug an outside tool or rule set into solo-sdd as an integration: a folder with a `key: value` description that the core reads by one contract, never by the tool's name, and runs only when the project enables it.

## Requirements

### Requirement: Integration description
An integration SHALL be a folder `<name>/` holding a file `integration` of `key: value` lines, `#` starting a comment. The keys SHALL be `name` (equal to the folder name: lowercase ASCII letters, digits and `-`, not starting with `-`), `about`, `points` (a list of `checks`, `review`, `ship`, `audit`), `command`, `material`, `applies`, `requires`, `mode`, `missing`, `timeout`, `output` and `tags` (a list of names). `name`, `about` and `points` SHALL be required.

#### Scenario: A complete description
- **WHEN** `solo-sdd/integrations/marker-check/integration` has `name: marker-check`, `about: refuses a marker line`, `points: checks, ship` and `command: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"`
- **THEN** `solo-sdd integrations list` prints a line for `marker-check` with its points `checks, ship` and its `about`

#### Scenario: Name differs from the folder
- **WHEN** the folder `marker-check/` holds `name: other-check`
- **THEN** it is refused naming the file, the line and `name`

#### Scenario: A point without its command
- **WHEN** an integration names the point `checks` and has no `command`
- **THEN** it is refused naming the file and `command`

### Requirement: Field defaults
`mode` SHALL take `gate` or `advice` and default to `advice`; `missing` SHALL take `warn` or `fail` and default to `warn`; `timeout` and `output` SHALL take a whole number from 1 and default to 120 seconds and 20 lines. `command` SHALL be required for the points `checks` and `ship`, `material` (a path inside the integration folder) for `review` and `audit`. An empty `applies` SHALL match any changed file.

#### Scenario: Defaults applied
- **WHEN** a description has only `name`, `about`, `points: checks` and `command`
- **THEN** it reads as `mode: advice`, `missing: warn`, `timeout: 120`, `output: 20`

#### Scenario: Material outside the folder
- **WHEN** a description with `points: review` has `material: ../secret.md`
- **THEN** it is refused naming the file, the line and `material`

### Requirement: Integration sources
Integrations SHALL be found in the project's `solo-sdd/integrations/<name>/` and in the owner's `~/.local/share/solo-sdd/integrations/<name>/` (under the passed home). When both hold the same name, the project one SHALL be used and `integrations list` SHALL name the owner one as shadowed.

#### Scenario: Same name in both
- **WHEN** both the project and the owner folder hold `marker-check`
- **THEN** `integrations list` prints `marker-check project` and a line naming the owner copy as shadowed

### Requirement: Explicit enablement
An integration SHALL run only when the `integrations` setting of `solo-sdd/config` (a list of names, empty by default) names it, except a bundled integration, which SHALL run unless `integrations.off` names it. A found project or owner folder not in the list SHALL stay disabled, an owner integration included. A name in the list with no folder in any source SHALL be refused by every reader that lists or runs it, and `integrations disable` SHALL still remove it.

#### Scenario: Owner integration not enabled by itself
- **WHEN** the owner folder holds `dup-scan` and the project's `integrations` is empty
- **THEN** `integrations list` prints `dup-scan owner disabled`

#### Scenario: A listed name without a folder
- **WHEN** `integrations: no-such` is set and no source holds `no-such`
- **THEN** `integrations list` exits 1 naming `no-such`

#### Scenario: A stale name removed
- **WHEN** `integrations: no-such` is set and `integrations disable no-such` runs
- **THEN** `integrations` no longer holds `no-such` and the command exits 0

#### Scenario: A bundled integration by default
- **WHEN** `integrations` is empty and `integrations.off` is empty
- **THEN** `integrations list` shows `antislop bundled enabled`

### Requirement: Broken description refused
A line that is not `key: value`, an unknown key, a repeated key, a wrong value or a missing required key SHALL be refused with the file path, the line number (none for a missing key) and the key, and SHALL NOT be skipped silently. `integrations list` SHALL still print the readable integrations and exit 1.

#### Scenario: An unknown key
- **WHEN** line 3 of `solo-sdd/integrations/marker-check/integration` is `colour: red`
- **THEN** `integrations list` prints the other integrations, names `solo-sdd/integrations/marker-check/integration:3` and `colour`, and exits 1

#### Scenario: A wrong mode
- **WHEN** a description has `mode: strict`
- **THEN** it is refused naming the line and listing `gate, advice`

### Requirement: Integrations command
`solo-sdd integrations list` SHALL print one line `<name> <source> enabled|disabled <points>: <about>` per found integration. `integrations enable <name>` and `disable <name>` SHALL work for any one, change only the `integrations` line of `solo-sdd/config` (`integrations.off` for a bundled one) and rewrite the solo-sdd block of `AGENTS.md`; `enable` SHALL refuse an unknown name or a broken description (exit 1), `disable` a name neither listed nor found. A repeated call SHALL change nothing.

#### Scenario: Enable an owner integration
- **WHEN** the owner folder holds `dup-scan` and `solo-sdd integrations enable dup-scan` runs in a project
- **THEN** `solo-sdd config get integrations` prints `dup-scan` and the other lines of `solo-sdd/config` keep their bytes

#### Scenario: Enable twice, then disable
- **WHEN** `enable marker-check` runs twice and then `disable marker-check` runs
- **THEN** after the second enable the file is unchanged, and after disable `integrations` holds no `marker-check`

#### Scenario: Enable a broken one
- **WHEN** `enable marker-check` runs and its description has an unknown key
- **THEN** exit 1 naming the file, the line and the key; `solo-sdd/config` is unchanged

#### Scenario: Disable a bundled one
- **WHEN** `integrations disable antislop` runs
- **THEN** only the `integrations.off` line changes, and it holds `antislop`
