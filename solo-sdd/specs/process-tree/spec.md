# process-tree Specification

## Purpose
Defines how the solo-sdd hooks and scripts find a project's process tree, so they work the same on the own `solo-sdd/` tree and, until import, on an `openspec/` one.

## Requirements

### Requirement: Process root
Every hook and script of solo-sdd SHALL take a project's process root as `solo-sdd/` if it exists, otherwise `openspec/`. On an `openspec/` root its output for the user (context, plan, report) SHALL carry the line `process in openspec/: run solo-sdd import openspec`. Both present: `solo-sdd/` wins.

#### Scenario: Own tree
- **WHEN** a project has `solo-sdd/changes/a/` with a `CLAIM` and no `openspec/`
- **THEN** the session context holds the text of `solo-sdd/project.md` and lists `a` with `CLAIM`, the guard refuses another session's edit of `a/tasks.md`

#### Scenario: Legacy tree
- **WHEN** a project has only `openspec/changes/a/`
- **THEN** the context lists `a` and has the line with `solo-sdd import openspec`

### Requirement: Process root in other capabilities
A path under `openspec/` or the command `openspec validate` that another capability of the hooks and scripts names (`orchestrator-status`, `dispatch-tool`, `worktree-env`, `spec-dispatch`, `dispatch-eval`, `work-hooks-subagents`, `change-claim`) SHALL mean the same path under the process root and the command of the requirement Validation command by tree.

#### Scenario: Merge check on the own tree
- **WHEN** `sdd-dispatch.py land-local` merges a change into a main folder with `solo-sdd/`
- **THEN** after the `--check` commands it runs `solo-sdd validate --all` in the main folder, not `openspec validate`

### Requirement: Validation command by tree
The status acceptance and the dispatch SHALL validate a `solo-sdd/` tree with the `solo-sdd` command or, without it, `python3 -m solo_sdd`, as `validate --all`, and SHALL NOT call `openspec` for it. Neither available SHALL fail the field with `solo-sdd not found`.

#### Scenario: Acceptance on the own tree
- **WHEN** `sdd-dispatch.py accept` checks a worktree with `solo-sdd/` and no `openspec` in `PATH`
- **THEN** the `VALIDATE` command is `solo-sdd validate --all`, and its exit code decides the field

#### Scenario: Package without the command
- **WHEN** there is no `solo-sdd` in `PATH` and `python3 -m solo_sdd` works
- **THEN** the field is decided by `python3 -m solo_sdd validate --all`

### Requirement: Archive command recognised
The status guard SHALL treat `solo-sdd archive <id>` like `openspec archive <id>`: the archive folder is looked up in the process root's `changes/archive/`, and a change still in `changes/<id>/` is reported as not archived.

#### Scenario: Archived by solo-sdd
- **WHEN** a handback says `archived` for `demo` and `solo-sdd/changes/archive/2026-11-10-demo/` exists
- **THEN** the guard accepts the archive field
