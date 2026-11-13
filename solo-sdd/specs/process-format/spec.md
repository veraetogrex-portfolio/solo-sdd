# process-format Specification

## Purpose
Defines where a project keeps its solo-sdd process and which rules `solo-sdd validate` enforces, so the process runs without any external spec tool.

## Requirements

### Requirement: Process tree
A project's process SHALL live in `solo-sdd/`: `project.md`, optional `analyze.md`, main specs `specs/<capability>/spec.md`, open changes `changes/<id>/` and archived changes `changes/archive/YYYY-MM-DD-<id>/`. A missing `project.md` SHALL be an error. A change folder SHALL hold `proposal.md`, `verification.md`, `tasks.md`, optional `design.md` and delta specs `specs/<capability>/spec.md`.

#### Scenario: A valid tree
- **WHEN** a project has `solo-sdd/project.md`, one main spec and one change with all required artifacts
- **THEN** `solo-sdd validate --all` exits with code 0 and prints `0 errors`

#### Scenario: A missing artifact
- **WHEN** the change `demo` has no `verification.md`
- **THEN** exit code 1, the error line names `demo` and `verification.md`

#### Scenario: No project file
- **WHEN** `solo-sdd/` has no `project.md`
- **THEN** exit code 1, the error names `solo-sdd/project.md`

### Requirement: Proposal and acceptance sections
`solo-sdd validate` SHALL fail a change whose `proposal.md` lacks or leaves empty any of `## Why`, `## What Changes`, `## Impact`, `## Out of Scope`, `## Depends On`, `## Source`, or whose `verification.md` lacks or leaves empty `## Live Scenario`, `## Needs` or `## Fallback`. An HTML comment alone counts as empty. In `proposal.md`, `verification.md` and `tasks.md` a header, task or line inside an HTML comment SHALL NOT count, nor a header inside a code block; `<!--` in code is not a comment.

#### Scenario: No Source
- **WHEN** `proposal.md` of `demo` has no `## Source`
- **THEN** exit code 1, the error names the file and `Source`

#### Scenario: A header inside a comment
- **WHEN** `## Source` of `demo` stands only inside `<!-- … -->`
- **THEN** exit code 1, the error names `Source` as missing

#### Scenario: A template comment only
- **WHEN** `## Out of Scope` holds only the template comment
- **THEN** exit code 1, the error names `Out of Scope` as empty

### Requirement: Task list limits
`solo-sdd validate` SHALL fail a change whose `tasks.md` has more than 10 checkbox tasks or whose last `##` group is not `Acceptance`.

#### Scenario: Eleven tasks
- **WHEN** `tasks.md` has 11 lines `- [ ] …`
- **THEN** exit code 1, the error names the file and the count 11

#### Scenario: No Acceptance group
- **WHEN** the last group of `tasks.md` is `## 2. Docs`
- **THEN** exit code 1, the error names the missing `Acceptance` group

### Requirement: Requirement format
`solo-sdd validate` SHALL fail a main spec or delta with a requirement text over 500 characters, a requirement without a scenario, a `#### Scenario:` with a body but no WHEN or GIVEN step or no THEN step, a delta requirement outside `ADDED`, `MODIFIED`, `REMOVED`, `RENAMED Requirements`, or a header without a space (`###Requirement:`). A main requirement that an open change modifies or removes SHALL NOT be length-checked in the main spec; a modifying delta is checked instead.

#### Scenario: A long requirement
- **WHEN** a requirement text has 501 characters
- **THEN** exit code 1, the error names the file, the requirement and the length

#### Scenario: A scenario without THEN
- **WHEN** a scenario has only `- **WHEN** …`
- **THEN** exit code 1, the error names the requirement, the scenario and the missing THEN

#### Scenario: An unknown delta section
- **WHEN** a delta requirement stands under `## DEPRECATED Requirements`
- **THEN** exit code 1, the error names the file and the section

#### Scenario: Same verdict as the removed tests
- **WHEN** `validate` runs on the toy tree on which the removed `tests/test_spec_length.py` and `tests/test_spec_format.py` reported six "file - requirement or section" pairs, one violation of each kind they checked
- **THEN** it reports the same six pairs, fixed in `tests/test_process_format.py`

### Requirement: New capability purpose
A delta for a capability with no main spec and no delta in an open change named in its `Depends On` SHALL start with `## Purpose` of at least 50 characters. A change with no delta requirement (an empty delta file or one with only `## Purpose` counts as none) SHALL pass only if its `proposal.md` has the line `Specs: none` under `## Capabilities`.

#### Scenario: A new capability without Purpose
- **WHEN** a change adds `specs/new-thing/spec.md` and `solo-sdd/specs/new-thing/` does not exist, and the delta has no `## Purpose`
- **THEN** exit code 1, the error names the capability and `Purpose`

#### Scenario: A capability brought by a dependency
- **WHEN** change `b` names change `a` in `Depends On`, `a` adds `specs/new-thing/spec.md` with `## Purpose`, and the delta of `b` for `new-thing` has none
- **THEN** no Purpose error for `b`

#### Scenario: A change without deltas
- **WHEN** a change has no `specs/` folder and its proposal has `Specs: none`
- **THEN** no error for missing deltas; without the line, exit code 1

### Requirement: Validate output
`solo-sdd validate` SHALL print one line per error `<file>: <rule>: <item>`, then `<n> errors`, and exit 1 on any error, else 0. `--json` SHALL print a list of objects with `file`, `rule`, `item`. `<id>` SHALL check one change; outside a project with `solo-sdd/` it SHALL print `no solo-sdd/ tree` and exit 1. It SHALL call no external program.

#### Scenario: Without OpenSpec
- **WHEN** `validate --all` runs with `PATH=/usr/bin:/bin` and no OpenSpec program anywhere
- **THEN** it checks the tree and exits by its verdict

#### Scenario: JSON
- **WHEN** `validate --all --json` runs on a tree with two errors
- **THEN** a JSON list of two objects with `file`, `rule`, `item`

#### Scenario: No tree
- **WHEN** `validate` runs in a folder without `solo-sdd/`
- **THEN** the line `no solo-sdd/ tree`, exit code 1

### Requirement: Validate scope
`solo-sdd validate --all` SHALL check `project.md`, every main spec and every open change, and SHALL NOT check archived changes: the archive is history written under earlier rules.

#### Scenario: An old archived change
- **WHEN** an archived change has a 600-character requirement and everything else is valid
- **THEN** `validate --all` exits with code 0

### Requirement: Validate dry-runs deltas
`solo-sdd validate` SHALL apply each change's deltas to the main specs in memory, writing nothing, and report as errors the problems `archive` would refuse on: a MODIFIED, REMOVED or RENAMED name missing from the main spec, an ADDED name already in it, each with the rule `delta`. The deltas of the open changes in `Depends On` SHALL be applied first, in their order, each after its own open dependencies and each once, so a name they add counts as present and a name they remove or rename as absent.

#### Scenario: A missing name
- **WHEN** a delta modifies `### Requirement: Missing`, which the main spec does not have
- **THEN** `validate <id>` reports an error naming the file and `Missing`, exit 1, no file is written

#### Scenario: Provided by a dependency
- **WHEN** change `b` has `a` in `Depends On` and modifies a requirement that `a` adds
- **THEN** `validate b` reports no error for that name

#### Scenario: A dependency chain
- **WHEN** `c3` has `c2` in `Depends On`, `c2` has `c1`, `c1` adds `X1`, `c2` modifies `X1` and adds `X2`, `c3` modifies `X2`
- **THEN** `validate c3` reports no delta error, whether `Depends On` of `c3` names `c2` alone or `c2, c1`

#### Scenario: Validate agrees with archive
- **WHEN** `validate <id>` reports no delta error and no change in its `Depends On` is still open
- **THEN** `archive <id>` refuses on no delta name either
