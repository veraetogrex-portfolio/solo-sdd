# spec-plan Specification

## Purpose
What the `spec-plan` skill leaves in the project repository.

## Requirements

### Requirement: Plan committed
After gate G1 `spec-plan` SHALL commit the folders of the changes it created and changed in one commit `change: <id>, …`, naming in the commit only these folders. If `solo-sdd/changes` is ignored by git, there is no commit, and the report names it with the line "plan outside git". Others' changes in the tree do not get into the commit.

#### Scenario: The plan is committed
- **WHEN** `spec-plan` created changes `a` and `b`, and the tree has someone else's edit `src/x.py`
- **THEN** the last commit holds only `solo-sdd/changes/a/` and `solo-sdd/changes/b/`, the edit `src/x.py` stayed uncommitted

#### Scenario: Specs are ignored
- **WHEN** `git check-ignore solo-sdd/changes` finds a rule
- **THEN** there is no commit, the report has the line "plan outside git"

### Requirement: Requirement text length
The requirement text in a delta, from the line `### Requirement:` to the first `#### Scenario:`, SHALL be at most 500 chars. `spec-plan` SHALL move examples and edge cases into scenarios, and several behaviours into separate requirements. If a change modifies a long requirement (`MODIFIED`), it SHALL shorten it in the same delta without changing the behaviour. `spec-analyze` SHALL count a requirement longer than 500 chars as a HIGH finding.

#### Scenario: A long new requirement
- **WHEN** `spec-plan` writes a requirement whose text with examples comes out at 700 chars
- **THEN** the examples go into scenarios, the requirement text is at most 500 chars

#### Scenario: Changing a long requirement
- **WHEN** a change edits one phrase in a main spec requirement of 1800 chars
- **THEN** in the `MODIFIED` delta the requirement is at most 500 chars; the rest of the behaviour moved into scenarios or `ADDED` requirements

#### Scenario: An analysis finding
- **WHEN** `spec-analyze` meets a requirement of 620 chars in a delta
- **THEN** a HIGH finding, a fix in the artifact and a line in `Decisions Without Owner`

### Requirement: Map by unit type
When `docs/codebase/` exists, `/spec-plan` SHALL read for each unit only the map files that the type table in the skill names for that unit's type, and a unit whose type is not in the table SHALL read `ARCHITECTURE.md` only. The report SHALL name, per change, the map files read, or `Map: none` when there is no map.

#### Scenario: Bugfix unit
- **WHEN** a plan has one bugfix unit and a map exists
- **THEN** the session reads `ARCHITECTURE.md` and `CONCERNS.md` from `docs/codebase/` and no other map file, and the report names both for that change

#### Scenario: Unit of two types
- **WHEN** a unit is both an interface and an API unit
- **THEN** it reads the union of both rows: CONVENTIONS and ARCHITECTURE, each once

#### Scenario: No map
- **WHEN** `docs/codebase/` does not exist
- **THEN** `/spec-plan` works as before and the report holds `Map: none`

### Requirement: Stale map warning
`/spec-plan` SHALL count the commits since the `Commit:` stamp of each map file it reads that change files outside `docs/` and `solo-sdd/`. More than 20, a stamp commit not in the history of `HEAD`, or no stamp SHALL give the report line `Map stale: <file>, <n> commits since <hash>; refresh: /project-init map` (`<n>` is `unknown` without a count, `<hash>` is `none` without a stamp), and planning SHALL go on with the map.

#### Scenario: 25 commits since the stamp
- **WHEN** 25 commits touching application code were made after the stamp of `ARCHITECTURE.md`
- **THEN** the report holds `Map stale: docs/codebase/ARCHITECTURE.md, 25 commits since <hash>; refresh: /project-init map` and the changes are still created

#### Scenario: Only docs changed
- **WHEN** 30 commits after the stamp changed only files under `docs/` and `solo-sdd/`
- **THEN** there is no `Map stale` line

#### Scenario: Stamp lost
- **WHEN** the stamp names a commit that is not in the history of `HEAD` (rebased away, even if the object is still in the repository)
- **THEN** the line `Map stale: <file>, unknown commits since <hash>; refresh: /project-init map` is printed with the stamp hash

#### Scenario: No stamp
- **WHEN** a map file read has no `Commit:` stamp on its first line
- **THEN** the line `Map stale: <file>, unknown commits since none; refresh: /project-init map` is printed

#### Scenario: Exactly 20 commits
- **WHEN** 20 commits touching application code were made after the stamp
- **THEN** there is no `Map stale` line
