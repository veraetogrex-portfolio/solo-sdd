## ADDED Requirements

### Requirement: Stale project rules named
`solo-sdd doctor` in a project with `rules.scope: project` SHALL print one `project-rules` line by the same decision `init` makes, without writing: `ok` for a current block, `warn` naming `solo-sdd init` for an unedited block of an older version, `warn` naming the rules of this version for an edited block or broken or erased markers. Under `rules.scope: global` or outside a project it SHALL print no such line.

#### Scenario: After an update
- **WHEN** the block was written by an older version, `solo-sdd/rules-block` holds its digest, and the installed rules differ
- **THEN** `doctor` prints `warn project-rules:` naming `solo-sdd init`, and `AGENTS.md` keeps its bytes

#### Scenario: Refresh clears it
- **WHEN** after that `solo-sdd init` runs
- **THEN** the block is updated and `doctor` prints `ok project-rules:`

#### Scenario: Edited block
- **WHEN** a person changed a line inside the block
- **THEN** `doctor` prints `warn project-rules:` naming the block as edited in place and the path of the rules of this version, not `solo-sdd init`

#### Scenario: Global scope
- **WHEN** the config has `rules.scope: global`
- **THEN** `doctor` prints no `project-rules` line
