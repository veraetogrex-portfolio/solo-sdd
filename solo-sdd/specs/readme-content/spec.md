# readme-content Specification

## Purpose
The README leads with what solo-sdd is, its quick start and its own features, states in checkable terms when its work stops, and `SOURCES.md` lists the third-party files the repository ships.

## Requirements

### Requirement: Stop conditions in the README
`docs/stop-conditions.md` SHALL list every stop condition of the process, each with the file that enforces it, name the goal of the loop (acceptance by the spec, independent review, live scenario), state that there is no token budget and why, and map the terms harness and loop to solo-sdd parts. `README.md` SHALL hold a section "How it stops" with the main conditions and an absolute link to that file.

#### Scenario: Every condition has a file
- **WHEN** a reviewer opens each file `docs/stop-conditions.md` names
- **THEN** each file holds the condition the table attributes to it

#### Scenario: Missing condition
- **WHEN** a stop condition exists in `global/AGENTS.md`, `ALGORITHM.md` or a skill and `docs/stop-conditions.md` does not list it
- **THEN** the reviewer marks the requirement as not met

### Requirement: Own features first
`README.md` SHALL start with what solo-sdd is in at most two sentences and the quick start (install with `--hooks`, `solo-sdd init`, `/project-init`, `/spec-plan`, `/spec-next`) before line 40, then its own features. It SHALL NOT compare solo-sdd with other tools and SHALL NOT name OpenSpec; `docs/migrate.md` holds the move from it (the `openspec/` folder and the `import openspec` command are a path and a command, not the name).

#### Scenario: Quick start position
- **WHEN** `tests/test_readme.py` reads `README.md`
- **THEN** the quick start heading is before line 40, it holds `solo-sdd install --hooks`, and no line names a tool from the test's list of compared tools

#### Scenario: OpenSpec only in the move document
- **WHEN** `README.md` names OpenSpec on any line
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

### Requirement: Short README
`README.md` SHALL be at most 12 000 bytes and hold the sections "Update and uninstall", "Docs", "Contributing" and "License". "Docs" SHALL link by an absolute address every `docs/*.md` file git tracks; a reference section moved out of the README keeps its text in the docs file it moved to.

#### Scenario: A grown README
- **WHEN** `README.md` grows past 12 000 bytes
- **THEN** `tests/test_readme.py` fails and names the size

#### Scenario: An unlinked document
- **WHEN** a new `docs/x.md` is tracked and the "Docs" section does not link it
- **THEN** the test fails and names `docs/x.md`

### Requirement: Skills listed
The "Skills" section of `README.md` SHALL name in backquotes every skill of `targets.json["skills"]`, each once, and no other skill.

#### Scenario: A new skill
- **WHEN** `targets.json` gets the skill `new-skill` and the "Skills" section does not name it
- **THEN** `tests/test_readme.py` fails and names `new-skill`

#### Scenario: A removed skill
- **WHEN** the "Skills" section names `old-skill`, which `targets.json` does not list
- **THEN** the test fails and names `old-skill`
