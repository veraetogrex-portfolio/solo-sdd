# lesson-routing Specification

## Purpose
A correction from the owner or the found cause of a bug becomes one short rule in the project's own `AGENTS.md`, written about the class of cause, without duplicates, and never in the installed global rules.

## Requirements

### Requirement: Lesson from a correction or a fix
After the owner corrects the agent in a way that applies beyond the current task, or after a bug fix whose cause is found, the agent SHALL write, without asking, one imperative sentence about the class of cause, not the symptom, into the `## Lessons` section of the project's `AGENTS.md`, creating the section at the end of the file if it is missing. When the owner forbade edits, the lesson goes to the report as `Lesson (not written): <sentence>` instead.

#### Scenario: Missing await
- **WHEN** a failing test is fixed by adding a missing `await` in one handler
- **THEN** the new line reads like "Every async call in a handler is awaited" and names no file or line number

#### Scenario: Task-local remark
- **WHEN** the owner says "rename this variable to `total`" about the current diff only
- **THEN** no line is written to `## Lessons`

#### Scenario: Project without AGENTS.md
- **WHEN** the project has no `AGENTS.md`
- **THEN** no `AGENTS.md` is created and the report gives the lesson as `Lesson (no AGENTS.md): <sentence>`

### Requirement: Lessons without duplicates
Before writing, the agent SHALL search `## Lessons` and the other sections of the project's `AGENTS.md`. A lesson an existing line already covers SHALL refine that line instead of adding a new one. The section SHALL hold at most 20 lines; a lesson that would make the 21st SHALL be written together with merging overlapping lines in the same edit.

#### Scenario: Same class again
- **WHEN** a second handler misses an `await` and `## Lessons` already holds the async line
- **THEN** the number of lines in `## Lessons` stays the same

#### Scenario: Section full
- **WHEN** `## Lessons` holds 20 lines and a new class of cause is found
- **THEN** after the edit the section holds at most 20 lines and the new class is in it

### Requirement: Global rules untouched by lessons
The agent SHALL NOT write a lesson into installed copies of the global rules (`~/AGENTS.md`, `~/.codex/AGENTS.md`, `~/.claude/CLAUDE.md`). A lesson about the solo-sdd process itself SHALL go to the final report as a line `Lesson for solo-sdd: <sentence>`.

#### Scenario: Process lesson in a consumer project
- **WHEN** in a consumer project the owner corrects how the agent runs `/spec-next`
- **THEN** the checksums of the three installed copies do not change and the report holds a line `Lesson for solo-sdd:`

### Requirement: Lesson named in the report
The final report SHALL name every line the agent wrote or refined in `## Lessons` and its file. The `spec-next` report SHALL carry the line `Lesson: <line> -> <file>` or `Lesson: none`.

#### Scenario: Report of spec-next
- **WHEN** `/spec-next` closes a change during which a lesson was written
- **THEN** its report holds `Lesson:` with the exact line and the path of the `AGENTS.md` it went to

#### Scenario: Only a process lesson
- **WHEN** `/spec-next` closes a change with no project lesson and one lesson about the solo-sdd process
- **THEN** its report holds both `Lesson: none` and `Lesson for solo-sdd: <sentence>`

#### Scenario: Under the dispatcher
- **WHEN** an orchestrator under `spec-dispatch` writes a lesson
- **THEN** its status block holds the `Lesson` line under `NOTES` and the dispatcher report holds it in the `Lessons:` line with the change name
