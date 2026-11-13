# readme-content Specification

## Purpose
The README leads with what solo-sdd is, its quick start and its own features, states in checkable terms when its work stops, and `SOURCES.md` lists the third-party files the repository ships.

## Requirements

### Requirement: Stop conditions in the README
`README.md` SHALL hold a section "How solo-sdd stops" that lists every stop condition of the process, each with the file that enforces it, names the goal of the loop (acceptance by the spec, independent review, live scenario), states that there is no token budget and why, and maps the terms harness and loop to solo-sdd parts.

#### Scenario: Every condition has a file
- **WHEN** a reviewer opens each file the section names
- **THEN** each file holds the condition the section attributes to it

#### Scenario: Missing condition
- **WHEN** a stop condition exists in `global/AGENTS.md`, `ALGORITHM.md` or a skill and the section does not list it
- **THEN** the reviewer marks the requirement as not met

### Requirement: Own features first
`README.md` SHALL start with what solo-sdd is in at most two sentences and the quick start (install, `solo-sdd init`, `/project-init`, `/spec-plan`, `/spec-next`) before line 40, then its own features. It SHALL NOT compare solo-sdd with other tools; the name OpenSpec SHALL appear only in the section on moving from it (the `openspec/` folder and the `import openspec` command are a path and a command, not the name).

#### Scenario: Quick start position
- **WHEN** `tests/test_readme.py` reads `README.md`
- **THEN** the quick start heading is before line 40, and no line names a tool from the test's list of compared tools

#### Scenario: OpenSpec only in the move section
- **WHEN** `README.md` names OpenSpec outside the section "Moving from OpenSpec"
- **THEN** the test fails and names the line

### Requirement: Sources are shipped third-party files
`SOURCES.md` SHALL list only third-party code or text the repository ships as pinned copies under `integrations/`, each with its origin, version and license.

#### Scenario: The pinned copies
- **WHEN** `integrations/` holds pinned copies (today `integrations/antislop/` and `integrations/security-audit/`)
- **THEN** `SOURCES.md` has one section per copy that names its folder, the version from its `VERSION` and its license, and names no other project

### Requirement: Line length
No line of `README.md`, `ALGORITHM.md` and the `skills/*/SKILL.md` files git tracks SHALL be longer than 600 characters (code points) outside fenced code blocks; a table row is a line too. A test SHALL name each longer line by file and line number.

#### Scenario: A long paragraph
- **WHEN** a skill gets a paragraph line of 700 characters
- **THEN** the test fails naming the skill file and the line number

#### Scenario: A long code line
- **WHEN** a fenced code block holds a 700-character command
- **THEN** the test passes

#### Scenario: A long table row
- **WHEN** a table row in `README.md` is 700 characters long
- **THEN** the test fails naming `README.md` and the line number

#### Scenario: An untracked skill
- **WHEN** a working copy skill that git does not track has a 700-character line
- **THEN** the test passes
