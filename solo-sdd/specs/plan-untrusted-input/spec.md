# plan-untrusted-input Specification

## Purpose
A change whose code parses foreign input (files, archives, documents, network data) gets tests on hostile input in `tasks.md` before the code, not one review finding per round.

## Requirements

### Requirement: Hostile input task
If the change code reads foreign input (files, archives, documents or network data whose path or content arrive while the program runs: an argument, a request, the network, the user's choice, rather than lying in the project repository), `spec-plan` SHALL include in `tasks.md` a task of tests on hostile input with the items applicable to this input from the requirement Hostile input checklist.

#### Scenario: Parsing DOCX
- **WHEN** `spec-plan` creates the change "accept DOCX as materials" with its own ZIP and XML parsing
- **THEN** `tasks.md` has a task of tests on hostile input with items about a ZIP bomb, entry paths, nesting depth, XML entities and a broken file

#### Scenario: No task
- **WHEN** `spec-analyze` checks an EPUB parsing change whose `tasks.md` has no hostile input task
- **THEN** a HIGH finding, the task is added to `tasks.md`

#### Scenario: The owner's input
- **WHEN** the change reads only `AGENTS.md` and the project's own configs
- **THEN** there is no hostile input task and no finding

### Requirement: Hostile input checklist
The items of the hostile input test task SHALL be taken from the list: a limit on size and number of entries (ZIP bomb, compression ratio), archive entry paths (`..`, absolute, links), nesting depth, XML entity expansion, catastrophic regular expressions, truncated and broken input, escaping when inserting into code, HTML or a command. An item inapplicable to this input is not written.

#### Scenario: Input without an archive
- **WHEN** a change accepts JSON from the user over the network and inserts its fields into HTML
- **THEN** the task has items about nesting depth, truncated and broken input and escaping when inserting into HTML, and no items about a ZIP bomb and archive entry paths

### Requirement: Hostile input analyze finding
`spec-analyze` SHALL mark a change whose code reads foreign input (requirement Hostile input task) without a hostile input test task as a HIGH finding and add the task; if `tasks.md` already has the maximum number of tasks (10, for a bug fix 5), the items are added to the existing test task.

#### Scenario: The task limit
- **WHEN** `spec-analyze` adds a hostile input task, and `tasks.md` already has the maximum number of tasks (10, for a bug fix 5)
- **THEN** the items are added to the existing test task
