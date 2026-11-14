# Proposal

## Why

`solo-sdd init` writes the rules block into a project's `AGENTS.md` and records its digest in `solo-sdd/rules-block`; a repeated `init` refreshes a block nobody edited. After a package update nothing tells the person that every project they prepared still carries the rules of the older version: `doctor` checks the home copies, not the project block, so agents keep working by old rules until someone happens to rerun `init`. The update check of `update-check` needs this signal to finish an update in a project.

## What Changes

- The decision of `init.project_rules` (ok, older and safe to refresh, edited in place, broken markers, markers erased, no block) is computed by a function that writes nothing; `init` keeps its output and writes.
- `solo-sdd doctor` in a project with `rules.scope: project` prints one `project-rules` line: `ok` for a current block; `warn ... from an older solo-sdd; refresh: solo-sdd init` for an unedited older block; `warn ... edited in place` with the path of the rules of this version for an edited one; the broken and erased markers as `init` names them. Under `rules.scope: global`, or outside a project, no line.

## Capabilities

### New Capabilities

### Modified Capabilities
- `rules-scope`: Stale project rules named is added.

## Impact

- `solo_sdd/init.py`, `solo_sdd/doctor.py`
- `docs/first-project.md`
- `tests/test_init.py`, `tests/test_cli.py`, `tests/affected.json`

## Out of Scope

- Showing the line in the home menu and refreshing from it after an update: `update-check`.
- Refreshing the blocks of every project on the machine at once: solo-sdd keeps no list of prepared projects.
- The settings screens: `settings-tui`, `settings-tui-lists`, `settings-tui-home`, `cli-menu`.

## Depends On

none

## Source

The owner, 2026-11-14 (translated from Russian): "Will the CLI watch for updates and update the version on launch?", then on adding the update check: "Yes, add it. Think ahead, damn it, about how to make it better".
