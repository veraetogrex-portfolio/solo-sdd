## MODIFIED Requirements

### Requirement: Line length
No line of `README.md`, `ALGORITHM.md`, the `skills/*/SKILL.md` files and the step files `skills/*/*.md` git tracks SHALL be longer than 600 characters (code points) outside fenced code blocks; a table row is a line too. A test SHALL name each longer line by file and line number.

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

#### Scenario: A long line in a step file
- **WHEN** the step file `skills/spec-dispatch/merge.md` gets a paragraph line of 700 characters
- **THEN** the test fails naming `skills/spec-dispatch/merge.md` and the line number
