# integration-doctor Specification

## Purpose
Makes the integrations of a project visible and their failures loud: `doctor` lists each enabled integration with its source, points, tool and last run, and a broken description reaches both `doctor` and the session context.

## Requirements

### Requirement: Doctor integration rows
Inside a project `solo-sdd doctor` SHALL print one row `ok|warn integration <name>: <source>, points <points>, requires <program> found|missing, last run <PASS|FAIL> <date>|none` per enabled integration, `warn` when the program is missing; a project integration's row SHALL also give its command. With nothing enabled it SHALL print `ok integrations: none enabled`.

#### Scenario: A project integration
- **WHEN** `marker-check` is enabled, its `requires` program is on `PATH` and its last record is a PASS
- **THEN** `doctor` prints an `ok integration marker-check: project` row with its points, `found`, `last run PASS <date>` and its command

#### Scenario: A missing tool
- **WHEN** `requires: no-such-tool` and the program is not on `PATH`
- **THEN** the row is `warn` and says `requires no-such-tool missing`

### Requirement: Doctor broken integration
An enabled name with no folder, or a project integration or an enabled owner integration whose description is refused, SHALL give a `fail` row naming the file, the line and the key, and `doctor` SHALL exit 1; the rows of the other integrations SHALL still be printed.

#### Scenario: A broken description
- **WHEN** line 3 of `solo-sdd/integrations/marker-check/integration` has an unknown key
- **THEN** `doctor` prints a `fail integration marker-check` row naming `solo-sdd/integrations/marker-check/integration:3` and the key, and exits 1

### Requirement: Integration errors in the session context
The SessionStart `context` hook SHALL add one line `integration errors: <file>:<line> <key>` (the first error, and the count when there are more) when a project integration or an enabled owner integration has a broken description, or an enabled name has no folder; no line otherwise. An error of the hook's own read SHALL be logged and SHALL NOT drop the rest of the context.

#### Scenario: A broken description at start
- **WHEN** a session starts in a project whose `marker-check` description has an unknown key on line 3
- **THEN** the context has `integration errors: solo-sdd/integrations/marker-check/integration:3` with the key

#### Scenario: All descriptions valid
- **WHEN** every found integration reads
- **THEN** the context has no integration errors line

#### Scenario: A broken owner integration not enabled
- **WHEN** an owner integration that the project does not enable has a broken description
- **THEN** the context has no integration errors line
