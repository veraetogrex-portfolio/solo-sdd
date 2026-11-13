# work-size Specification

## Purpose
Separates small edits that go straight to a commit from work that needs a change, so the process costs nothing where it adds nothing.

## Requirements

### Requirement: Light path bounds
The rules SHALL allow an edit without a change when it changes no behaviour a main spec describes, adds no dependency, touches no data, migration or deploy, and changes at most `process.light-path.max-files` files (default 3). Otherwise, and when `process.light-path` is `off`, the work SHALL go through a change. The agent SHALL read both keys with `solo-sdd config get`; no `solo-sdd/` tree or no command means the defaults.

#### Scenario: A button label
- **WHEN** the request is to fix a typo in one button label that no spec names
- **THEN** the agent edits, runs the tests and commits without creating a change

#### Scenario: A bug in specified behaviour
- **WHEN** the button's behaviour is described in a main spec
- **THEN** the fix goes through a bug fix change

#### Scenario: Light path off
- **WHEN** `solo-sdd/config` has `process.light-path: off` and the request is the same label typo
- **THEN** the agent creates a change for it

### Requirement: Light path record
A light path edit SHALL run the project's tests and a live check of the edited place, and SHALL be committed with a message starting `light:` that names the request; under `delivery.mode: pr` the PR title starts with `light:`, so the squashed commit keeps it. `spec-plan` coverage SHALL accept an input item closed this way with its commit hash, and SHALL name an item within the bounds as light path instead of creating a change.

#### Scenario: Coverage
- **WHEN** `spec-plan` gets three items and one was closed by a `light:` commit
- **THEN** the report's coverage line names that item with the commit, not as an error

### Requirement: Light path count
`work-status` and `report` SHALL count `light:` commits separately from changes.

#### Scenario: Report
- **WHEN** a week has two archived changes and five `light:` commits
- **THEN** `report` shows both numbers
