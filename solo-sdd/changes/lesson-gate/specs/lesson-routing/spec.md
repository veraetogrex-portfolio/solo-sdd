## ADDED Requirements

### Requirement: Gate for a mechanical lesson
When a lesson's class of cause is mechanical, that is a fixed string, character, command, API name, import form or file path whose presence a program decides without judging intent, the agent SHALL write the project lesson as before and also give the report line `Lesson gate: <the check> — <where it would run>`. A lesson whose check needs judgement of intent, and a `Lesson for solo-sdd:`, SHALL get no such line. The `spec-next` report form SHALL name it.

#### Scenario: A banned character
- **WHEN** the owner corrects the agent: "never put an em dash into UI strings"
- **THEN** `## Lessons` gets the line about the dash and the report holds `Lesson gate:` naming a check of the changed text files for the character

#### Scenario: A judgement call
- **WHEN** the owner corrects the agent: "name a function by what it returns, not by how it works"
- **THEN** `## Lessons` gets the line and the report holds no `Lesson gate:`

#### Scenario: A process lesson
- **WHEN** the owner corrects how the agent runs `/spec-next`: "never print the archive path twice"
- **THEN** the report holds `Lesson for solo-sdd:` and no `Lesson gate:`

#### Scenario: Under the dispatcher
- **WHEN** an orchestrator under `spec-dispatch` gives a `Lesson gate:` line
- **THEN** its status block holds it under `NOTES` and the dispatcher report holds it in the `Lessons:` line with the change name

### Requirement: Lesson held by a check
When a change adds a check that refuses every case a `## Lessons` line names, it SHALL remove the line, keep its text under its id (created if missing) in `LESSONS.md` with `Held by: <check>`, and report `Lesson held: <line> -> <check>`; a check that refuses only some keeps the line. As an exception to Lesson from a correction or a fix, a lesson a `Held by:` entry covers writes no line and no `Lesson gate:`. Where edits are not allowed, nothing is removed.

#### Scenario: The check covers the class
- **WHEN** a change adds a check that fails on an em dash in every UI string file of the project and `## Lessons` holds the dash line
- **THEN** the line is gone from `## Lessons`, `LESSONS.md` holds its text under a `### <id>` heading with `Held by:` naming the check, and the report holds `Lesson held:` with the line and the check

#### Scenario: The check covers a part
- **WHEN** the added check fails on the dash only in `.json` files and the lesson is about every UI string
- **THEN** the line stays in `## Lessons`

#### Scenario: The same class after removal
- **WHEN** the dash line was removed with `Held by:` and the owner again says "no em dash in UI strings"
- **THEN** no new `## Lessons` line and no `Lesson gate:` line are written, and the report names the check that holds it
