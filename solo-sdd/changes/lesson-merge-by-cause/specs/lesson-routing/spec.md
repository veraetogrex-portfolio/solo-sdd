## MODIFIED Requirements

### Requirement: Lessons without duplicates
Before writing, the agent SHALL search `## Lessons` and the other sections of the project's `AGENTS.md`. A lesson an existing line already covers SHALL refine that line instead of adding a new one. The section SHALL hold at most 20 lines; a lesson that would make the 21st SHALL be written together with a merge in the same edit: two or more overlapping lines become one new line that names the cause they share, never their joined text.

#### Scenario: Same class again
- **WHEN** a second handler misses an `await` and `## Lessons` already holds the async line
- **THEN** the number of lines in `## Lessons` stays the same

#### Scenario: Section full
- **WHEN** `## Lessons` holds 20 lines and a new class of cause is found
- **THEN** after the edit the section holds at most 20 lines and the new class is in it

#### Scenario: Merge names the shared cause
- **WHEN** the section is full and two lines are merged to make room
- **THEN** the merged line is one sentence within the bound of `Short line with full text`, and the full text of both old lines stands under its id in `LESSONS.md`

## ADDED Requirements

### Requirement: Short line with full text
Every `## Lessons` line SHALL be one sentence of at most 300 characters before an optional link `([full text](LESSONS.md#<id>))`. Details, examples and dates of a line SHALL go under `### <id>` in the project's `LESSONS.md`, created when first needed; a refinement of a linked line edits both. After any edit of the section no line SHALL exceed the bound: a longer line is shortened to its cause in the same edit, its old text kept verbatim under its id.

#### Scenario: Glued line found
- **WHEN** an agent writes a lesson into a section that holds a line of 1,200 characters with six rules
- **THEN** after the edit every line is at most 300 characters before its link, and the old 1,200 characters stand verbatim in `LESSONS.md` under the id that line links to

#### Scenario: Link to a missing id
- **WHEN** a line links to `LESSONS.md#<id>`
- **THEN** `LESSONS.md` holds a heading `### <id>`
