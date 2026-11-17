## ADDED Requirements

### Requirement: Stop gate switches
The `stop` hook SHALL skip the gate of `hooks.stop.uncommitted`, `hooks.stop.unarchived`, `hooks.stop.open-pr` or `hooks.stop.ui-check` when the repository that gate checks sets it to `off`; under `delivery.merge-by: human` the open PR gate stays off whatever its switch. `hooks.auto-claim: off` SHALL stop a `tasks.md` tick from creating `CLAIM`; a foreign `CLAIM` or a `WAITING` is still refused. Each defaults to `on`; a broken config SHALL keep every gate on and write `errors.log`.

#### Scenario: A project without interface checks
- **WHEN** the file has `hooks.stop.ui-check: off`, and the session edited `app.css` without a browser check
- **THEN** the stop is not blocked for the interface check

#### Scenario: A broken config
- **WHEN** the file has a broken line, and the session left uncommitted edits
- **THEN** the stop is blocked for the uncommitted edits, and `errors.log` names the line

#### Scenario: A person merges
- **WHEN** the file has `hooks.stop.open-pr: on` and `delivery.merge-by: human`, and the session pushed a branch with an open PR
- **THEN** the stop is not blocked for the open PR

#### Scenario: Settings of the edited repository
- **WHEN** the session runs in repository A, left uncommitted edits in repository B, and only B's file has `hooks.stop.uncommitted: off`
- **THEN** the stop is not blocked for B's edits

#### Scenario: Auto-claim off
- **WHEN** the file has `hooks.auto-claim: off`
- **THEN** a tick in `tasks.md` creates no `CLAIM`, and an edit of a change with another session's `CLAIM` is still refused

### Requirement: Interface settings
`ui.extensions` (default `.html, .htm, .css, .scss, .sass, .less, .tsx, .jsx, .vue, .svelte`) SHALL decide which edited files count as interface for the `stop` hook and `project-init`, and `ui.widths` (default `1280, 390`) SHALL be the widths `ui-check` and `spec-plan` name for a check. An extension other than `.` and letters or digits, or a width other than a whole number from 1, SHALL be refused with exit 1, the file unchanged.

#### Scenario: Templates count as interface
- **WHEN** the file has `ui.extensions: .html, .jinja`, and the session edited `page.jinja` without a browser check
- **THEN** the stop is blocked for the interface check

#### Scenario: A width that is not a number
- **WHEN** `config set ui.widths "1280, wide"` runs
- **THEN** exit 1 names `wide` and whole numbers, the file is unchanged
