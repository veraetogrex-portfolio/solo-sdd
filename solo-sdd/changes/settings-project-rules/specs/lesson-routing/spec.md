## MODIFIED Requirements

### Requirement: Lesson from a correction or a fix
After the owner corrects the agent in a way that applies beyond the current task, or after a bug fix whose cause is found, the agent SHALL write, without asking, one imperative sentence about the class of cause, not the symptom, into the `## Lessons` section of the project's `AGENTS.md`, creating the section at the end of the file if it is missing. When the owner forbade edits, or `lessons.write` is `off`, the lesson goes to the report as `Lesson (not written): <sentence>` instead.

#### Scenario: Missing await
- **WHEN** a failing test is fixed by adding a missing `await` in one handler
- **THEN** the new line reads like "Every async call in a handler is awaited" and names no file or line number

#### Scenario: Task-local remark
- **WHEN** the owner says "rename this variable to `total`" about the current diff only
- **THEN** no line is written to `## Lessons`

#### Scenario: Project without AGENTS.md
- **WHEN** the project has no `AGENTS.md`
- **THEN** no `AGENTS.md` is created and the report gives the lesson as `Lesson (no AGENTS.md): <sentence>`
