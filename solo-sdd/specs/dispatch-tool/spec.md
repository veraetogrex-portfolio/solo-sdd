# dispatch-tool Specification

## Purpose
The script `sdd-dispatch.py` does the mechanical steps for the dispatcher: accepting an orchestrator status and merging a change in `local` mode, printing one summary line per step.

## Requirements

### Requirement: Status acceptance command
`sdd-dispatch.py accept <file>` SHALL parse the status block by the capability `orchestrator-status` and for `STATUS: archived` run in `WORKTREE` the commands of the `VALIDATE` and `LIVE` fields (the text before the first ` -> `), taking the exit code before shortening the output. The script does not run the `TESTS` command. Codes: 0 both fields match; 1 there are mismatches; 2 the block is not parsed or the status is not `archived`, no commands run; the summary line names the reason.

#### Scenario: The status matches
- **WHEN** `VALIDATE` ends with code 0, and the `LIVE` output holds the text after ` -> `
- **THEN** code 0, the summary line "status matches"

#### Scenario: Status not_ready
- **WHEN** the file has `STATUS: not_ready`
- **THEN** code 2, no commands run

#### Scenario: A broken block
- **WHEN** the file is empty, has no `STATUS:`, `LIVE` has no ` -> ` or there is no `WORKTREE` folder
- **THEN** code 2 with the reason, no commands run

#### Scenario: All cases of an unparsed block
- **WHEN** the file cannot be read or is empty, has no `STATUS:` line, the `WORKTREE`, `VALIDATE` or `LIVE` field is empty, `LIVE` has no ` -> ` or the text after it is empty, there is no `WORKTREE` folder
- **THEN** the block is not parsed: code 2, the summary line names the reason, no commands run

### Requirement: Status comparison
In `accept` the `VALIDATE` field SHALL match on exit code 0, and the `LIVE` field on code 0 if the text after ` -> `, trimmed, is contained in the command output (stdout and stderr together), both with every run of whitespace collapsed to one space. For every mismatch the script prints a line: the field, the command, stated, got, with the last three output lines as printed.

#### Scenario: An exit code under a pipe
- **WHEN** the `LIVE` command ends with code 1 and prints the expected text
- **THEN** code 1, the line names `LIVE`, the stated output and code 1

#### Scenario: Different output
- **WHEN** the `LIVE` command ends with code 0, but the output lacks the text after ` -> `
- **THEN** code 1, the line names the stated text and the last three output lines

#### Scenario: Extra spaces in the output
- **WHEN** the `LIVE` command ends with code 0 and prints `Tests  19 passed` with two spaces, and the stated text is `Tests 19 passed`
- **THEN** the field matches

### Requirement: Local land command
`sdd-dispatch.py land-local <MAIN> <WORKTREE> <id> [--check <command>]...` SHALL stop at the first failure: before the merge, edited tracked files of `MAIN` give code 2, a branch writing a file `MAIN` has untracked code 6; `git merge --no-ff --no-edit change/<id>`, a conflict: `merge --abort`, code 6; `sdd-worktree.py transport`, code 3: `reset --keep` to the pre-merge commit, code 6. Each code 2 and 6 names the files. `sdd-worktree.py` output (`not transported: <files>` too) is printed as is.

#### Scenario: A merge conflict
- **WHEN** merging `change/b` gives a conflict in `README.md`
- **THEN** code 6, the line names `README.md`, the main branch is on the previous commit, the worktree and branch are in place

#### Scenario: An untracked file in the way
- **WHEN** `change/b` edits `solo-sdd/changes/archive/2026-11-01-a/tasks.md`, which `MAIN` holds ignored
- **THEN** code 6 with the line `not merged: merge would overwrite untracked files: solo-sdd/changes/archive/2026-11-01-a/tasks.md`, the merge does not start, the file is unchanged

#### Scenario: Others' edits in the main folder
- **WHEN** the tracked `AGENTS.md` is changed in `MAIN`
- **THEN** code 2 with `AGENTS.md`, the merge does not start

#### Scenario: Rolling back a conflict
- **WHEN** `git merge` gives a conflict
- **THEN** the script runs `merge --abort` and ends with code 6 and the conflict files

#### Scenario: The transfer failed
- **WHEN** `sdd-worktree.py transport` ended with code 3
- **THEN** `reset --keep` to the commit before the merge and code 6 with the files

#### Scenario: A step failure after merge
- **WHEN** a step failed with a code other than those handled above, and the merge is already done
- **THEN** the script first rolls back the merge the same way as after a red check, then code 1 with the line "not merged: <step>: <error>"

#### Scenario: A step failure
- **WHEN** git or `sdd-worktree.py` ended with a code other than those handled in the requirement text
- **THEN** code 1 with the line "not merged: <step>: <error>"

### Requirement: Local land checks and cleanup
After the merge and the transfer `land-local` SHALL run every `--check` and `solo-sdd validate --all` once each. All passed: `sdd-worktree.py remove`, `git branch -d change/<id>`, code 0 and the merge hash. A failure of `remove` or `branch -d` does not roll back the merge: code 1 with the line "merged <hash>, not cleaned: <step>: <error>".

#### Scenario: Everything passed
- **WHEN** the merge, the transfer and all checks passed
- **THEN** code 0, the worktree is removed, the branch `change/<id>` is deleted

### Requirement: Local land after a red check
If a check after merge in `land-local` failed, the script SHALL roll back the merge (`git reset --keep` to the commit before it, then `sdd-worktree.py undo`), not repeat checks "until green", and once run the failed check in `MAIN` on the main branch before the merge. It passes there: code 3, with the command and the last failure lines (up to 20, stdout and stderr together). It fails there too: code 4 "main red" with the command and the lines. The worktree and branch stay in both cases.

#### Scenario: A red seam
- **WHEN** after merging `change/c` `npm test` fails, and on main before the merge it passes
- **THEN** code 3 with the failure lines; the main folder has no archive of `c`

#### Scenario: Main is red by itself
- **WHEN** the failed check also fails on main before the merge
- **THEN** code 4 "main red", the merge is rolled back

### Requirement: Owner-only paths in local land
Before the merge `sdd-dispatch.py land-local` SHALL check the files of the branch `change/<id>` against the main branch with the "owner only" paths by the same rules as the requirement Owner-only paths gate of the capability `pr-tool`. The item is also checked in the WORKTREE `AGENTS.md`: the transfer would bring it into the main folder. A match gives code 8 "waits for the owner: <paths>", the merge does not start, the worktree and branch are in place.

#### Scenario: A hook in local mode
- **WHEN** "Delivery" has "Owner only: `global/*.py`", and the change branch changes `global/work_hooks.py`
- **THEN** code 8 with this path, the main branch is unchanged

#### Scenario: The item in AGENTS.md outside git
- **WHEN** `AGENTS.md` is ignored by git, and in WORKTREE a path is removed from the "Owner only:" item
- **THEN** code 8, the merge and the transfer do not start

### Requirement: LIVE from the Live Scenario
`accept` SHALL count as a mismatch, without running it, a `LIVE` command that, whitespace collapsed, equals no code span of the `## Live Scenario` section of `<ARCHIVE>/verification.md` read as `solo-sdd validate` reads it; the line SHALL name `LIVE` and `not in the Live Scenario`. An empty `ARCHIVE`, one outside `WORKTREE`, or no readable file or section SHALL give `LIVE: no Live Scenario in <path>`.

#### Scenario: An invented command
- **WHEN** the status has `LIVE: echo ok -> ok` and the Live Scenario has no code span `echo ok`
- **THEN** code 1, the line names `LIVE` and `not in the Live Scenario`, `echo ok` did not run

#### Scenario: A part of a command
- **WHEN** the Live Scenario has `python3 tests/stands/words.py --all` and `LIVE` is `python3 tests/stands/words.py`
- **THEN** code 1, the line names `not in the Live Scenario`

#### Scenario: A command from the scenario
- **WHEN** a Live Scenario step has the code span `python3 tests/stands/words.py` and `LIVE` is that command
- **THEN** the command runs and is compared as before

#### Scenario: No verification file
- **WHEN** the `ARCHIVE` folder has no `verification.md`
- **THEN** code 1 with `LIVE: no Live Scenario in <path>`, the `LIVE` command did not run

### Requirement: Command timeouts
Every command `accept` and `land-local` run SHALL be stopped with its process group after a timeout: the seconds of `SDD_DISPATCH_TIMEOUT` when it is a whole number of ASCII digits from 1 to 2147483, else 600. In `accept` a timeout SHALL be a mismatch `<field>: timeout after <n> s`; in `land-local` a `--check` timeout SHALL count as a failed check and a git step timeout as a failed step (code 1), the line `<command>: timeout after <n> s`.

#### Scenario: A hanging LIVE
- **WHEN** the `LIVE` command does not end
- **THEN** after 600 seconds `accept` exits 1 with `LIVE: timeout after 600 s`

#### Scenario: A child keeps the output open
- **WHEN** `SDD_DISPATCH_TIMEOUT=1` and the `LIVE` command is `sleep 100 | cat`
- **THEN** `accept` exits 1 with `LIVE: timeout after 1 s` within 10 seconds

#### Scenario: A hanging check in land-local
- **WHEN** `SDD_DISPATCH_TIMEOUT=1` and a `--check` command does not end
- **THEN** `land-local` treats it as a failed check by Local land after a red check, the output names `timeout after 1 s`

#### Scenario: A broken value
- **WHEN** `SDD_DISPATCH_TIMEOUT` is `abc`, `0`, `١٢` or `2147484`
- **THEN** the timeout is 600 seconds
