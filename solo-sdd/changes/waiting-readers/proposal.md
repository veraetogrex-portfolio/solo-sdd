# Proposal

## Why

`work-pull` (2026-11-22) gave `docs/waiting.md` a second table, `## Closed`, and taught `report` to read only the first one. Its review round 1 found five more skills, and `ALGORITHM.md` ("The waiting table") and section 4 of the global rules, that read or write the file without naming the first table: `context-resume` reports every row as a blocker, so closed rows come back as waiting; `project-init` writes "one line in the `docs/waiting.md` table" and deletes its `DESIGN.md` row when no empty fields are left, against the template's "a row is never deleted"; `spec-next` (with its step file `closing.md`), `spec-plan` and `blockers` add "a line in `docs/waiting.md`" that may land under `## Closed`.

## What Changes

- `context-resume` takes its blockers only from the first table of `docs/waiting.md`.
- `spec-next`, `spec-plan`, `blockers` and `project-init` write a new waiting row into the first table.
- `project-init` moves its met `DESIGN.md` row to `## Closed` with the evidence `DESIGN.md: no empty fields` and the date instead of deleting it; a later empty field gets a new row in the first table.
- `ALGORITHM.md` (the blocker rule, the external remainder, the `WAITING` and waiting-table rows) and section 4 of `global/AGENTS.md` name the first table.
- The template `templates/docs/waiting.md` names `project-init` as the mover of its own `DESIGN.md` row.
- A stand `tests/stands/waiting-readers.py` grades subagent runs of `context-resume`, `blockers` and `project-init` on a copy of the `next-up` fixture.

## Capabilities

### New Capabilities

### Modified Capabilities
- `next-up`: the requirement "Readers of waiting lines" names every skill besides `next-up` that reads or writes the waiting rows of `docs/waiting.md` (`spec-dispatch` writes only its `## Run decisions` section, not rows).
- `ui-direction`: the requirements "Project design direction" and "Design file rerun" write the `DESIGN.md` row into the first table; "Design file rerun" moves the met `DESIGN.md` row to `## Closed` instead of deleting it.

## Impact

- `skills/context-resume/SKILL.md`
- `skills/project-init/SKILL.md`
- `skills/spec-next/SKILL.md`
- `skills/spec-plan/SKILL.md`
- `skills/blockers/SKILL.md`
- `skills/spec-next/closing.md`
- `ALGORITHM.md`
- `global/AGENTS.md`
- `templates/docs/waiting.md`
- `tests/test_skill_commands.py`
- `tests/stands/waiting-readers.py`
- `tests/stands/waiting-readers/`

## Out of Scope

- The `next-up` skill itself and the `report` skill: done in `work-pull`.

## Depends On

- work-pull

## Source

The owner, 2026-11-20, in the `Source` of `work-pull` (translated from Russian): "`next-up` closes a `docs/waiting.md` line itself if it found evidence". The finding that leads here: `solo-sdd/changes/archive/2026-11-22-work-pull/verification.md`, Decisions Without Owner, 2026-11-22: "review round 1, Important 3 (other readers and writers of `docs/waiting.md`: `context-resume`, `project-init`, `spec-next`, `spec-plan`, `blockers`) → outside this change's delta, moved to the new change `waiting-readers` (Depends On `work-pull`)."
