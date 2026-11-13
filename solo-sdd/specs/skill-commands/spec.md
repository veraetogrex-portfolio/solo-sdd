# skill-commands Specification

## Purpose
Keeps the skills, the algorithm and the global rules on solo-sdd's own commands and process tree, so an agent following them never needs OpenSpec.

## Requirements

### Requirement: No OpenSpec commands in the texts
`skills/*/SKILL.md`, `ALGORITHM.md` and `global/AGENTS.md` SHALL NOT tell the agent to run an `openspec` command or to read a path under `openspec/`; they SHALL use `solo-sdd new`, `validate`, `list`, `archive` and paths under `solo-sdd/`. The only allowed mention is the hint `solo-sdd import openspec`.

#### Scenario: The texts
- **WHEN** `tests/test_skill_commands.py` scans the deployed texts
- **THEN** no line runs `openspec` or names `openspec/`, except lines with `solo-sdd import openspec`

#### Scenario: An old line comes back
- **WHEN** a skill gets the line `openspec validate --all --strict`
- **THEN** the test fails and names the file and the line

### Requirement: Writing rules in spec-plan
`spec-plan` SHALL itself state the artifact rules an agent needs to write a change that `solo-sdd validate` accepts: the proposal and verification sections, `## Purpose` for a new capability, a whole `MODIFIED` block, at most 10 tasks with the two `Acceptance` tasks, and `Specs: none` for a change without deltas.

#### Scenario: A plan by the skill alone
- **WHEN** an agent follows `spec-plan` in a project without `openspec` and writes one change for a toy request
- **THEN** `solo-sdd validate --all` passes on the first run

### Requirement: No deployment from spec-next
`spec-next` SHALL NOT rebuild a schema or deploy skills and rules as a step of a run.

#### Scenario: Step list
- **WHEN** `spec-next` is read
- **THEN** it names no `openspec-after-update.py` and no `sync.py push` call

### Requirement: Legacy tree in the skills
When a project has `openspec/` and no `solo-sdd/`, `spec-plan`, `spec-next`, `spec-analyze` and `spec-dispatch` SHALL stop before any change work and name `solo-sdd import openspec` as the next step; they SHALL NOT import by themselves.

#### Scenario: A project not yet moved
- **WHEN** `spec-next` starts in a project with only `openspec/changes/`
- **THEN** it names `solo-sdd import openspec` and changes no file
