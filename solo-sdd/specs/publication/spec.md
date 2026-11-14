# publication Specification

## Purpose
solo-sdd lies in an open GitHub repository without the previous history and without `solo-sdd/` in any commit, every change is checked in CI, and installation by the README works on a clean machine.

## Requirements

### Requirement: First publication without history
`scripts/publish-first.sh` without arguments SHALL check the preconditions, build the future commit, check it and print the command plan, without changing branches, tags, remotes, the index and working files. With `--go` it SHALL run the plan. Open changes and `change/*` branches are not preconditions. The script SHALL NOT delete branches, worktrees and files. On a violation of any precondition or check the script prints all violations and ends with code 1, changing nothing of the above.

#### Scenario: A dry run
- **WHEN** the preconditions hold and the script runs without arguments
- **THEN** the plan is printed, `git branch`, `git tag`, `git remote`, `git status` and `.gitignore` did not change, exit code 0

#### Scenario: Open changes do not interfere
- **WHEN** `solo-sdd/changes/` has other open changes and there is a branch `change/x`, and the other preconditions hold
- **THEN** the script passes, the branch `change/x` stays in place

#### Scenario: A precondition is violated
- **WHEN** any one precondition is violated and the script runs, including with `--go`
- **THEN** the script names the violation and ends with code 1, branches, remotes, the index and files did not change

#### Scenario: A personal file in the tree
- **WHEN** a file from the "single owner" block is tracked by git
- **THEN** the script names it and ends with code 1, changing nothing, even with `--go`

#### Scenario: Publication
- **WHEN** the script runs with `--go`
- **THEN** `origin/main` has exactly one commit; the tree differs from `history-local` only by the absence of `solo-sdd/` and `docs/waiting.md` and the line `solo-sdd/` in `.gitignore`; `git log origin/main -- solo-sdd` is empty; the remote has only `main` and the tag `v0.1.0`; the files `solo-sdd/` and `docs/waiting.md` lie on disk and git ignores them; `history-local` and the `change/*` branches are in place; the repository is public

#### Scenario: Pushing the old history
- **WHEN** after publication `history-local` is pushed, any of its commits under another name, a `change/*` branch from the old history, a commit with `solo-sdd/` or a tag on a tree
- **THEN** the push is refused by the `pre-push` hook, nothing appeared on the remote

#### Scenario: An existing hook
- **WHEN** before the run the repository had its own `pre-push`
- **THEN** it is kept and called after the check with the same input, its refusal refuses the push

#### Scenario: A failure after renaming main
- **WHEN** a plan step after renaming `main` to `history-local` ended with an error
- **THEN** the script stops with a non-zero code and a message which step failed and that the old history is in `history-local`; there are no rollbacks, a repeated run refuses by a precondition, and the rest of the plan is run with the commands from the printed plan

### Requirement: Continuous integration
`.github/workflows/test.yml` SHALL run on `push` and `pull_request` to `main` on `ubuntu-latest`, on a pushed `v*` tag on `macos-latest` only, and on `workflow_dispatch` on both, with `contents: read`, every action pinned by a full commit hash. Steps: install Hypothesis and `pyflakes==3.4.0` for `/usr/bin/python3`; run `pyflakes` on `solo_sdd/`, `global/`, `scripts/` and `sync.py`; run `tests/run.py`; then `validate --all` when the tree has `solo-sdd/`. Any failure SHALL fail the run.

#### Scenario: A broken test
- **WHEN** a test from `tests/` fails in a PR
- **THEN** the CI run on Ubuntu is red, and the log names the test

#### Scenario: A broken spec
- **WHEN** a PR adds to `solo-sdd/specs/` a requirement without a scenario
- **THEN** the CI run on Ubuntu is red, the log shows the step `Validate the process tree` and names the requirement

#### Scenario: A tree without solo-sdd
- **WHEN** the workflow runs on a tree without `solo-sdd/`, as the commit `scripts/publish-first.sh` builds
- **THEN** the step `Validate the process tree` prints `no solo-sdd/: nothing to check` and passes

#### Scenario: A lint error
- **WHEN** a PR adds an unused import to `solo_sdd/cli.py`
- **THEN** the run is red at the step `Lint`, the log names the file and the line

#### Scenario: Pinned actions
- **WHEN** `tests/test_release.py` reads every file `.github/workflows/*.yml`
- **THEN** every `uses:` value ends with `@` and 40 hexadecimal digits, and a value pinned by a tag or a branch fails the test naming the file and the value

#### Scenario: Operating systems by event
- **WHEN** `tests/test_release.py` reads `test.yml`
- **THEN** a `push` to `main` and a `pull_request` select only `ubuntu-latest`, a `v*` tag only `macos-latest` (`release.yml` runs Ubuntu for a tag), `workflow_dispatch` both, and a mutant that adds `macos-latest` to `pull_request` fails the test

### Requirement: Install from clone
`README.md` SHALL name as the installation a clone of `https://github.com/veraetogrex-portfolio/solo-sdd` and `python3 sync.py push`. These commands on a clone of the new commit and a clean home folder SHALL give `python3 sync.py status` with all lines `ok`.

#### Scenario: A clone on a clean home folder
- **WHEN** the commands of the README "Installation" section are run on a fresh clone with a temporary home folder
- **THEN** `sync.py push` ends with code 0, all lines of `sync.py status` equal `ok`

### Requirement: First publication preconditions
The preconditions of `scripts/publish-first.sh` SHALL be:
- the current branch is `main`, no branch `history-local`, no tag `v0.1.0`, no remote `origin`;
- `git worktree list` is one line;
- `git status --porcelain` is empty except under `solo-sdd/` and `docs/waiting.md`;
- `python3 tests/test_public_tree.py` gives code 0;
- `gh api user --jq .login` equals `veraetogrex-portfolio`;
- `gh repo view veraetogrex-portfolio/solo-sdd` fails with "not found" (`Could not resolve to a Repository`).

#### Scenario: Edits in solo-sdd do not interfere
- **WHEN** uncommitted edits exist only under `solo-sdd/` and in `docs/waiting.md`
- **THEN** the clean `git status` precondition holds: these paths do not go into the new commit and stay on disk

#### Scenario: Another gh error
- **WHEN** `gh repo view veraetogrex-portfolio/solo-sdd` ends with another error, not "not found"
- **THEN** it is the violation "could not check", not a permission: code 1

### Requirement: First publication commit
The future commit of `scripts/publish-first.sh` SHALL be built from the `HEAD` tree without `solo-sdd/` and `docs/waiting.md`, with the line `solo-sdd/` in `.gitignore` if it is not there. Before switching branches the script SHALL check: the commit tree has no `solo-sdd/`, `docs/waiting.md` and paths from the "single owner" block of `.gitignore`, this block is at least 10 lines, `git log <commit> -- solo-sdd` is empty.

#### Scenario: A short owner block
- **WHEN** the "single owner" block in `.gitignore` is shorter than 10 lines
- **THEN** the script names the violation and ends with code 1, changing nothing

### Requirement: First publication plan
The plan of `scripts/publish-first.sh` SHALL be: rename `main` to `history-local`; make `main` a parentless branch on the new commit with the message `solo-sdd 0.1.0`, changing no working files except the `.gitignore` line; `git tag v0.1.0`; install the `pre-push` hook; `gh repo create veraetogrex-portfolio/solo-sdd --public --source . --remote origin --description <description>`; `gh repo edit veraetogrex-portfolio/solo-sdd --add-topic` for the topics; push (First publication push).

#### Scenario: The plan in a dry run
- **WHEN** the script runs without arguments with the preconditions met
- **THEN** the printed plan lists these steps in this order

#### Scenario: Repository topics
- **WHEN** the step `gh repo edit … --add-topic` runs
- **THEN** the topics `claude-code`, `codex`, `spec-driven-development` and the OpenSpec topic are added

### Requirement: First publication push
As the last plan step the script SHALL run `git push -u origin refs/heads/main:refs/heads/main refs/tags/v0.1.0:refs/tags/v0.1.0` and SHALL push only these two refs, by name, without `--all`, `--mirror` and `--tags`.

#### Scenario: Only two refs
- **WHEN** the script runs with `--go`, and the repository has the branches `history-local` and `change/*`
- **THEN** only `main` and the tag `v0.1.0` appeared on the remote

### Requirement: First publication pre-push hook
The `pre-push` hook SHALL refuse a push if the refs being sent include `refs/heads/history-local`, a commit sharing history with `history-local` under any name, a commit whose history has `solo-sdd`, or a ref not to a commit (a tag on a tree or a file). An existing `pre-push` is saved by the script as `pre-push.before-publish` and called after its own check with the same arguments and input.

#### Scenario: A tag on a file
- **WHEN** after publication a tag pointing to a blob is pushed
- **THEN** the push is refused by the `pre-push` hook

### Requirement: Change archive outside git
`solo-sdd/changes/archive/` SHALL be git-ignored and kept only in the working folder; `solo-sdd/specs/` and the open changes SHALL stay in git. `sdd-worktree.py transport`, run by `land-local` or `sdd-pr.py land`, SHALL bring an archived folder into the main folder and never carry the removal of an archive file. No step SHALL delete an archived file of the main folder: `undo` keeps a file git tracks again, `land-local` refuses a branch that would overwrite an untracked file.

#### Scenario: An archive in a worktree
- **WHEN** an orchestrator archives a change in its worktree and `land-local` merges it
- **THEN** the main folder has `solo-sdd/changes/archive/<date>-<id>/`, and `git ls-files solo-sdd/changes/archive` prints nothing

#### Scenario: A failed check after the transport
- **WHEN** a check of `land-local` is red after the transport
- **THEN** `sdd-worktree.py undo` removes only the folder this transport created, and the archived folders that were in the main folder before stay

#### Scenario: A rollback of the removal from the index
- **WHEN** `land-local` merges the branch that removes `solo-sdd/changes/archive/` from the index, `transport` puts the archive back on disk, and a check is red
- **THEN** after the rollback the main folder tracks the archive again, every archive file is on disk and `git status` shows no deleted file

#### Scenario: A folder missing in the worktree
- **WHEN** an archived folder the main folder has is deleted in the worktree and `transport` runs
- **THEN** the folder stays in the main folder and `transport` prints `deleted 0`

#### Scenario: A rollback whose reset fails
- **WHEN** `land-local` merges the branch that removes `solo-sdd/changes/archive/` from the index, a red check leaves a tracked file edited, and `reset --keep` refuses
- **THEN** `land-local` prints `rollback failed: reset` and every archive file is still on disk

#### Scenario: A branch that edits an archived file
- **WHEN** a branch cut before the ignore line edits an archived file, and the main folder already ignores the archive and holds that file with other content
- **THEN** `land-local` prints `not merged: merge would overwrite untracked files: <path>`, exits 6 without merging, and the main folder's file is unchanged

#### Scenario: A branch cut before the ignore line
- **WHEN** a branch cut from a `main` without the ignore line archives its change, so the archived folder is committed, and it is merged
- **THEN** `tests/test_public_tree.py` names each tracked path under `solo-sdd/changes/archive/`, and `land-local` refuses with "check red with the change"

### Requirement: Publication without the private history
`docs/release.md` SHALL describe the owner's step that publishes the repository without its private history: first, in every clone, install the guard and rename `origin` to `private` at the `solo-sdd-private` address; then rename the GitHub repository to it, create an empty public `veraetogrex-portfolio/solo-sdd`, make one new root commit the local `main`, keep the old `main` as `history-private`, and push `main` to the public `origin`. It SHALL say the agent never runs this step.

#### Scenario: The owner publishes
- **WHEN** the owner follows `docs/release.md`
- **THEN** the public repository has one commit and no `solo-sdd/changes/archive/` path in it

#### Scenario: Work after the publication
- **WHEN** the step's commands ran in a clone
- **THEN** local `main` is the public root commit and tracks `origin/main`, the remote `private` names the old repository, and `history-private` holds the old `main`

### Requirement: CI run cost
`test.yml` SHALL set `concurrency` grouped by the workflow and the ref with `cancel-in-progress: true`. Its runner step SHALL be `tests/run.py --tier slow` for `push` and `pull_request` and `tests/run.py --tier release` for a tag and `workflow_dispatch`; the tests step of `release.yml` SHALL be `tests/run.py --tier release`. The lint step SHALL come before the runner step.

#### Scenario: The workflow text
- **WHEN** `tests/test_release.py` reads `test.yml` and `release.yml`
- **THEN** the `concurrency` group names the workflow and `github.ref` with `cancel-in-progress: true`, the runner steps carry the tiers above, and `Lint` comes before them

#### Scenario: A PR pushed twice
- **WHEN** Actions starts jobs and a PR is pushed twice in a row
- **THEN** only an Ubuntu job runs for each push, and the first run is cancelled

### Requirement: Old history push guard
`scripts/pre-push-guard.sh`, installed as the `pre-push` hook, SHALL refuse a push whose refs include a commit sharing history with the local branch `history-local` or `history-private`, or a ref not to a commit, and SHALL pass any other push.

#### Scenario: An old branch pushed
- **WHEN** after the publication `history-private` or a branch cut from it is pushed to `origin` under any name
- **THEN** the push is refused, the hook names the ref, and the remote has only `main`

#### Scenario: A new change branch
- **WHEN** a branch cut from the new `main` is pushed, or a remote branch is deleted
- **THEN** the push passes

#### Scenario: A tag on a blob
- **WHEN** a tag pointing to a blob is pushed
- **THEN** the push is refused and the hook names the ref

### Requirement: Merge only on green CI
`AGENTS.md` and `docs/release.md` SHALL say that an agent merges a PR only when `sdd-pr.py wait` gives `CI: green`, and that on `CI: red`, `CI: infra` or `CI: codeql` the agent fixes, reruns and waits again by `/ship` or `spec-dispatch`, and a PR that is still not green waits for the owner; they SHALL NOT tell an agent to merge around a red or missing check, and SHALL NOT say that Actions starts no jobs.

#### Scenario: A PR with green checks
- **WHEN** an agent delivers a change in `pr` mode and `wait` gives `CI: green`
- **THEN** both files let the agent merge it through `sdd-pr.py merge`, where `delivery.merge-by` lets an agent merge

#### Scenario: A PR whose checks are red or did not start
- **WHEN** `wait` gives `CI: red`, `CI: infra` or `CI: codeql`
- **THEN** both files send the agent to the fixes and reruns of `/ship` or `spec-dispatch` first, and say that a PR that is still not green waits for the owner and that an agent never merges around a red or missing check
