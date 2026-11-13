# Proposal

## Why

Users cannot remove old projects; the list grows without end.

## What Changes

- `DELETE /projects/{id}` removes the project with that id and its files.

## Capabilities

### New Capabilities

### Modified Capabilities
- `projects`: a project can be deleted.

## Impact

`app/routes/projects.py`, `tests/test_projects.py`.

## Out of Scope

- Restoring a deleted project.

## Depends On

none

## Source

"Add a way to delete a project" (the owner, 09.11.2026)
