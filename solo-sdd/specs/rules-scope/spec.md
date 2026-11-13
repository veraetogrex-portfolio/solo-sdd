# rules-scope Specification

## Purpose
Decides where the solo-sdd rules are written, so they apply to the projects that chose solo-sdd and to nothing else unless the user asks.

## Requirements

### Requirement: Global rules opt-in
`solo-sdd install` SHALL write the global rules block only with `--global-rules` or when the state records an earlier global deployment. `uninstall --global-rules` SHALL remove only that block by the managed block rules.

#### Scenario: A new user
- **WHEN** `solo-sdd install` runs on a clean home
- **THEN** `~/AGENTS.md`, `~/.codex/AGENTS.md` and `~/.claude/CLAUDE.md` are not created or changed

#### Scenario: An existing deployment
- **WHEN** the state records the global block from an earlier version
- **THEN** `install` updates the block as before

### Requirement: Project rules block
`solo-sdd init` SHALL write the rules as a managed block into the project's `AGENTS.md`, keeping the bytes outside the block, and SHALL create `CLAUDE.md` with the line `@AGENTS.md` when the project has none. An edited block SHALL be `drift` and SHALL NOT be overwritten.

#### Scenario: A project with own rules
- **WHEN** `AGENTS.md` has the team's own text and no markers
- **THEN** after `init` the text is unchanged at the start and the solo-sdd block is at the end

#### Scenario: An edited block
- **WHEN** a person changed a line inside the project block, and `init --reconfigure` runs
- **THEN** the block is left as is and named as `drift`

### Requirement: Rules scope setting
The settings key `rules.scope` SHALL take `project` (default) or `global`; with `project`, `init` writes the project block; with `global`, it writes none and names the global block as the source.

#### Scenario: Global scope
- **WHEN** `rules.scope: global` and `init` runs
- **THEN** `AGENTS.md` gets no block, the output names the global rules
