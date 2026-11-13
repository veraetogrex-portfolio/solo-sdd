# test-growth Specification

## Purpose
Which tests a change adds, keeps or changes, so the suite grows with behaviour and not with repeated checks, and the suite time of every change is visible.

## Requirements

### Requirement: No repeated tests
`spec-plan` SHALL say: a scenario the Live Scenario stand proves needs no second test of the same behaviour; a new case of a tested behaviour is a new row of that test, not a new function; code with no behaviour of its own gets no test (scenario «Untested code»); required tests are not repeats (scenario «Required tests»). `spec-analyze` pass 1 SHALL accept such a scenario without a second test; `spec-next` step 7a SHALL label a repeated test `Important`; `global/AGENTS.md` SHALL hold the rule.

#### Scenario: A new edge case
- **WHEN** a task adds a case to a behaviour that has a table-driven test
- **THEN** the task adds a row to that table, not a test function

#### Scenario: Untested code
- **WHEN** a task would test a getter, a DTO, configuration, a thin library wrapper, a private function a scenario test reaches, a one-off script or what a separate CI step checks
- **THEN** the task plans no such test; a one-off script is checked by a stand

#### Scenario: A scenario the stand proves
- **WHEN** `spec-analyze` pass 1 meets a scenario that a Live Scenario step checks and no unit test checks
- **THEN** the scenario counts as covered, with no finding

#### Scenario: A repeated test in review
- **WHEN** a reviewer finds a unit test that repeats a scenario a higher-level test already covers
- **THEN** the finding is `Important`

#### Scenario: Required tests
- **WHEN** a stand proves a scenario that also has a property test `spec-analyze` pass 3a requires, or a bug fix's test of the bug scenario
- **THEN** that test is not a repeat: `spec-plan` plans it and the reviewer gives no finding for it

### Requirement: Doubles only for external I/O
`spec-plan` and `global/AGENTS.md` SHALL allow test doubles only for external I/O (the network, paid APIs) and the clock; own storage SHALL get a temporary real one or an in-memory fake, and the module under test SHALL NOT be mocked.

#### Scenario: A storage test
- **WHEN** a task tests code that writes to the project's own SQLite file
- **THEN** the test uses a temporary database file, not a mock of the storage module

### Requirement: Tests change only by a requirement
An assertion of an existing test SHALL be changed or deleted only by a task that names a MODIFIED or REMOVED requirement. A task that changes a test's setup, cost or layout SHALL name the test and keep every assertion. `spec-plan` SHALL hold this rule for tasks, `spec-next` step 5 for the code it writes and `global/AGENTS.md` for all work.

#### Scenario: A test in the way
- **WHEN** a task's code makes an existing test fail and the task names no MODIFIED requirement for it
- **THEN** the code is fixed, not the test

#### Scenario: A cheaper fixture
- **WHEN** a task builds a test class's repository once per class instead of once per test and keeps every assertion
- **THEN** the task needs no MODIFIED requirement

### Requirement: Property test budget
`spec-plan` SHALL say: a property test that starts a process or creates a repository per example states its example count in its task and in the test.

#### Scenario: A repository per example
- **WHEN** a task plans a Hypothesis test that creates a git repository per example
- **THEN** the task names the test's `max_examples`, and the test sets the same number

### Requirement: Suite time in the report
The `spec-next` report and the `Result` of `verification.md` SHALL hold the line `Suite: <before> (<change>) -> <after>`: `<after>` is the seconds of the change's last suite run, `<before>` the `<after>` of the `Suite:` line in the archived change `<change>` whose folder sorts last among those with one; with none, `Suite: n/a -> <after>`.

#### Scenario: A report
- **WHEN** a change is archived and the archived change `x`, last by folder name among those with the line, recorded `Suite: 300 (w) -> 310`
- **THEN** the report and `Result` hold `Suite: 310 (x) -> <seconds of this change's last suite run>`, with no extra suite run on the base branch

#### Scenario: The first record
- **WHEN** no archived change has a `Suite:` line
- **THEN** the line is `Suite: n/a -> <after>`
