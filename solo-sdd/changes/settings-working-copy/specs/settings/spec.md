## ADDED Requirements

### Requirement: Working copy settings
`worktree.paths`, `worktree.prepare` and `worktree.after-refresh` (text), `worktree.links` (default `node_modules, .venv`), `dispatch.shared`, `dispatch.loopback` (`off`) and `dispatch.check-timeout` (600) SHALL be read by `sdd-worktree.py`, `sdd-dispatch-plan.py` and `sdd-dispatch.py`. A `node_modules` item SHALL be linked as today (up to three levels deep), another `worktree.links` item at its path from the root. A valid `SDD_DISPATCH_TIMEOUT` SHALL win over `dispatch.check-timeout`.

#### Scenario: A prepare command from the config
- **WHEN** the file has `worktree.prepare: npm ci` and `AGENTS.md` has no "Working copy" section
- **THEN** `sdd-worktree.py setup` runs `npm ci` in the worktree and its summary line names it

#### Scenario: Another linked folder
- **WHEN** the file has `worktree.links: node_modules, vendor/bundle`, and the main folder has `vendor/bundle/` and `.venv/`
- **THEN** after `sdd-worktree.py setup` the worktree's `vendor/bundle` is a link to the main folder's, and `.venv` is not a link

#### Scenario: The variable wins
- **WHEN** the file has `dispatch.check-timeout: 900` and `SDD_DISPATCH_TIMEOUT=5`
- **THEN** a hanging check in `land-local` names `timeout after 5 s`

#### Scenario: An invalid variable
- **WHEN** the file has `dispatch.check-timeout: 2` and `SDD_DISPATCH_TIMEOUT=abc`
- **THEN** a hanging check in `land-local` names `timeout after 2 s`

### Requirement: Working copy items as the old source
Without a file value, `dispatch.limit` and each key of Working copy settings except `worktree.links` and `dispatch.check-timeout` SHALL take its `AGENTS.md` item, source `AGENTS.md`: "Paths:", "Prepare:", "After refresh:", "Shared:" (backquoted values) and "Orchestrators:" (the first number) of "Working copy"; "Loopback: needed" of "Working copy" or "Commands" as `on`. A value the key refuses SHALL not be taken and SHALL be named on stderr with `AGENTS.md:<line>`.

#### Scenario: The old item
- **WHEN** there is no file value and "Working copy" has "Shared: `CHANGELOG.md`"
- **THEN** `config get dispatch.shared` prints `CHANGELOG.md` with `source: AGENTS.md`

#### Scenario: The old limit
- **WHEN** there is no file value and "Working copy" has "Orchestrators: 4"
- **THEN** `config get dispatch.limit` prints `4` with `source: AGENTS.md`

#### Scenario: Loopback declared under Commands
- **WHEN** there is no file value and "Commands" has the item "Loopback: needed"
- **THEN** `config get dispatch.loopback` prints `on` with `source: AGENTS.md`

#### Scenario: A refused old value
- **WHEN** there is no file value and "Working copy" has "Paths: `/etc/hosts`, `docs/a.md`"
- **THEN** `config get worktree.paths` prints `docs/a.md`, and stderr names `AGENTS.md:<line>` and `/etc/hosts`
