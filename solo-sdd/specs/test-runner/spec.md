# test-runner Specification

## Purpose
One command runs solo-sdd's own suite: test files in parallel, the last failures first, only failures in the output, and only the affected files when asked.

## Requirements

### Requirement: One test command
`python3 tests/run.py` SHALL run every `test_*.py` file of the `tests/` folder it lies in as its own process with stdin closed, at most `--jobs <n>` at once (default: the number of cores), and end with code 1 when any file fails. It SHALL print the output of failed files only, one line `ok <file> (<s> s)` or `FAIL <file> (<s> s)` per file, and the summary `files: <n>, failed: <k>, seconds: <s>`.

#### Scenario: A green suite
- **WHEN** every test file passes
- **THEN** the runner prints one `ok` line per file and the summary with `failed: 0`, and ends with code 0

#### Scenario: A failing file
- **WHEN** one file fails
- **THEN** the runner prints that file's output and its `FAIL` line, ends with code 1, and every other file still runs

### Requirement: Named files
`python3 tests/run.py <file>...` SHALL run only the named test files, with the same output and codes; a name that is not a `test_*.py` file of its `tests/` folder SHALL end the run with code 2 naming it, before any file runs. File names, `--failed` and `--affected` SHALL exclude each other: a run given two of them ends with code 2 and runs nothing.

#### Scenario: The oracle run of sdd-eval
- **WHEN** `sdd-eval.py compare` appends `tests/test_cli.py tests/test_init.py` to the `Tests` command `python3 tests/run.py`
- **THEN** only those two files run, and the code is 1 if one of them fails

#### Scenario: An unknown name
- **WHEN** the runner gets `tests/test_missing.py`
- **THEN** it ends with code 2 naming `tests/test_missing.py`, and no file runs

### Requirement: Failed files first
The runner SHALL keep the failed files in the git-ignored state file `tests/.last-failed`, one path per line, and start them before the others; `--failed` SHALL run only them. After a run the state SHALL hold the failures of this run plus the earlier failures of files this run did not select. Every selected file SHALL run exactly once per run, whatever the state file holds.

#### Scenario: A rerun after red
- **WHEN** the last run failed in `tests/test_sdd_pr.py` and the runner starts with `--failed`
- **THEN** it runs only `tests/test_sdd_pr.py`

#### Scenario: A partial run keeps other failures
- **WHEN** the state holds `tests/test_sdd_pr.py` and `tests/test_cli.py`, and a run of `tests/test_cli.py` alone passes
- **THEN** the state holds `tests/test_sdd_pr.py` only

#### Scenario: A broken state file
- **WHEN** the state file is empty, unreadable or names a file that no longer exists
- **THEN** the runner runs every selected file once, ignores the names it cannot use, and rewrites the state file

### Requirement: Affected files
`python3 tests/run.py --affected <path>...` SHALL run the test files `tests/affected.json` maps to the given paths (a key is a file, or a folder ending in `/` that holds the path; a folder path also takes the keys inside it), the files the map marks as always run, and every test file the map names nowhere; a path no key holds SHALL run the whole suite.

#### Scenario: An edit of the plan script
- **WHEN** the runner gets `--affected global/sdd_dispatch_plan.py`
- **THEN** it runs `tests/test_sdd_dispatch_plan.py`, `tests/test_sdd_eval.py` and the other files the map gives for that path, the always-run files and the files the map names nowhere, and not `tests/test_sdd_pr.py`, `tests/test_sdd_worktree.py` or `tests/test_work_hooks.py`

#### Scenario: An unknown path
- **WHEN** the runner gets `--affected tools/new.py`, which no key of the map holds
- **THEN** it runs the whole suite

#### Scenario: A stale map
- **WHEN** a key of `tests/affected.json` is no existing path, or a value is no existing test file
- **THEN** `tests/test_runner.py` fails naming the key or the value
