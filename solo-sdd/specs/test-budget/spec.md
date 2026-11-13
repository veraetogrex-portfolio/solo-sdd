# test-budget Specification

## Purpose
How many test runs a change takes and which command each run uses, so a change costs one full suite run plus the tests of the edited modules.

## Requirements

### Requirement: Two test commands
`project-init` SHALL write two rows into the Commands table of a project's `AGENTS.md`: `Tests`, the whole suite, and `Tests (one)`, one file or one test with a placeholder for its name, in the project's own test runner; solo-sdd's own `AGENTS.md` SHALL hold both rows. Every reader of the suite command (scripts, the `TESTS` field of a status, the `Checks` section, the thread limit of the dispatcher rule) SHALL take the `Tests` row only.

#### Scenario: A new project
- **WHEN** `project-init` prepares a Python project tested with unittest
- **THEN** the Commands table has a `Tests` row and a `Tests (one)` row that runs one test file

#### Scenario: This repository
- **WHEN** `tests/test_skill_commands.py` reads `AGENTS.md`
- **THEN** both rows are in the Commands table, and the `Checks` section names the `Tests` row, not "all tests from the table"

#### Scenario: A script reads the suite command
- **WHEN** `sdd-eval.py` reads the test command of an `AGENTS.md` whose `Tests (one)` row stands above the `Tests` row
- **THEN** it takes the value of the `Tests` row

### Requirement: Suite once per change
`spec-next`, `global/AGENTS.md` and `ALGORITHM.md` SHALL say: while coding only the tests of the edited module run (`Tests (one)`); the whole suite runs once after the last code edit and again only when code changed after that run; after a red run the failed tests run first and the suite once they are green; test output uses the quiet reporter, and on a failure only the failing lines are read.

#### Scenario: A review with only Nits
- **WHEN** the suite passed after the last code edit and the review finds only Nits, closed without a code edit
- **THEN** the change archives without a second suite run

#### Scenario: A Nit fixed in code
- **WHEN** a Nit is fixed by a code edit after the suite passed
- **THEN** the tests of the edited module run, and the suite runs once more after the last such edit, with no new review round

#### Scenario: Quiet output
- **WHEN** an agent runs the suite
- **THEN** it uses the runner's quiet option (`-q` for pytest, `--reporter=dot` for vitest, `--silent` for jest; unittest prints only dots by default), and on a red run it reads the failure lines, not the whole log

#### Scenario: Under the dispatcher
- **WHEN** a change runs under `spec-dispatch` in `local` mode
- **THEN** the orchestrator runs the suite by this budget, and the dispatcher's run after merge (capability `spec-dispatch`) stays as it is and is not counted in it

#### Scenario: A fix after an Important finding
- **WHEN** a reviewer's Important finding leads to a code edit
- **THEN** the tests of the edited module run first, and the suite runs once more after the last edit

### Requirement: Reviewer does not rerun the suite
`spec-next` step 7a SHALL hand the reviewer the test command with its result line; the reviewer SHALL NOT rerun the whole suite and SHALL run only the single tests it doubts.

#### Scenario: A doubtful test
- **WHEN** the reviewer doubts that a test checks its requirement
- **THEN** it runs that one test by the `Tests (one)` command, not the suite
