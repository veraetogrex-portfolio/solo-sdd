## MODIFIED Requirements

### Requirement: Test command under dispatcher
If the project's `AGENTS.md` has a "Working copy" section or `solo-sdd/config` sets a `worktree.` or `dispatch.` key, `project-init` SHALL write the test command in the "Commands" section with the thread limit `max(1, ⌊cores / N⌋)`, where N is `dispatch.limit` through `solo-sdd config get` (default 2): for vitest and jest `--maxWorkers`, for pytest-xdist `-n`. Without them, or a test runner that cannot limit threads, the command is written without a flag.

#### Scenario: Vitest under the dispatcher
- **WHEN** the project has vitest, the computer has 8 cores, "Working copy" with "Orchestrators: 2"
- **THEN** "Commands" has the test command with `--maxWorkers=4`

#### Scenario: A project without the dispatcher
- **WHEN** there is no "Working copy" section
- **THEN** the test command has no thread limit flag

#### Scenario: Without the "Orchestrators:" item
- **WHEN** the project has vitest, the computer has 8 cores, "Working copy" without the item "Orchestrators:"
- **THEN** "Commands" has the test command with `--maxWorkers=4`

#### Scenario: The old item still counts
- **WHEN** the project has vitest, the computer has 8 cores, "Working copy" with "Orchestrators: 4", and no `solo-sdd/config` value
- **THEN** "Commands" has the test command with `--maxWorkers=2`

#### Scenario: The limit from the config
- **WHEN** the project has vitest, the computer has 8 cores, and `solo-sdd/config` has `dispatch.limit: 4` with `worktree.links: node_modules`
- **THEN** "Commands" has the test command with `--maxWorkers=2`

## ADDED Requirements

### Requirement: Working copy values in the settings
When `project-init` decides working copy values (paths to copy, a prepare or after-refresh command, shared paths, loopback, the orchestrator limit), it SHALL write them with `solo-sdd config set` into `solo-sdd/config` and SHALL NOT create a "Working copy" section; an existing "Working copy" section SHALL stay as written.

#### Scenario: A new project with dependencies
- **WHEN** `project-init` runs in a project without "Working copy" whose worktrees need `npm ci`
- **THEN** `solo-sdd/config` has `worktree.prepare: npm ci`, and `AGENTS.md` has no "Working copy" section
