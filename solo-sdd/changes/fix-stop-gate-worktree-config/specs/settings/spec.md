## MODIFIED Requirements

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

#### Scenario: A worktree with its own config
- **WHEN** the session runs in a worktree whose committed `solo-sdd/config` has `hooks.stop.open-pr: off`, the main checkout's file has `on`, and the session pushed a branch with an open PR
- **THEN** the stop is not blocked for the open PR

#### Scenario: A worktree without a config file
- **WHEN** the repository ignores `solo-sdd/config`, the session runs in a worktree that has no such file, and the main checkout's file has `delivery.merge-by: human`
- **THEN** the main checkout's file applies, and the stop is not blocked for the open PR
