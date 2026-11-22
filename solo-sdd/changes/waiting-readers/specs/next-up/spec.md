## MODIFIED Requirements

### Requirement: Readers of waiting lines
The `report` and `context-resume` skills SHALL take what waits only from the first table of `docs/waiting.md`; `spec-next`, `spec-plan`, `blockers` and `project-init` SHALL add a waiting row to the first table. The `docs/waiting.md` template SHALL say that only the first table waits, that a met row moves to `## Closed`, and that the `WAITING` file of its change is then removed by the owner on `next-up`'s proposal.

#### Scenario: A report after a closing
- **WHEN** `docs/waiting.md` has rows under `## Closed`
- **THEN** step 5 of `report` and the Blockers line of `context-resume` read the first table only, so no closed row is reported as waiting

#### Scenario: A new waiting row
- **WHEN** `docs/waiting.md` has a `## Closed` table and `blockers` adds a waiting row
- **THEN** the row goes into the first table, and the `## Closed` table keeps its rows unchanged
