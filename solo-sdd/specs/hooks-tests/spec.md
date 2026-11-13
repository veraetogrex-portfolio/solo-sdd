# hooks-tests Specification

## Purpose
The hook tests are unittest methods that call the hook logic in the process, so one scenario runs alone and a failure hides no other test.

## Requirements

### Requirement: Hook tests as unittest
`tests/test_work_hooks.py` SHALL be a unittest module with one test method per scenario that calls the hook logic in the process, plus at least one and at most three runs of the real `global/work_hooks.py` entry point for each command its `main` dispatches and the previous script ran. A failing test SHALL NOT stop the later ones.

#### Scenario: One scenario alone
- **WHEN** `python3 -m unittest test_work_hooks.<Class>.<test>` runs from `tests/`
- **THEN** only that test runs

#### Scenario: Two failures
- **WHEN** two guard scenarios fail
- **THEN** the run reports both

#### Scenario: Entry-point runs
- **WHEN** the stand counts the runs of `global/work_hooks.py` as a process per command
- **THEN** every command the previous script ran has one to three, and no command has more

### Requirement: Isolated in-process calls
An in-process call SHALL run with the hook module's `HOME` and `STATE`, the environment and stdin patched for its test and restored when the test ends, its stdout captured; no test SHALL see another test's hook state, environment or temporary HOME.

#### Scenario: A variable set by one test
- **WHEN** one test sets `SOLO_SDD_EXPENSIVE_OK=1` for its call and a later test calls the guard without it
- **THEN** the later test's call sees no `SOLO_SDD_EXPENSIVE_OK`

### Requirement: Every hook check kept
Every check of the previous script SHALL be held by the new module: it SHALL hold at least as many assertions, and every hook mutant of the stand's fixed list that the previous script fails on SHALL fail it too. Every temporary HOME a test creates SHALL be removed when the test ends, also when it fails.

#### Scenario: Leftover folders
- **WHEN** the module runs to the end
- **THEN** no new `wh-home-*` folder stays in the temporary folder

#### Scenario: A failing test
- **WHEN** a test fails after creating its temporary HOME
- **THEN** that HOME is removed

#### Scenario: A hook mutant
- **WHEN** the stand runs the previous script and the new module against a copy of `global/work_hooks.py` with one guard rule disabled
- **THEN** both fail
