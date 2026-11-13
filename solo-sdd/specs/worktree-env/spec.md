# worktree-env Specification

## Purpose
One script prepares a change worktree for work the same way as the main project folder, carries the git-ignored artifacts back without losing neighbouring edits and cleans up after itself, so neither the dispatcher nor the orchestrators solve this again.

## Requirements

### Requirement: Worktree setup
`sdd-worktree.py setup <MAIN> <WORKTREE>` SHALL create the snapshot folder `<WORKTREE>.base/` (outside the worktree) even if there is nothing to copy: after any successful `setup` it exists; copy the artifacts by the requirement Worktree setup copies; link the dependencies by the requirements Worktree node_modules links and Worktree venv link; run the prepare command and finish by the requirement Worktree setup command and result.

#### Scenario: A project with an ignored solo-sdd
- **WHEN** in `MAIN` `solo-sdd/` and `AGENTS.md` are in `.gitignore`, and `apps/desktop` and the root have `node_modules`
- **THEN** `WORKTREE` has copies of `solo-sdd/` and `AGENTS.md`, a snapshot in `<WORKTREE>.base/`, two `node_modules` folders of links, and `git -C <WORKTREE> status --short` is empty

#### Scenario: A workspace package
- **WHEN** `MAIN/node_modules/@scope/core` holds a relative link `../../packages/core`, and in `WORKTREE` the file `packages/core/index.js` is changed
- **THEN** `WORKTREE/node_modules/@scope/core` points to `WORKTREE/packages/core`, importing `@scope/core` from `WORKTREE` gives the changed file, and the external package `WORKTREE/node_modules/left-pad` is a link to `MAIN/node_modules/left-pad`

#### Scenario: Everything is tracked
- **WHEN** `solo-sdd/` and `AGENTS.md` in `MAIN` are under git, there are no dependencies
- **THEN** nothing is copied, the folder `<WORKTREE>.base/` exists and is empty, exit code 0; the following `refresh` and `transport` end with code 0 and change neither `MAIN` nor `WORKTREE`

#### Scenario: A snapshot after any successful setup
- **WHEN** `setup` ended with code 0, even if there was nothing to copy
- **THEN** the folder `<WORKTREE>.base/` exists

### Requirement: Ignored artifacts transport
`sdd-worktree.py transport <MAIN> <WORKTREE>` SHALL carry into `MAIN` the changes of the ignored artifacts of the `setup` set:
- a file in `WORKTREE` and not in the snapshot: copy it into `MAIN`;
- a file changed in `WORKTREE` against the snapshot: a `git merge-file` merge, base the snapshot, ours `MAIN`, theirs `WORKTREE`;
- a file in the snapshot, deleted in `WORKTREE` (the change folder after the archive): delete it in `MAIN` if it matches the snapshot there, except under `changes/archive/`.

#### Scenario: Two lines in AGENTS.md
- **WHEN** after the worktree was created `MAIN` got a line of a neighbouring change, and `WORKTREE` its own line in another place of `AGENTS.md`
- **THEN** after the transfer `MAIN` has both lines, exit code 0

#### Scenario: A change archive
- **WHEN** in `WORKTREE` the change moved into `solo-sdd/changes/archive/`, and the capability spec is updated
- **THEN** `MAIN` got the archive folder, there is no active change folder, the spec is updated

#### Scenario: A conflict
- **WHEN** the same spec line was changed both in `MAIN` and in `WORKTREE`
- **THEN** exit code 3, the list names the file, no file of `MAIN` is changed

#### Scenario: Undoing the transfer
- **WHEN** the transfer passed, and the checks after merge failed
- **THEN** after `undo` the ignored artifacts of `MAIN` match the state before the transfer: the change archive is deleted, the specs and `AGENTS.md` are as before

#### Scenario: An archived folder gone from WORKTREE
- **WHEN** an archived folder of the snapshot is deleted in `WORKTREE`, changed or not in `MAIN`
- **THEN** `MAIN` keeps it, the command prints `deleted 0` and ends with code 0

#### Scenario: An empty set
- **WHEN** the set of ignored artifacts is empty
- **THEN** the command does nothing and ends with code 0

### Requirement: Worktree removal
`sdd-worktree.py remove <MAIN> <WORKTREE>` SHALL delete the `node_modules` link folders created by `setup` (only with the `.sdd-worktree` mark) and the `.venv` link, the snapshot `<WORKTREE>.base/`, the copy `<WORKTREE>.undo/`, the record `<WORKTREE>.start` and the worktree (`git worktree remove` without `--force`: uncommitted work in the worktree is not erased, the command fails), without touching the folders the links point to.

#### Scenario: Cleanup
- **WHEN** the worktree was prepared by `setup` and the change is merged
- **THEN** `git worktree list` does not show the worktree, there is no snapshot, undo copy or `.start` record, `node_modules` in `MAIN` is in place

### Requirement: Worktree refresh
`sdd-worktree.py refresh <MAIN> <WORKTREE>` SHALL carry into `WORKTREE` the changes of the ignored artifacts of `MAIN` made after `setup`: a three-way merge where the base is the snapshot, ours is `WORKTREE`, theirs is `MAIN`; new files of `MAIN` are copied; a file deleted in `MAIN` (for example, a neighbouring change folder after its archive) is deleted in `WORKTREE` if it equals the snapshot there, otherwise it is a conflict and the file in `WORKTREE` stays.

#### Scenario: A neighbouring change appended to AGENTS.md
- **WHEN** after `setup` `MAIN/AGENTS.md` got a line of a neighbouring change, and `WORKTREE/AGENTS.md` its own
- **THEN** after `refresh` `WORKTREE/AGENTS.md` has both lines, the snapshot equals `MAIN/AGENTS.md`, code 0

#### Scenario: A conflict on update
- **WHEN** one spec line was changed both in `MAIN` and in `WORKTREE`
- **THEN** the file in `WORKTREE` has conflict markers, code 3, the file is named

#### Scenario: A neighbouring change went to the archive
- **WHEN** after `setup` in `MAIN` the folder `solo-sdd/changes/<neighbour>/` moved to `solo-sdd/changes/archive/<date>-<neighbour>/`, and its files in `WORKTREE` did not change
- **THEN** after `refresh` `WORKTREE` has no `solo-sdd/changes/<neighbour>/`, the neighbour's archive exists, code 0

#### Scenario: Deleted in MAIN, changed in WORKTREE
- **WHEN** a neighbouring change folder is deleted in `MAIN` after `setup`, and its file in `WORKTREE` is changed
- **THEN** `refresh` gives code 3 and names the file; `transport` gives code 3, the folder did not appear in `MAIN`; after deleting the file in `WORKTREE` `transport` gives code 0

#### Scenario: A conflict with markers
- **WHEN** a conflict arose on `refresh`
- **THEN** the file in `WORKTREE` gets conflict markers for manual resolution, the command prints the file list and ends with code 3

### Requirement: Hook self-check is location independent
The hook self-check `tests/test_work_hooks.py` SHALL give one verdict in the main project folder and in a worktree from `$TMPDIR`. The projects on which it checks writing outside the project folder, the launch folder and an NFD path SHALL lie outside the working copy and outside the temporary folders where the hook always allows writing.

#### Scenario: A worktree from a temporary folder
- **WHEN** the self-check runs in a worktree from `$TMPDIR`
- **THEN** a write into a project outside the launch folder is refused, with the launch folder given it passes, and the self-check ends with code 0

#### Scenario: A copy outside a temporary folder
- **WHEN** the self-check runs in a working copy outside temporary folders
- **THEN** it ends with code 0, as in a worktree

#### Scenario: A broken hook is visible in a worktree
- **WHEN** in a copy from `$TMPDIR` the hook stops refusing writes outside the project, stops taking the launch folder into account or normalising paths to one form
- **THEN** the self-check ends with a non-zero code

### Requirement: Discard unused worktree
`sdd-worktree.py setup` SHALL as its first action write the full hash of the worktree `HEAD` into the file `<WORKTREE>.start` (outside the worktree), before copying and the prepare command, so the record exists even after a failed preparation.

`sdd-worktree.py discard <MAIN> <WORKTREE>` SHALL remove a worktree with no commit made after `setup`, by the requirements Discard refusal, Discard cleanup and Discard result.

#### Scenario: The preparation created a file and failed
- **WHEN** `setup` ran a prepare command that created `junk.txt` in the worktree and returned code 1
- **THEN** `discard` ends with code 0, `git worktree list` has no worktree, there is no branch `change/<id>`, `MAIN` is unchanged

#### Scenario: The branch has a commit
- **WHEN** after `setup` a commit was made in the worktree
- **THEN** `discard` ends with code 1 and deletes nothing: neither the worktree, nor the branch, nor the snapshot

#### Scenario: No start record
- **WHEN** there is no `<WORKTREE>.start` (the worktree was prepared by an earlier version of the script)
- **THEN** `discard` ends with code 1 and deletes nothing

#### Scenario: The start commit only in this branch
- **WHEN** the worktree `HEAD` equals the recorded hash, but no other ref of `MAIN` holds this commit (the main branch was rolled back)
- **THEN** `discard` ends with code 1 and deletes nothing

#### Scenario: A detached HEAD
- **WHEN** `git checkout --detach` was run in the worktree, `HEAD` equals the recorded hash
- **THEN** `discard` ends with code 0, the worktree is removed, the branch `change/<id>` is in place, the output has `worktree discarded: no branch`

### Requirement: Individually ignored files
`sdd-worktree.py setup` SHALL include in the ignored artifact set the document files of `MAIN` (`.md`, `.txt`, `.rst`, `.adoc`) up to 1 MiB that git ignores individually, not as part of an ignored folder (`git ls-files --others --ignored --exclude-standard --directory`, entries without a trailing `/`; a file in a folder git ignores is excluded even if the folder has a tracked file), except links, `node_modules`, `.venv` and `.env*`.

#### Scenario: A project document under .gitignore
- **WHEN** in `MAIN` `docs/` is under git, and `docs/architecture.md` is in `.gitignore`; the change appended a line to it in `WORKTREE`, and meanwhile a neighbouring change appended another line in `MAIN`
- **THEN** after `transport` `MAIN/docs/architecture.md` has both lines, code 0

#### Scenario: An ignored folder does not get into the set
- **WHEN** in `MAIN` the folders `out/` and `.cache-data/` with files inside are ignored
- **THEN** `setup` does not copy them, `transport` neither carries nor names them

#### Scenario: An ignored folder with a tracked file
- **WHEN** the folder `out/` is in `.gitignore`, `out/keep.txt` is tracked, and `out/app.md` lies next to it
- **THEN** `setup` does not copy it, `transport` neither carries nor names it

#### Scenario: A generated file and settings
- **WHEN** `tsconfig.tsbuildinfo` and `.env` are ignored individually, and both are changed in `WORKTREE`
- **THEN** `setup` did not copy them; `transport` does not touch them in `MAIN`, names `tsconfig.tsbuildinfo` and `.env` in the line "not transported", code 0

#### Scenario: A large document
- **WHEN** an individually ignored `docs/dump.md` of 5 MiB is changed in `WORKTREE`
- **THEN** `transport` does not carry it, prints "not transported: docs/dump.md" and ends with code 0

#### Scenario: A conflict in a document
- **WHEN** one line of `docs/architecture.md` was changed both in `MAIN` and in `WORKTREE`
- **THEN** `transport` gives code 3 and names the file, `MAIN` is not changed

#### Scenario: How individually ignored files are found
- **WHEN** `setup` collects individually ignored files
- **THEN** it takes the entries of `git ls-files --others --ignored --exclude-standard --directory` without a trailing `/`; a file in a folder git ignores is excluded even if the folder has a tracked file

### Requirement: Command after refresh
If the `AGENTS.md` section "Working copy" has the item "After refresh: `<command>`", `sdd-worktree.py refresh` SHALL after a transfer without conflicts run this command through `sh -c` with `WORKTREE` as the working folder, closed stdin and a limit of 600 s. Success is one line "after refresh: <command> — code 0" without the command output. A non-zero code or an exceeded limit: `refresh` SHALL end with code 4. On a conflict (code 3) and without the item the command is not run.

#### Scenario: What is printed on failure
- **WHEN** the after-update command ended with a non-zero code or exceeded the limit
- **THEN** `refresh` prints the command name, the code or "timeout" and at most the last 20 lines of its output; the transfer and the snapshot update are already done

#### Scenario: Rebuilding a helper
- **WHEN** "Working copy" has "After refresh: `npm run build:ocr`", and `refresh` carried the changes without conflicts
- **THEN** `npm run build:ocr` ran in `WORKTREE`, code 0, one line about the command is printed without its output

#### Scenario: The build failed
- **WHEN** the after-update command ended with code 1
- **THEN** `refresh` gives code 4, the command and the last output lines are printed, the snapshot is already updated

#### Scenario: A conflict
- **WHEN** `refresh` found a conflict and ends with code 3
- **THEN** the after-update command did not run

### Requirement: Worktree setup copies
`sdd-worktree.py setup` SHALL copy from `MAIN` into `WORKTREE` all files under `solo-sdd/`, the files `AGENTS.md`, `CLAUDE.md` and the paths from the `AGENTS.md` section "Working copy" that git in `MAIN` ignores (`git check-ignore`) and that are missing in `WORKTREE`; not touch tracked files; save the copied files into the snapshot `<WORKTREE>.base/`, the base for carrying them back.

#### Scenario: The file is already in the worktree
- **WHEN** an ignored `AGENTS.md` already lies in `WORKTREE`
- **THEN** `setup` does not overwrite it

### Requirement: Worktree node_modules links
For every `node_modules` folder in `MAIN` no deeper than three levels `sdd-worktree.py setup` SHALL create in `WORKTREE` a folder of the same name made of links, if there is none: every entry of `MAIN/node_modules` is a link to it by an absolute path, except link entries (requirement Worktree node_modules symlink entries); the `@scope` and `.bin` folders are expanded the same way one level deeper; other hidden folders (caches) are skipped; the mark `.sdd-worktree` is put into the created folder.

#### Scenario: Scope, .bin and caches
- **WHEN** `MAIN/node_modules` has `@scope/`, `.bin/` and `.cache/`
- **THEN** `@scope` and `.bin` are expanded the same way one level deeper, `.cache` and other hidden folders (caches) are skipped

#### Scenario: Deeper than three levels
- **WHEN** `node_modules` lies in `MAIN` at the fourth nesting level
- **THEN** no link folder is created for it

### Requirement: Worktree venv link
For `.venv` at the root of `MAIN` `sdd-worktree.py setup` SHALL create a symbolic link to it in `WORKTREE` if there is none, and add to `info/exclude` of the shared git directory the patterns `node_modules` and `.venv` without a trailing slash if they are not there, so the links do not get into `git status` and commits.

#### Scenario: The .venv link is invisible to git
- **WHEN** `MAIN` has `.venv`, and `info/exclude` has no `.venv` pattern
- **THEN** `WORKTREE` has the `.venv` link, `info/exclude` has the line `.venv`, `git -C <WORKTREE> status --short` does not show it

### Requirement: Transport conflict
On a merge conflict or a deletion of a file changed in `MAIN` (outside the archive, which the requirement Ignored artifacts transport keeps) `sdd-worktree.py transport` SHALL NOT change `MAIN` for any file, SHALL print the file list and end with code 3.

#### Scenario: Deleted in WORKTREE, changed in MAIN
- **WHEN** a snapshot file is deleted in `WORKTREE`, and changed in `MAIN`
- **THEN** code 3, the file is named, no file of `MAIN` is changed

### Requirement: Transport undo
Before changing `MAIN` the `transport` command SHALL save the previous versions of the affected `MAIN` files into `<WORKTREE>.undo/`; `sdd-worktree.py undo <MAIN> <WORKTREE>` returns them and deletes the files the transfer created and git does not track, so `MAIN` becomes as it was before the transfer. `<WORKTREE>.undo/` is overwritten by every transfer that changes `MAIN`; `undo` returns the state before the last such transfer; a transfer with a conflict does not touch it.

#### Scenario: A conflict after a successful transfer
- **WHEN** a transfer passed, then the next transfer gave a conflict, and `undo` was run
- **THEN** `MAIN` is returned to the state before the successful transfer: the conflicting transfer did not overwrite `<WORKTREE>.undo/`

#### Scenario: A file tracked again
- **WHEN** the transfer created files a merge had removed from the index, and the rollback reset tracks them again before `undo`
- **THEN** `undo` keeps them on disk and `git status` shows no deleted file

### Requirement: Refresh snapshot update
After `refresh` the snapshot for all affected files, including conflicts with markers, SHALL be updated to the `MAIN` version: a later `transport` merges the orchestrator's resolution against the new state of `MAIN`. For conflicts without markers (a file deleted on one side and changed on the other, or new on both sides and different) the snapshot stays: `transport` does not carry such a file until `WORKTREE` is brought to `MAIN`, and neither resurrects nor deletes it silently.

#### Scenario: New on both sides and different
- **WHEN** after `setup` the file `docs/x.md` appeared both in `MAIN` and in `WORKTREE` with different text
- **THEN** `refresh` gives code 3, its snapshot stays; `transport` does not carry it until `WORKTREE/docs/x.md` equals the `MAIN` version

#### Scenario: What brought to MAIN means
- **WHEN** a conflict file without markers in `WORKTREE` is deleted after `MAIN` or became equal to its version
- **THEN** `WORKTREE` is brought to `MAIN`, `transport` no longer holds this file

### Requirement: Discard refusal
`sdd-worktree.py discard` SHALL change nothing, print the reason to stderr and end with code 1 if there is no `<WORKTREE>.start`, the worktree `HEAD` does not equal the recorded hash, or this commit is reachable only from the branch that would have to be deleted (no other local branch, remote branch or tag holds it). If `git worktree remove` or `git branch -D` failed, `discard` SHALL print the error to stderr and end with code 1; `<WORKTREE>.start` then stays.

#### Scenario: git worktree remove failed
- **WHEN** `git worktree remove --force` ended with an error
- **THEN** `discard` prints it to stderr, code 1, `<WORKTREE>.start` is in place

### Requirement: Discard cleanup
With no refusal, `sdd-worktree.py discard` SHALL delete the `node_modules` link folders marked `.sdd-worktree` and the `.venv` link, `<WORKTREE>.base/`, `<WORKTREE>.undo/`, run `git -C <MAIN> worktree remove --force <WORKTREE>` and delete the worktree's branch (`git branch -D`; nothing with a detached `HEAD`), then `<WORKTREE>.start` and the dispatcher's `mktemp` folder (`sdd-*`) if empty. `discard` SHALL NOT touch the link targets and the files of `MAIN`.

#### Scenario: Link targets are intact
- **WHEN** `discard` deleted the link folder `WORKTREE/node_modules`
- **THEN** `MAIN/node_modules` and its packages are in place

### Requirement: Discard keeps commits
After `discard` every commit reachable before the call from any ref of `MAIN` (a local branch, a remote branch, a tag) SHALL stay reachable from one of them: `discard` loses no commits in any worktree state.

#### Scenario: A commit only in the change branch
- **WHEN** the branch `change/x` has a commit that is in no other ref of `MAIN`
- **THEN** `discard` refuses, the branch and the commit are in place

### Requirement: Untransported ignored files
`sdd-worktree.py transport` SHALL print "not transported: <files>" for individually ignored files outside the set that exist in `MAIN` and in `WORKTREE` and differ, without changing the exit code.

#### Scenario: An identical file outside the set
- **WHEN** an individually ignored `.env` outside the set exists in `MAIN` and in `WORKTREE` and is the same
- **THEN** there is no "not transported" line about it

### Requirement: Worktree setup command and result
`sdd-worktree.py setup` SHALL run the prepare command from the "Working copy" section, if there is one, with `WORKTREE` as the working folder, then print one summary line (files copied, links, the command) and end with code 0; on a `setup` error, a non-zero code and the reason in stderr.

#### Scenario: The prepare command in the worktree
- **WHEN** the "Working copy" section of `AGENTS.md` has a prepare command
- **THEN** `setup` runs it with `WORKTREE` as the working folder

#### Scenario: No prepare command
- **WHEN** the "Working copy" section has no prepare command
- **THEN** `setup` runs no prepare command

#### Scenario: The summary line
- **WHEN** `setup` ended with code 0
- **THEN** one summary line names how many files were copied, how many links created and which prepare command ran

### Requirement: Worktree node_modules symlink entries
An entry of `MAIN/node_modules` that is itself a symbolic link (an npm workspace package, `.bin` files) `sdd-worktree.py setup` SHALL reproduce in the `WORKTREE` link folder with the same target, so a relative link points to the package of `WORKTREE` itself.

#### Scenario: A relative package link
- **WHEN** `MAIN/node_modules/@scope/core` holds a relative link `../../packages/core`
- **THEN** `WORKTREE/node_modules/@scope/core` is a link with the same target `../../packages/core`, it points to `WORKTREE/packages/core`

### Requirement: Discard result
Having removed the worktree, `sdd-worktree.py discard` SHALL print `worktree discarded: <branch>` (with a detached `HEAD`, `worktree discarded: no branch`) and end with code 0; uncommitted and untracked files in the worktree are lost: they are files of the prepare command, not work.

#### Scenario: The discard result
- **WHEN** `discard` removed a worktree on the branch `change/x`
- **THEN** `worktree discarded: change/x` is printed (with a detached `HEAD`, `worktree discarded: no branch`), code 0

#### Scenario: Prepare files are lost
- **WHEN** the worktree holds uncommitted and untracked files
- **THEN** they are lost: they are files of the prepare command, not work

### Requirement: Individually ignored files handling
Individually ignored files of the set (requirement Individually ignored files) `sdd-worktree.py setup` SHALL copy into `WORKTREE` and into the snapshot and keep their list in the snapshot, and `refresh`, `transport` and `undo` SHALL handle them as the rest of the set.

#### Scenario: An individually ignored document on refresh
- **WHEN** an individually ignored `docs/architecture.md` from the set is changed in `MAIN` after `setup`, unchanged in `WORKTREE`, and `refresh` is run
- **THEN** the change is carried into `WORKTREE`, and the snapshot is updated, as for the other files of the set
