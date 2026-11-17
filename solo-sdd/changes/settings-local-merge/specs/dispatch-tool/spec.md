## MODIFIED Requirements

### Requirement: Local land command
`sdd-dispatch.py land-local <MAIN> <WORKTREE> <id> [--check <command>]...` SHALL stop at the first failure: before the merge, edited tracked files of `MAIN` give code 2, a branch writing a file `MAIN` has untracked code 6; the merge by `delivery.local-merge`, a conflict: abort, code 6; `sdd-worktree.py transport`, code 3: `reset --keep` to the pre-merge commit, code 6. Codes 2 and 6 name the files; `sdd-worktree.py` output is printed as is.

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

#### Scenario: The default merge
- **WHEN** `delivery.local-merge` is not set and `land-local` merges `change/b`
- **THEN** the main branch gets a merge commit with two parents, as `git merge --no-ff --no-edit` makes

#### Scenario: Squash
- **WHEN** `delivery.local-merge` is `squash`, `change/b` has three own commits, the last named `b: done`
- **THEN** the main branch gets one commit with one parent named `b: done`, and the cleanup deletes `change/b`

#### Scenario: Rebase
- **WHEN** `delivery.local-merge` is `rebase`, and the main branch moved ahead after `change/b` started
- **THEN** the main branch history is linear with the commits of `change/b` on top, no merge commit

#### Scenario: A squash conflict
- **WHEN** `delivery.local-merge` is `squash` and the squash gives a conflict in `README.md`
- **THEN** the index and tree are reset to the previous commit, code 6 names `README.md`, the worktree and branch are in place

#### Scenario: Transport lines kept
- **WHEN** `sdd-worktree.py transport` prints `not transported: docs/notes.md` and ends with code 0
- **THEN** the line is printed as is and the run goes on

#### Scenario: A rebase conflict
- **WHEN** `delivery.local-merge` is `rebase` and rebasing `change/b` onto the main branch gives a conflict in `README.md`
- **THEN** the rebase runs in a temporary worktree that is removed, code 6 names `README.md`, the main branch, `change/b` and WORKTREE are on their previous commits

#### Scenario: Rebase keeps ignored copies
- **WHEN** `delivery.local-merge` is `rebase`, the main branch moved ahead, and `change/b` takes `solo-sdd/changes/archive/` out of git while `MAIN` tracks it
- **THEN** code 0, the archive files are on the disk of `MAIN` after the transfer: WORKTREE moves to the rebased commit with `reset --keep` and keeps its ignored copies

#### Scenario: Squash without an own commit
- **WHEN** `delivery.local-merge` is `squash` and `change/b` has no own commit along the first parent other than merge and empty commits
- **THEN** code 1 with "not merged: merge: no title in the last own commit of the branch", the main branch is unchanged

### Requirement: Local land checks and cleanup
After the merge and the transfer `land-local` SHALL run every `--check` and `solo-sdd validate --all` once each. All passed: `sdd-worktree.py remove`, `git branch -d change/<id>` (`-D` after `squash` and `rebase`: git does not see the branch as merged), code 0 and the merge hash. A failure of `remove` or the branch deletion does not roll back the merge: code 1 with the line "merged <hash>, not cleaned: <step>: <error>".

#### Scenario: Everything passed
- **WHEN** the merge, the transfer and all checks passed
- **THEN** code 0, the worktree is removed, the branch `change/<id>` is deleted

#### Scenario: Cleanup after squash
- **WHEN** `delivery.local-merge` is `squash`, the merge and all checks passed
- **THEN** code 0, `change/<id>` is deleted although its commits are not in the main branch by hash
