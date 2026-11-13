# change-claim Specification

## Purpose
The `CLAIM` marker in a change folder says an agent runs the change; the Claude Code write hook places it, recognises its own and does not let anyone edit another's change.

## Requirements

### Requirement: Claim on first done task
The write hook SHALL place `CLAIM` in the change folder of the main project folder itself only on an edit of this change's `tasks.md` that increases the number of checked tasks (`- [x]`). An edit of other change files or of `tasks.md` without new checks does not place the marker. If a `CLAIM` already stands and it is someone else's, the hook SHALL forbid editing any file of the change, as before; `WAITING` still forbids editing too.

#### Scenario: Analysis edits artifacts
- **WHEN** a session without a marker edits `proposal.md`, `specs/…/spec.md` and adds an unchecked task to `tasks.md`
- **THEN** the edits pass, no `CLAIM` appeared

#### Scenario: The first checked task
- **WHEN** a session without a marker checks task `1.1` in `tasks.md`
- **THEN** the edit passes, the change folder of the main folder got a `CLAIM` with this session's id

#### Scenario: Someone else's marker
- **WHEN** the change has a `CLAIM` of another session, and this session edits its `proposal.md`
- **THEN** the edit is forbidden with the previous text about a taken change
