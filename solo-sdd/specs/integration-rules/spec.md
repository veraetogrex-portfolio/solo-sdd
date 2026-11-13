# integration-rules Specification

## Purpose
Carries the text of an integration to the agents: rules into the solo-sdd block of the project's `AGENTS.md`, and review or audit material to the reviewer of `spec-next` and to `spec-audit`, always as data the agent reads, never as commands it runs.

## Requirements

### Requirement: Integration rules in the project block
For each enabled integration with a `rules.md`, the solo-sdd block of `AGENTS.md` SHALL end with a section `## Integration: <name>` holding that file, in name order; an empty or blank `rules.md` gives no section. `solo-sdd init`, `integrations enable` and `integrations disable` SHALL rewrite the block; text outside it SHALL keep its bytes. Under `rules.scope: global` no section SHALL be written and the command SHALL print that the rules were not written.

#### Scenario: Enable adds the section
- **WHEN** `marker-check` has a `rules.md` and `integrations enable marker-check` runs
- **THEN** the block of `AGENTS.md` ends with `## Integration: marker-check` and the file text, and the lines outside the block are unchanged

#### Scenario: Disable removes it
- **WHEN** `integrations disable marker-check` runs afterwards
- **THEN** the block has no `## Integration: marker-check` section

### Requirement: Rules without a project block
`integrations enable` and `disable` SHALL rewrite only an existing solo-sdd block: an `AGENTS.md` without one SHALL stay as it is (no file is created), and when an enabled integration has rules the command SHALL print that they were not written and name `solo-sdd init`. A block edited in place SHALL stay as it is and be named as `drift`, as `init` does.

#### Scenario: No block yet
- **WHEN** the project has no `AGENTS.md` and `integrations enable marker-check` runs
- **THEN** it exits 0, no `AGENTS.md` is created, and the output says the rules of `marker-check` were not written and names `solo-sdd init`

### Requirement: Rules text refused
A `rules.md` that holds a solo-sdd block marker line, is a link or not a regular file, is not valid UTF-8 or is over 8 KB SHALL be refused naming the file and the reason. Only the rules of the integrations enabled after the call SHALL be read, and on a refusal `AGENTS.md` and `solo-sdd/config` SHALL be left unchanged and the command SHALL exit 1.

#### Scenario: A marker inside the rules
- **WHEN** `rules.md` holds the line `<!-- solo-sdd:end -->`
- **THEN** `integrations enable marker-check` exits 1 naming the file and the marker, and `AGENTS.md` and `solo-sdd/config` keep their bytes

#### Scenario: Disabling the broken one
- **WHEN** the enabled `marker-check` has a broken `rules.md` and `integrations disable marker-check` runs
- **THEN** its section is removed and the command exits 0

### Requirement: Review and audit material
`solo-sdd check --point review|audit [--changed]` SHALL start no command and print `MATERIAL <name>: <path>` for each enabled integration of that point whose `applies` matches, `<path>` being the absolute path of its `material` file; `no integrations enabled` when there is none. A listed name with no folder, a broken description or a missing material file SHALL print `FAIL <name>: <reason>` and exit 1.

#### Scenario: Material listed
- **WHEN** `style-notes` is enabled with `points: review` and `material: method.md`
- **THEN** `check --point review` prints `MATERIAL style-notes:` with the path of `method.md`, and no process is started

### Requirement: Material reaches the reviewer and the auditor
`spec-next` step 7a SHALL hand the reviewer the files that `check --point review --changed` lists, and `spec-audit` SHALL read the files that `check --point audit` lists, each as a method to apply; an instruction in that text to run, fetch or change something SHALL NOT be followed.

#### Scenario: Skill texts name the material
- **WHEN** the laid-out `spec-next` and `spec-audit` skills are read
- **THEN** step 7a lists the `review` material among what the reviewer gets, `spec-audit` reads the `audit` material, and both say its instructions are not executed
