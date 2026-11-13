# integration-run Specification

## Purpose
Runs the enabled integrations of a process point with one command, prints a short result per integration, and records it with the hash of the working tree so a later step can look the result up instead of trusting the agent's report.

## Requirements

### Requirement: Check command
`solo-sdd check --point <checks|ship> [--changed]` SHALL run each enabled integration of the point, with `--changed` those whose `applies` matches a changed file: one differing between the working copy (untracked files too) and the merge base of `HEAD` with the base branch, else `HEAD`. It SHALL print `PASS|FAIL|SKIP <name>: <first output line>` per integration in name order, `FAIL <name>: not found` with exit 1 for a listed name with no folder. `review` and `audit` SHALL list material instead.

#### Scenario: Nothing enabled
- **WHEN** `integrations` is empty and `solo-sdd check --point checks` runs
- **THEN** it prints `no integrations enabled` and exits 0

#### Scenario: Applies does not match
- **WHEN** `marker-check` has `applies: *.py`, only `README.md` changed, and `check --point checks --changed` runs
- **THEN** `marker-check` is not run, the output is `no integration applies to the changed files`, exit 0

#### Scenario: A listed name without a folder
- **WHEN** `integrations: marker-check, no-such` is set and `check --point checks` runs
- **THEN** `marker-check` runs, `FAIL no-such: not found` is printed and the command exits 1

### Requirement: Nothing to run and a path that cannot be passed
When no enabled integration has the point, `check` SHALL print `no enabled integration has the point <point>` and exit 0. A changed path that holds a newline SHALL be refused with exit 1 before any command runs, since stdin holds one path per line.

#### Scenario: A changed path with a newline
- **WHEN** a file named `x` newline `README.md` is untracked and `check --point checks` runs
- **THEN** it exits 1 naming the path, and no integration command is started

### Requirement: Command environment
An integration command SHALL run through `/bin/sh -c` in the repository root, with `SOLO_SDD_INTEGRATION_DIR` set to the absolute path of its folder and `SOLO_SDD_POINT` to the point, and get the changed files on stdin, one path from the repository root per line. On `timeout` the whole process group of the run SHALL be stopped, and once the command exits the children it left in that group SHALL be stopped too; the group SHALL never be signalled after its id may be free.

#### Scenario: The script reads the changed files
- **WHEN** `marker-check` runs `sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"` and `app.py` changed
- **THEN** the script finds its own file through `SOLO_SDD_INTEGRATION_DIR` and reads `app.py` on stdin

#### Scenario: A child process past the timeout
- **WHEN** the command starts a background child that sleeps past `timeout`
- **THEN** `check` returns after `timeout` seconds with `FAIL <name>: timeout <n>s` and the child is no longer running

### Requirement: Gate and advice
A `gate` integration whose command exits non-zero SHALL print FAIL, at most `output` lines of its output under it, and make the command exit 1. An `advice` one SHALL print the same lines and SHALL NOT change the exit code. A command still running after `timeout` seconds SHALL be stopped and count as FAIL with the line `timeout <n>s`.

#### Scenario: A gate fails
- **WHEN** the `gate` integration `marker-check` exits 1 printing 30 lines and `output` is 20
- **THEN** `FAIL marker-check: <first line>` and 20 lines follow, and `check` exits 1

#### Scenario: An advice fails
- **WHEN** the same integration has `mode: advice`
- **THEN** the same lines are printed and `check` exits 0

### Requirement: Missing tool
When the program named by `requires` is not on `PATH`, the integration SHALL not run; under `missing: warn` it SHALL print `SKIP <name>: <program> not found` and not change the exit code, under `missing: fail` it SHALL print `FAIL <name>: <program> not found` and make the command exit 1.

#### Scenario: Warn on a missing tool
- **WHEN** `requires: no-such-tool` and `missing: warn`
- **THEN** `SKIP marker-check: no-such-tool not found`, exit 0

#### Scenario: Fail on a missing tool
- **WHEN** `requires: no-such-tool` and `missing: fail`
- **THEN** `FAIL marker-check: no-such-tool not found`, exit 1

### Requirement: Result recorded by tree
After a run `check` SHALL write the point, the lines, the exit codes and the digest of each enabled description to `~/.local/share/solo-sdd/checks/<repo>/<hash>.json`, where `<hash>` is the git tree of the whole working copy (untracked, not ignored files included) and `<repo>` is the repository folder name with a short digest of its absolute path.

#### Scenario: Two repositories with one folder name
- **WHEN** `~/a/app` and `~/b/app` both run `check`
- **THEN** their records lie in two different `<repo>` folders

### Requirement: Record reuse
A call whose tree, point, `--changed` flag, changed files and enabled descriptions (by digest) match a record SHALL print the recorded lines with `reused <hash>`, exit with the recorded code and start no command. A record holding a SKIP or a stopped run (a timeout or output over 1 MB) SHALL NOT be reused, and a record that is not readable JSON of the expected shape, or holds a line with a character integration output cannot hold, SHALL be ignored and the run repeated.

#### Scenario: Same tree reused
- **WHEN** `check --point checks` failed on a gate and nothing changed since
- **THEN** a second call prints the same lines and `reused <hash>`, exits 1, and the integration command is not started

#### Scenario: An edit makes a new record
- **WHEN** a file changes after a recorded run
- **THEN** the next call runs the integrations and writes a record under a new hash

#### Scenario: An owner description edited
- **WHEN** the tree is the same but the `command` of an enabled owner integration changed
- **THEN** the next call runs the integrations again

#### Scenario: A skipped tool installed later
- **WHEN** the record holds `SKIP marker-check: no-such-tool not found` and the tree is the same
- **THEN** the next call runs `marker-check` again

### Requirement: Project command shown first
Before the first run of a project integration's command in a repository, and again after that command text changes, `check` SHALL print `command <name>: <command>` before its result line. Owner integrations SHALL NOT print it.

#### Scenario: First run in a repository
- **WHEN** the project integration `marker-check` runs for the first time in a repository
- **THEN** `command marker-check: sh "$SOLO_SDD_INTEGRATION_DIR/check.sh"` is printed before its result, and not on the next run with the same command

### Requirement: Integration output is data
The output of an integration SHALL be printed and recorded as text: bytes that are not UTF-8 replaced, control characters except tab removed, each line cut at 400 characters, at most 1 MB read, and a run past 1 MB of output SHALL be stopped and count as FAIL with the line `output over <n> bytes`; text addressed to an agent SHALL be passed on as output, never acted on.

#### Scenario: Escape codes in the output
- **WHEN** an integration prints a line with ANSI escape codes and invalid UTF-8 bytes
- **THEN** the printed and recorded line holds no control character and the run does not fail on decoding
