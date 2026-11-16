## ADDED Requirements

### Requirement: Skill size budget
Every `skills/*/SKILL.md` that git tracks SHALL be at most 16,000 bytes, so that the part Claude Code re-attaches after compaction (the first 5,000 tokens) holds the whole file. A test SHALL name each larger file with its size in bytes.

#### Scenario: A skill over the budget
- **WHEN** a tracked `SKILL.md` grows to 16,001 bytes
- **THEN** the test fails naming the file and `16001 bytes`

#### Scenario: A skill at the budget
- **WHEN** a tracked `SKILL.md` is exactly 16,000 bytes
- **THEN** the test passes

#### Scenario: An untracked skill
- **WHEN** a working copy skill that git does not track is 40,000 bytes
- **THEN** the test passes

### Requirement: Step files
A step body moved out of a `SKILL.md` SHALL lie in a file of the same skill folder, named in backquotes by the line of its step together with the instruction to read it each time the step starts. A test SHALL fail when a named step file is missing or when a `.md` file of a skill folder other than `SKILL.md` is named by no line of that `SKILL.md`.

#### Scenario: A missing step file
- **WHEN** `skills/spec-dispatch/SKILL.md` names `merge.md` and the folder has no such file
- **THEN** the test fails naming the skill and `merge.md`

#### Scenario: An orphan step file
- **WHEN** `skills/spec-next/` holds `old-step.md` that its `SKILL.md` does not name
- **THEN** the test fails naming the skill and `old-step.md`

#### Scenario: Deployed next to the skill
- **WHEN** `sync.py push` deploys `spec-dispatch` into `~/.claude/skills`
- **THEN** every step file of `skills/spec-dispatch/` lies next to the deployed `SKILL.md` with the same text
