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
When a change or an edit adds a check that runs on every change (a hook, CI or the test suite) and refuses every case a `## Lessons` line names, the agent SHALL remove the line, keep its text under its id in `LESSONS.md` with `Held by: <check command or file> — <where it runs>`, and report `Lesson held: <line> -> <check>`; a check that refuses only some, or that nothing runs, keeps it. Where edits are forbidden or `lessons.write` is `off`, nothing is removed and no `Lesson held:` is given.

#### Scenario: The check covers the class
- **WHEN** a change adds a test to the project suite that fails on an em dash in every UI string file of the project and `## Lessons` holds the dash line
- **THEN** the line is gone from `## Lessons`, `LESSONS.md` holds its text under a `### <id>` heading with `Held by:` naming the check, and the report holds `Lesson held:` with the line and the check

#### Scenario: The check covers a part
- **WHEN** the added test fails on the dash only in `.json` files and the lesson is about every UI string
- **THEN** the line stays in `## Lessons`

### Requirement: Held lesson not written again
The search for duplicates of Lessons without duplicates SHALL also read the `Held by:` entries of the project's `LESSONS.md`. As an exception to Lesson from a correction or a fix and to Gate for a mechanical lesson, a lesson such an entry covers writes no `## Lessons` line and no `Lesson gate:`, and the report gives `Lesson held: <lesson> -> <check>`.

#### Scenario: The same class after removal
- **WHEN** the dash line was removed with `Held by:` and the owner again says "no em dash in UI strings"
- **THEN** no new `## Lessons` line and no `Lesson gate:` line are written, and the report holds `Lesson held:` naming the check that holds it
