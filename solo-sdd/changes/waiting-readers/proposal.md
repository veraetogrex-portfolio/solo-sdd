# Proposal

## Why

`work-pull` (2026-11-22) gave `docs/waiting.md` a second table, `## Closed`, and taught `report` to read only the first one. Its review round 1 found five more skills, and `ALGORITHM.md` ("The waiting table") and section 4 of the global rules, that read or write the file without naming the first table: `context-resume` reports every row as a blocker, so closed rows come back as waiting; `project-init` writes "one line in the `docs/waiting.md` table" and deletes its `DESIGN.md` row when no empty fields are left, against the template's "a row is never deleted"; `spec-next` (with its step file `closing.md`), `spec-plan` and `blockers` add "a line in `docs/waiting.md`" that may land under `## Closed`.

## What Changes

- `context-resume` takes its blockers only from the first table of `docs/waiting.md`.
- `spec-next`, `spec-plan`, `blockers` and `project-init` write a new waiting row into the first table.
- `project-init` moves its met `DESIGN.md` row to `## Closed` instead of deleting it.

## Capabilities

### New Capabilities

### Modified Capabilities
- `next-up`: the requirement "Readers of waiting lines" names every skill that reads or writes `docs/waiting.md`.

## Impact

- `skills/context-resume/SKILL.md`
- `skills/project-init/SKILL.md`
- `skills/spec-next/SKILL.md`
- `skills/spec-plan/SKILL.md`
- `skills/blockers/SKILL.md`
- `skills/spec-next/closing.md`
- `ALGORITHM.md`
- `global/AGENTS.md`
- `tests/test_skill_commands.py`

## Out of Scope

- The `next-up` skill itself and the `report` skill: done in `work-pull`.

## Depends On

- work-pull

## Source

Review round 1 of `work-pull`, 2026-11-22, finding Important 3 (outside that change's delta).
