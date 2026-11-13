# spec-dispatch Specification

## Purpose
The `spec-dispatch` skill: the main agent hands ready changes to Opus orchestrators, does not read code itself and gets only statuses, then merges the results one at a time and delivers main.

## Requirements

### Requirement: Ready changes and waves
The dispatcher SHALL count a change as ready if its folder has no `CLAIM` and `WAITING`, the main folder has no branch `change/<id>` (it remains from an unmerged run), and `Depends On` in `proposal.md` is `none` or only changes already in `solo-sdd/changes/archive/`. Readiness and order SHALL be computed by the script `sdd-dispatch-plan.py` and recomputed at the start, after every merge and after every orchestrator status.

#### Scenario: A dependent change waits
- **WHEN** `add-words` and `add-lines` are ready, and `add-top-words` depends on `add-words`
- **THEN** `add-words` and `add-lines` are launched at once, `add-top-words` right after the merge of `add-words`, without waiting for `add-lines`

#### Scenario: A shared file
- **WHEN** two ready changes name the same file `textkit/commands/words.py` in `Impact`
- **THEN** the second launches after the merge of the first

#### Scenario: A shared AGENTS.md and a shared capability
- **WHEN** two ready changes both name `AGENTS.md` in `Impact` and both change the capability `cli`, but different requirements
- **THEN** they work at the same time

#### Scenario: One requirement
- **WHEN** two ready changes modify the requirement "Character count command" of the capability `chars`
- **THEN** they do not work at the same time; first goes the one more open changes depend on, on a tie the first alphabetically

#### Scenario: The critical path first
- **WHEN** one slot is free, `a-docs` (nothing depends on it) and `b-core` (two open changes depend on it) are ready
- **THEN** `b-core` is launched

#### Scenario: Nothing to hand out
- **WHEN** there are no ready changes
- **THEN** the dispatcher launches nothing and lists the changes in the report with the reason: `CLAIM`, `WAITING`, an unarchived dependency, a hard conflict with a running one, or "not merged" with the branch and worktree

#### Scenario: A repeated launch after a conflict
- **WHEN** a branch `change/<id>` with a worktree remains from the last run, and the change in the main folder is not archived
- **THEN** the change is not launched again, the report names it "not merged" with the worktree path and the branch

#### Scenario: A shared documents directory
- **WHEN** "Working copy" has "Shared: `docs/`", and two ready changes name `docs/cli.md` in `Impact`
- **THEN** they are launched at the same time, the plan output has a `together:` line with `docs/cli.md`

#### Scenario: A document without "Shared"
- **WHEN** there is no "Shared", and two ready changes edit `skills/spec-dispatch/SKILL.md`
- **THEN** the second waits with the reason "conflict with …: file skills/spec-dispatch/SKILL.md"

#### Scenario: A shared path with a running one
- **WHEN** change `b` is issued while `a` is running, and both edit a file under the shared directory `apps/desktop/scenarios/`
- **THEN** `b` is launched, the line `together: b and a — <file>` is in the output

#### Scenario: The default limit
- **WHEN** "Working copy" has no "Orchestrators:" item, and three independent changes are ready
- **THEN** two are launched, the third waits with the reason "limit"

### Requirement: Orchestrator launch
For every change of a wave the dispatcher SHALL create a branch `change/<id>` and a worktree in a temporary folder (`git worktree add -b change/<id> <temporary folder>/wt-<id>` with `MAIN` as the working folder, the plain form the `guard` hook lets through) and launch one background `general-purpose` subagent with `model: opus` and the description `Orchestrator <id>`; all orchestrators of a wave launch in one message. The `isolation` parameter is not used.

#### Scenario: A wave of two changes
- **WHEN** the wave has `add-words` and `add-lines`
- **THEN** two worktrees are created in a temporary folder, and two orchestrators are launched in one message with the descriptions `Orchestrator add-words` and `Orchestrator add-lines`

#### Scenario: Subagent depth not set
- **WHEN** `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` is not set in the dispatcher's environment
- **THEN** no orchestrator is launched, no worktree is created, the report names the command `solo-sdd install --hooks` and a session restart

#### Scenario: Depth set below 2
- **WHEN** `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` equals `1`
- **THEN** no orchestrator is launched, the report names the value `1` and asks to raise it to 2; it does not suggest the command `solo-sdd install --hooks` as the solution

#### Scenario: Preparation failed
- **WHEN** the prepare command from the "Working copy" section created a file in the worktree and ended with an error
- **THEN** this change's orchestrator is not launched, the worktree and the branch `change/<id>` are removed by `discard`, the other changes launch, and on the next recalculation `sdd-dispatch-plan.py` issues this change in `launch:`, not in `waiting: not merged: branch`

### Requirement: Dispatcher context discipline
The dispatcher SHALL NOT read code, diffs and change artifacts, except the `Depends On` and `Impact` sections of `proposal.md` and the capability list in `specs/`; SHALL NOT run `cd` (only `git -C <path>` and subshells `(cd <path> && …)`); SHALL shorten command output (`-q`, `--oneline`, `| tail -3`) and SHALL NOT do the orchestrator's work.

#### Scenario: A check without reading code
- **WHEN** the dispatcher checks an orchestrator's status
- **THEN** it runs the check commands and compares exit codes and output, without opening code files and diffs

### Requirement: Status acceptance
For an `archived` status the dispatcher SHALL repeat in `WORKTREE` the commands from the `VALIDATE` and `LIVE` fields with the command `sdd-dispatch.py accept` (capability `dispatch-tool`) and act by its exit code. The dispatcher does not repeat the `TESTS` command at acceptance: in `pr` mode the PR's CI checks the test suite, in `local` mode the checks after merge in the main folder do (requirement Sequential merge and cleanup), each time already at the seam with the main branch.

#### Scenario: The status matches
- **WHEN** repeating `VALIDATE` and `LIVE` gives the same codes and output
- **THEN** the change goes to merge

#### Scenario: pr mode
- **WHEN** in `pr` mode an orchestrator handed back `archived` with `TESTS: npm test -> exit 0`
- **THEN** the dispatcher repeats only `VALIDATE` and `LIVE` in `WORKTREE`; the test suite goes to the PR's CI

#### Scenario: local mode
- **WHEN** in `local` mode an orchestrator handed back `archived` with `TESTS: npm test -> exit 0`
- **THEN** `npm test` is not run at acceptance; after merge the checks of the "Checks" section run once in the main folder

#### Scenario: No tests in "Checks"
- **WHEN** in `local` mode the "Checks" section does not run tests
- **THEN** after merge the test command from the "Commands" section runs once in the main folder

#### Scenario: Tests are added to the checks after merge
- **WHEN** no command of the "Checks" section runs tests
- **THEN** the dispatcher adds the test command from the "Commands" section to the checks after merge (`--check` of `land-local`)

#### Scenario: A mismatch at acceptance
- **WHEN** `accept` returned code 1
- **THEN** the dispatcher once returns to the orchestrator through SendMessage the list of mismatches from the command output

#### Scenario: A repeated mismatch
- **WHEN** after the return `accept` again returned code 1
- **THEN** the change counts as "not ready", its worktree and branch stay, the other changes continue

#### Scenario: Statuses not_ready and blocked
- **WHEN** an orchestrator handed back `not_ready` or `blocked`
- **THEN** the dispatcher does not recheck them and carries them into the report with the reason

### Requirement: Sequential merge and cleanup
Accepted changes SHALL be merged into the main branch one at a time. In `local` mode the dispatcher SHALL do it with the command `sdd-dispatch.py land-local` (capability `dispatch-tool`) with the commands of the `AGENTS.md` section "Checks" in `--check`: the script merges `change/<id>` with `--no-ff`, transfers the ignored artifacts (`Transport after merge`), runs the checks, rolls back and cleans up, and the dispatcher acts by the exit code and does not do these steps itself.

#### Scenario: A conflict on merge
- **WHEN** merging `change/b` gives a conflict after merging `change/a`
- **THEN** the merge of `change/b` is undone, orchestrator `b` got one message to update the branch and resolve the conflict; after its new status the merge is repeated

#### Scenario: A repeated conflict
- **WHEN** after the return merging `change/b` again gives a conflict in the same files
- **THEN** the main branch is in the state after `change/a`, worktree `b` is kept, the report says "not merged: conflict" with the files

#### Scenario: A red test after merge
- **WHEN** after merging `change/c` `npm test` fails, while on the main branch before the merge it passes
- **THEN** the merge is rolled back without repeated runs, orchestrator `c` got the command and the failure lines

#### Scenario: The main branch is red by itself
- **WHEN** the check that failed after merge also fails on the main branch before the merge
- **THEN** new changes are not launched, the owner is asked with the command and the failure lines

#### Scenario: A new conflict after main moved
- **WHEN** orchestrator `b` resolved a conflict in `AGENTS.md` and handed back the status, and meanwhile `change/a` was merged, and updating branch `b` gives a conflict in `README.md`
- **THEN** orchestrator `b` got a second return with the file `README.md`; a third conflict means "not merged: conflict"

### Requirement: Delivery and report
The dispatcher SHALL determine the delivery mode by the `AGENTS.md` section "Delivery", ask the owner once when it is missing and there is a remote, and record the answer in the section; in `local` mode it SHALL deliver the main branch by the `ship` skill, name the session model, and in messages and the report tell "in the local branch" from "on the remote".

#### Scenario: No remote
- **WHEN** the main folder has no remote and no "Delivery" section
- **THEN** the mode is `local`, delivery ends with the local main branch, the report says that push was not done because there is no remote

#### Scenario: A remote without the "Delivery" section
- **WHEN** there is a remote, but `AGENTS.md` has no "Delivery" section
- **THEN** the first orchestrators are launched, right after them the owner got one question about the mode; the mode applies from the first status acceptance

#### Scenario: The dispatcher on Opus
- **WHEN** the dispatcher session runs on Opus
- **THEN** the work is not interrupted, the first message and the report name the Opus model; there is no caveat "designed for Sonnet"

#### Scenario: The state in the middle of delivery
- **WHEN** 14 changes are accepted, and the remote main branch has 3
- **THEN** the message says "14 in the local branch, 3 on the remote", not "all 14 merged"

#### Scenario: The answer is recorded
- **WHEN** there is a remote, no "Delivery" section, `AGENTS.md` is ignored by git, the owner answered "pr, squash"
- **THEN** the main folder's `AGENTS.md` got a "Delivery" section with the mode `pr` and the method `squash`; the next run in the same folder does not ask

#### Scenario: AGENTS.md under git in local mode
- **WHEN** `AGENTS.md` is tracked by git and not changed, the owner answered "local"
- **THEN** before the first merge the local main branch got a separate commit with only `AGENTS.md`, the section holds `- Mode: local`

#### Scenario: AGENTS.md under git with others' edits
- **WHEN** `AGENTS.md` is tracked by git and holds uncommitted edits, the owner answered "local"
- **THEN** the file and the main branch are unchanged, the report under "Needs from you" holds the ready text of the "Delivery" section

#### Scenario: AGENTS.md under git in pr mode
- **WHEN** `AGENTS.md` is tracked by git, the owner answered "pr, squash"
- **THEN** the main branch is unchanged, the report under "Needs from you" holds the ready text of the "Delivery" section

#### Scenario: Determining the delivery mode
- **WHEN** the dispatcher prepares for a run
- **THEN** it determines by the "Delivery" section: `local` or `pr`, the PR merge method (`squash`, `merge`, `rebase`), the PR title rule and whether a merge into the main branch triggers a deploy; no section and the main folder has no remote means mode `local`

#### Scenario: The mode question
- **WHEN** there is no "Delivery" section, there is a remote
- **THEN** one question to the owner per run (requirement Owner questions) with the options `pr, squash`, `pr, merge`, `pr, rebase` and `local`, right after launching the first orchestrators (their worktrees come from the local main branch; in `pr` mode the branch is updated from the remote at acceptance anyway); the mode applies from the first status acceptance

#### Scenario: Recording the owner's answer
- **WHEN** the owner answered the mode question
- **THEN** the dispatcher at once records the "Delivery" section in the main folder's `AGENTS.md` with the lines of the `project-init` template (`- Mode: pr`, `- Merge: squash`, for `local` only `- Mode: local`; other items are not invented), so the next run does not ask; if `AGENTS.md` is ignored by git or untracked, by writing the file; if it is tracked and the mode is `local`, by a separate commit into the local main branch before the first merge; in `pr` mode or with uncommitted edits in the file, by the ready section text in "Needs from you" of the report (the dispatcher does not commit into a protected main branch or over others' edits)

#### Scenario: Delivery and deploy
- **WHEN** the last merge in `local` mode is done, or a merge into the main branch or a push triggers a prod deploy
- **THEN** in `local` mode after the last merge the main branch is delivered by the `ship` skill; in `pr` mode delivery goes per change (requirement PR per change); before the first action that triggers a deploy the dispatcher asks the owner, naming what rolls out and where

#### Scenario: The dispatcher model
- **WHEN** the dispatcher sends the first message
- **THEN** it names the session model; the dispatcher runs on the main model, its work is mechanical, so the skill advises starting it with `/effort low`

#### Scenario: Report content
- **WHEN** the dispatcher sends a status message or the final report
- **THEN** they tell "in the local branch" from "on the remote" (the number of changes in each); the final report holds a table by change (status, status check, merge or PR with a link, agents, hooks, acceptance), the dispatcher model, `git log --oneline --graph` of the last commits, `git worktree list`, `git status --short` of the main folder and the open PRs of the run

### Requirement: Transport after merge
After merging a change into the main branch and before the checks the dispatcher SHALL run `sdd-worktree.py transport <MAIN> <WORKTREE>`. The dispatcher SHALL handle code 3 as a merge conflict: roll back the merge (`git reset --keep` to the commit before the merge) and follow the conflict rules. Any rollback of a merge after a successful transfer (for example, when the checks fail) SHALL include `sdd-worktree.py undo <MAIN> <WORKTREE>`.

#### Scenario: A transfer without a conflict
- **WHEN** the change is merged, and `transport` ended with code 0
- **THEN** the checks after merge already run with the change's archive and specs in the main folder

#### Scenario: A rollback after a transfer
- **WHEN** the transfer passed, and a check after merge failed
- **THEN** the dispatcher ran `git reset --keep` and `sdd-worktree.py undo`; the main folder has no archive of the change

#### Scenario: A transfer conflict
- **WHEN** `transport` returned code 3
- **THEN** the merge is rolled back, the main folder is in the state before the merge, the change is handled as a merge conflict

#### Scenario: Diffs of ignored files
- **WHEN** the transfer touched ignored files
- **THEN** the dispatcher does not read their diffs

### Requirement: Owner questions
A decision needed from the owner during the dispatcher's work SHALL be asked at once in a question window (`AskUserQuestion`) with options and the recommended one first, not in the report text; the launched orchestrators meanwhile keep working in the background, and the dispatcher handles their statuses, merges and new launches after the answer: the question window holds the dispatcher's turn.

#### Scenario: A change waits for a decision
- **WHEN** an orchestrator handed back `not_ready`, and continuing is possible only by the owner's decision
- **THEN** the owner got a question window at the same moment, and the dispatcher continues the other changes

#### Scenario: A proposal to parallelise
- **WHEN** the plan holds `add-lines` because of `docs/architecture.md`, shared with the running `add-words`, and the dispatcher thinks they can run in parallel
- **THEN** the owner at once gets a question window with the options "Treat docs/architecture.md as shared until the end of the run" and "One at a time", not the line "tell me if needed"; after the first answer the plan is recomputed with `--shared docs/architecture.md` and issues `add-lines`

#### Scenario: The question window holds the dispatcher's turn
- **WHEN** a question window is open, and orchestrators are working
- **THEN** the launched orchestrators keep working in the background, and the dispatcher handles their statuses, merges and new launches after the answer

#### Scenario: The question window is unavailable
- **WHEN** the dispatcher works in a `claude -p` session, where there is no question window, and needs the owner's decision
- **THEN** the question is the first line of the message marked "Needs from you", and the dispatcher continues the other changes without waiting for the answer

### Requirement: PR per change
In `pr` mode the dispatcher SHALL create worktrees of new changes from the remote main branch after `git fetch`, run `sdd-pr.py ship` right after a status is accepted, `sdd-pr.py land` after `green`, merge PRs one at a time in acceptance order and react to the codes of these commands, without assembling the steps into command chains itself. `sdd-pr.py` SHALL print one summary line per call and at most 20 lines of explanation or failure.

#### Scenario: A worktree from the remote main
- **WHEN** the dispatcher creates the worktree of a new change
- **THEN** it is created from the remote main branch after `git fetch`

#### Scenario: Running ship
- **WHEN** a change's status is accepted
- **THEN** the dispatcher runs as a background command `sdd-pr.py ship <MAIN> <WORKTREE> <main> <title>` with the title by the rule from "Delivery": it updates the branch from the remote main, runs `refresh`, pushes the branch, opens the PR and waits for CI; the other changes go on

#### Scenario: ship codes at the dispatcher
- **WHEN** `ship` returned code 6 or 1
- **THEN** code 6 (conflict) is handled as a merge conflict by the requirement Sequential merge and cleanup, code 1 as "not merged: PR" with the reason

#### Scenario: Running land after green
- **WHEN** the PR's CI gave `green`
- **THEN** the dispatcher runs `sdd-pr.py land <MAIN> <WORKTREE> <url> <method>` with the method from "Delivery": a merge with the hash of the checked head, `merge --ff-only` of the main folder, a transfer of the ignored artifacts (`Transport after merge`) and cleanup

#### Scenario: Checks after merge
- **WHEN** a PR is merged in `pr` mode
- **THEN** the checks are the status acceptance in `WORKTREE` and the PR's CI on the branch updated from the remote main; they are not repeated locally, because the dispatcher cannot roll back a merged PR

#### Scenario: Merge order and land codes
- **WHEN** several PRs are ready for merge
- **THEN** they are merged one at a time in acceptance order; `land` with code 5 (main moved ahead) means `ship` in the background again and `land` after a new `green`; code 1 means "not merged: merge" with the reason; code 7 means the change counts as merged, `land` is repeated once, a repeated code 7 means cleanup with the step and the reason in "Needs from you"

#### Scenario: A return on red CI
- **WHEN** the PR's CI is red
- **THEN** the dispatcher once returns the change to the orchestrator with the failure lines from the `ship` output; a repeated failure means "not merged: CI" with the PR link

#### Scenario: A CI rerun
- **WHEN** the PR's CI is red
- **THEN** a rerun without edits is allowed once and only if the log has no failed tests (a runner or network failure); a required check that did not start is restarted by an empty commit in the change branch (requirement Required checks in CI wait), not by `gh run rerun`; after the rerun the dispatcher waits for the result with the background command `sdd-pr.py wait <url>`

#### Scenario: The sdd-pr.py summary line
- **WHEN** `sdd-pr.py` finished a call
- **THEN** one summary line is printed (the PR number and link, the CI result `green`, `red`, `infra` or `codeql`, the merge result) and at most 20 lines of explanation or failure

#### Scenario: The meaning of the red and infra results
- **WHEN** a PR check failed, was cancelled or timed out, or the checks did not start within the allotted time
- **THEN** `red`: the log of the failed step has a sign of a failed test (`FAIL:`, `ERROR:`, `FAILED`, `AssertionError`, `failed`); `infra`: there are no such signs, or the checks did not start within the allotted time

#### Scenario: A merge with a foreign hash
- **WHEN** `merge` is called with a hash that did not match the PR head
- **THEN** the PR is not merged, the call ends with an error

#### Scenario: A return on the codeql result
- **WHEN** the `codeql` result (code 8) is got for the first time
- **THEN** the dispatcher once returns the change to the orchestrator with the alert lines from the `ship` or `wait` output; after a new status, `ship` again

#### Scenario: A repeated codeql without a CI rerun
- **WHEN** the `codeql` result repeated after the return
- **THEN** "not merged: CodeQL" with the PR link, without a CI rerun

#### Scenario: CI runs in parallel
- **WHEN** the status of `add-words` is accepted, and `add-lines` is still working
- **THEN** the PR of `add-words` is open, its CI runs while the `add-lines` orchestrator works

#### Scenario: Red CI
- **WHEN** the CI of the `add-lines` PR failed on the test `test_lines`
- **THEN** the `add-lines` orchestrator got one message with the failure lines; after a new status `ship` updated the PR and CI is awaited again

#### Scenario: The local branch matches the remote
- **WHEN** all PRs of the run are merged
- **THEN** `git -C <MAIN> rev-parse <main>` equals `origin/<main>`, there are no local merge commits on top of the remote

#### Scenario: A push failure is not lost
- **WHEN** `ship` for `add-words` ended with code 1 at the push step
- **THEN** the dispatcher sees the step and the reason in the summary line, the change in the report is "not merged: PR" with the reason, not "CI: infra"

#### Scenario: The PR is merged, the cleanup failed
- **WHEN** `land` for `add-words` returned code 7 at the `transport` step, and the repeated `land` too
- **THEN** the report has `add-words` merged (counted on the remote), and "Needs from you" has the `transport` step and its reason

#### Scenario: A CodeQL alert
- **WHEN** `ship` for `add-words` returned code 8 with the line `#28 js/bad-code-sanitization src/check.ts:102`
- **THEN** the `add-words` orchestrator got one message with this line, `land` was not called; after a new status `ship` ran again

#### Scenario: A repeated CodeQL alert
- **WHEN** after the return on code 8 the `add-words` orchestrator handed back a new status, and `ship` again returned code 8
- **THEN** `add-words` in the report is "not merged: CodeQL" with the PR link, CI was not rerun, there is no second return

### Requirement: Uncommitted change artifacts
If `solo-sdd/changes` in the main folder is not ignored by git, `sdd-dispatch-plan.py` SHALL NOT issue a change whose folder has untracked or uncommitted files, and SHALL print it in `waiting:` with the reason `not committed`: a worktree from a commit will not see it. The reasons `CLAIM`, `WAITING` and `not merged` SHALL take precedence: the `CLAIM` file itself lies in the folder uncommitted.

#### Scenario: The change is not committed
- **WHEN** `solo-sdd/changes/a/` is not tracked by git, and `solo-sdd/` is not ignored
- **THEN** `a` is in the `waiting:` line with the reason "not committed", the orchestrator is not launched

#### Scenario: The change is changed after the commit
- **WHEN** `tasks.md` of the committed change `a` is changed and not committed
- **THEN** `a` is in the `waiting:` line with the reason "not committed"

#### Scenario: A taken change
- **WHEN** folder `a` is not committed and holds a `CLAIM`
- **THEN** `a` is in the `waiting:` line with the reason `CLAIM`

#### Scenario: Specs are ignored
- **WHEN** `solo-sdd/` is ignored by git in the project
- **THEN** changes are issued as before, the report holds the line "Artifacts outside git: solo-sdd/"

#### Scenario: Only the rules are ignored
- **WHEN** `AGENTS.md` is ignored, `solo-sdd/` is not, folder `a` is not committed
- **THEN** `a` waits with the reason "not committed", the report holds the line "Artifacts outside git: AGENTS.md"

#### Scenario: Why an uncommitted change is not issued
- **WHEN** a change has uncommitted files
- **THEN** a worktree from a commit will not see it, so the change waits; `CLAIM` is more important, because the `CLAIM` file itself lies in the folder uncommitted

### Requirement: Leftovers in report
The dispatcher SHALL carry the "Leftovers:" line from `NOTES` of an orchestrator status of any kind (`archived`, `not_ready`, `blocked`) into the "Needs from you" section of the final report with the change name. The orchestrator prompt SHALL allow the "Leftovers:" line above the `NOTES` line limit.

#### Scenario: A stand folder remained
- **WHEN** orchestrator `chars-bytes` handed back `archived` with the line "Leftovers: /var/folders/…/chars-stand-1a2b"
- **THEN** "Needs from you" of the final report has a line with `chars-bytes` and this path

#### Scenario: No leftovers
- **WHEN** no status of the run holds a "Leftovers:" line
- **THEN** "Needs from you" has no lines about leftovers

### Requirement: Abandoned claims
`sdd-dispatch-plan.py` SHALL mark a `CLAIM` abandoned if there is no branch `change/<id>` and either the marker holds `session=<id>` and this session's files `~/.claude/hook-state/<id>.json` and `<id>.claims` have not changed for 60 minutes or longer or do not exist, or the marker has no session id and the `CLAIM` file is 12 hours old or older. The script does not remove the marker.

#### Scenario: Markers of a silent session
- **WHEN** eight changes hold a `CLAIM` with `session=157c88ff…`, this session's files in `hook-state` have not changed for 7 hours, there are no `change/*` branches
- **THEN** all eight have the reason "CLAIM abandoned: session 157c88ff silent 7 h", the owner gets one question, after "Remove and launch" the plan issues the changes for launch

#### Scenario: A live session
- **WHEN** a `CLAIM` with `session=<id>`, and this session's files changed 5 minutes ago
- **THEN** the reason stays `CLAIM`, no question

#### Scenario: A marker without a session id
- **WHEN** a `CLAIM` with the line `codex 2026-10-21` without `session=`, the file is 13 hours old, no branch
- **THEN** the reason is "CLAIM abandoned: label 13 h"; for a file 11 hours old the reason is `CLAIM`

#### Scenario: No session traces
- **WHEN** a `CLAIM` with `session=<id>` was placed 3 hours ago, this session has no files in `hook-state`
- **THEN** the reason is "CLAIM abandoned: session <first 8 chars of id> silent 3 h"

#### Scenario: The owner declines
- **WHEN** the owner answered "Keep" to the question about abandoned markers
- **THEN** the markers stay, the changes are in "waiting" until the end of the run, on the next recalculations the question is not repeated

#### Scenario: A marker with a branch
- **WHEN** the session is silent for 3 hours, but the branch `change/<id>` exists
- **THEN** the marker is not abandoned: the reason is "not merged: branch", the owner sorts it out

#### Scenario: The marker or the time cannot be read
- **WHEN** the marker or the file time could not be read, and it is not the absence of the session's files
- **THEN** the marker is not abandoned: the reason stays `CLAIM`

### Requirement: Unknown dependency
`sdd-dispatch-plan.py` SHALL print, for a change whose name from `Depends On` matches neither an open change nor an archived one, the reason "unknown dependency: <name>", and if `solo-sdd/specs/` has a folder with this name, "unknown dependency: <name> (a spec, not a change)". The reason "depends on" stays only for open changes. The script SHALL accept `--ignore-dep <id>:<name>` (repeatable) and not count this name as a dependency of this change.

#### Scenario: A spec in Depends On
- **WHEN** change `fix-pin` has `` `cli-participants` `` in `Depends On`, there is no such change, open or archived, and the folder `solo-sdd/specs/cli-participants/` exists
- **THEN** the plan prints "fix-pin — unknown dependency: cli-participants (a spec, not a change)"; with `--ignore-dep fix-pin:cli-participants` `fix-pin` is issued for launch

#### Scenario: A real dependency
- **WHEN** `add-top-words` depends on the open change `add-words`
- **THEN** the reason is "depends on add-words"

#### Scenario: A typo in the name
- **WHEN** `Depends On` has `add-wrods`, and there is no such change or spec
- **THEN** the reason is "unknown dependency: add-wrods"

#### Scenario: The old Russian word for none
- **WHEN** `Depends On` of change `265-fix-xlsx` holds the old Russian value meaning "none" (the three letters U+043D U+0435 U+0442)
- **THEN** it is a name, not an empty value: the reason "unknown dependency: " with that word and a question to the owner, not a silent launch

#### Scenario: "none" with a note
- **WHEN** `Depends On` holds "None, all independent"
- **THEN** there are no dependencies: the word "all" does not count as a name

#### Scenario: Open and unknown together
- **WHEN** a change depends on the open `add-words` and on `add-wrods`, which does not exist
- **THEN** the reason is "unknown dependency: add-wrods; depends on add-words"; with `--ignore-dep` "depends on add-words" remains

### Requirement: Unknown dependency question
On the first plan where a change got the reason "unknown dependency", the dispatcher SHALL ask the owner in one window about all such changes of this plan, together with the other questions of this plan: all spec names in one question with "Ignore" first and recommended, all other names in one question with "Keep" first and recommended; one kind of names, one question. After "Keep" the changes wait until the end of the run without a repeated question.

#### Scenario: The answer "Ignore"
- **WHEN** the owner answered "Ignore" to the question about `fix-pin` and `cli-participants`
- **THEN** the plan is recomputed with `--ignore-dep fix-pin:cli-participants`, the `fix-pin` orchestrator is launched with the line "Remove from Depends On: cli-participants", `MAIN/solo-sdd/changes/fix-pin/proposal.md` is not changed

#### Scenario: A typo
- **WHEN** the unknown name is `add-wrods`, there is no spec with this name
- **THEN** the option "Keep" goes first and recommended

#### Scenario: A spec and a typo in one plan
- **WHEN** the plan has `fix-pin` with a spec name and `chars-bytes` with `add-wrods`
- **THEN** one window with two questions: about the spec with "Ignore" first, about the typo with "Keep" first

#### Scenario: "Ignore" until the end of the run
- **WHEN** the owner answered "Ignore"
- **THEN** until the end of the run the dispatcher passes `--ignore-dep` to the script, and the line "Remove from Depends On: <names>" into this change's orchestrator prompt; it does not edit the main folder's files

#### Scenario: Without a question window
- **WHEN** there is no question window (a `claude -p` session)
- **THEN** the question goes as a "Needs from you" line by the requirement Owner questions, and until the answer "Keep" applies

### Requirement: Waiting changes and the limit
`sdd-dispatch-plan.py` SHALL accept `--waiting <id,…>`: changes waiting for merge (status accepted, branch on CI); in the conflict check they count as running, in the limit only above it. The first output line is "limit: N, running: K, waiting for merge: W". In `pr` mode the dispatcher SHALL move a change from `--running` to `--waiting` once the status is accepted and `ship` is started; in `local` mode the change stays in `--running` until merge.

#### Scenario: Parsing the lists
- **WHEN** `--running` and `--waiting` hold the same id or an id not from open changes
- **THEN** an id in both lists counts as running, an id not from open changes is dropped, and every waiting one above the limit takes one slot

#### Scenario: Waiting ones do not hold slots
- **WHEN** the limit is 3, one orchestrator is running, two changes wait for the CI of their PRs, three more changes without conflicts are ready
- **THEN** the plan issues two changes for launch, the first line is "limit: 3, running: 1, waiting for merge: 2"

#### Scenario: A conflict with a waiting one
- **WHEN** change `b` edits the same file as change `a` waiting for merge
- **THEN** `b` waits with the reason "conflict with a", although slots are free

#### Scenario: More waiting ones than the limit
- **WHEN** the limit is 3, none are running, five changes wait for merge
- **THEN** the two waiting ones above the limit take two slots, one change is issued for launch

#### Scenario: local mode
- **WHEN** the delivery mode is `local`, a change's status is accepted and it waits for merge
- **THEN** the dispatcher passes it in `--running`, it takes a slot

### Requirement: Refresh command failure
If on a branch update `sdd-worktree.py refresh` ended with code 4 (the "After refresh:" command failed), also inside `sdd-pr.py ship`, the dispatcher SHALL once return the change to the orchestrator with the command and its output lines; the orchestrator fixes the build in `WORKTREE` on the updated branch and hands back the status again. A repeated code 4 means "not merged: PR" with these lines in the report. Code 4 during a return for a conflict SHALL count as this return.

#### Scenario: The build after update failed
- **WHEN** `ship` for `add-ocr` stopped at the `refresh` step, and it returned code 4 with the lines `npm run build:ocr` and "swiftc: error"
- **THEN** the `add-ocr` orchestrator got one message with the command and these lines; after a new status `ship` ran again

#### Scenario: A repeated failure
- **WHEN** after the return `refresh` again returned code 4
- **THEN** the change in the report is "not merged: PR" with the command and the output lines, there is no second return

#### Scenario: The build failed during a return for a conflict
- **WHEN** during a return for a conflict the `add-ocr` orchestrator itself ran `refresh`, it returned code 4, and after the fix code 4 again
- **THEN** the orchestrator handed back `STATUS: not_ready` with the command and the code in `NOTES`; the change in the report is "not merged: PR" with the command and the output lines, there is no separate return from the dispatcher

### Requirement: Dispatch pipeline and order
Launches SHALL go as a pipeline: while fewer orchestrators run than the limit (default 2, another value is the item "Orchestrators: <number>" of the `AGENTS.md` section "Working copy"), the dispatcher launches the next ready change that has no hard conflict with any running one. The order SHALL be: first the change that more open changes depend on directly or through a chain, on a tie by id alphabetically.

#### Scenario: The limit from the working copy
- **WHEN** "Working copy" has "Orchestrators: 3", and four independent changes are ready
- **THEN** three are launched, the fourth waits with the reason "limit" and launches as soon as one of the three frees a slot

#### Scenario: A dependency through a chain
- **WHEN** `b` depends directly on `a`, `c` depends on `b`, and one open change depends on the ready `d`
- **THEN** with one free slot `a` is launched first

### Requirement: Hard conflicts between changes
Only the following SHALL count as a hard conflict of two changes: their deltas have a requirement with the same name in the same capability (in any of the sections ADDED, MODIFIED, REMOVED, RENAMED) or their `Impact` sections name the same file (requirement Impact file paths). A shared capability with different requirements, a shared directory and shared paths do not hinder parallel work: such changes launch together.

#### Scenario: One requirement in RENAMED and MODIFIED
- **WHEN** one change renames requirement `X` of the capability `cli` in the RENAMED section, and another modifies `X` in the MODIFIED section
- **THEN** they have a hard conflict, they do not work at the same time

### Requirement: Impact file paths
A file in the `Impact` section SHALL be a value in backquotes that has `/` or an extension and no spaces and `*` signs, except directories (ends in `/` or exists in the main folder as a directory) and shared paths: `AGENTS.md`, `CLAUDE.md`, `docs/waiting.md`, `CHANGELOG.md` and the backquoted paths from the item "Shared:" of the `AGENTS.md` section "Working copy". A path from "Shared" ending in `/` makes all files under it shared.

#### Scenario: Not files
- **WHEN** the `Impact` of two changes names `skills/*.md`, `textkit/` or `README and tests`
- **THEN** these are not files, there is no conflict on them

#### Scenario: A shared file without a directory
- **WHEN** both changes name `CHANGELOG.md` in `Impact`
- **THEN** it is a shared path, there is no conflict

### Requirement: Shared path pairs
If an issued change and an issued or running one name one shared path in `Impact`, `sdd-dispatch-plan.py` SHALL print this pair as one line `together: <id> and <id> — <path>`, several paths separated by commas. The dispatcher carries these pairs into the report; a conflict, if it happens on merge, is resolved by a return to the orchestrator (requirement Sequential merge and cleanup).

#### Scenario: Two shared paths
- **WHEN** the issued `a` and `b` both name `AGENTS.md` and `CHANGELOG.md` in `Impact`
- **THEN** the output has one line `together: a and b — AGENTS.md, CHANGELOG.md`, and the report has the same

### Requirement: Orchestrator prompt
The orchestrator prompt SHALL hold the change name, the absolute paths `MAIN` and `WORKTREE`, the branch, the instruction to run the change by `spec-next` in the "Under the dispatcher" mode and the status format of the capability `orchestrator-status`.

#### Scenario: The orchestrator prompt
- **WHEN** the dispatcher launches the `add-words` orchestrator
- **THEN** the prompt names `add-words`, the absolute `MAIN` and `WORKTREE`, the branch `change/add-words`, the "Under the dispatcher" mode and the status format

### Requirement: Worktree setup before launch
Right after `git worktree add` the dispatcher SHALL run `python3 ~/.local/bin/sdd-worktree.py setup <MAIN> <WORKTREE>` (capability `worktree-env`); on a non-zero code no orchestrator is launched, the dispatcher SHALL run `sdd-worktree.py discard <MAIN> <WORKTREE>` (removes the worktree with the prepare files and the branch), and the report says "not launched: worktree preparation" with the last error lines; if `discard` refused, also its reason, and the worktree and branch stay.

#### Scenario: discard refused
- **WHEN** `setup` ended with code 1, and `discard` refused too
- **THEN** the report names "not launched: worktree preparation" with the last error lines and the reason `discard` refused, the worktree and branch stay

### Requirement: Subagent depth before launch
Before the first wave the dispatcher SHALL check that `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` in its environment is at least 2 (otherwise an orchestrator cannot launch executors and the reviewer); if it is lower or not set, the orchestrators are not launched. If the variable is not set, the report names one owner action for the whole computer: `solo-sdd install --hooks` and a session restart.

#### Scenario: Depth 2
- **WHEN** `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` equals `2`
- **THEN** the orchestrators of the first wave are launched

#### Scenario: Why depth 2
- **WHEN** the depth is below 2
- **THEN** an orchestrator cannot launch executors and the reviewer, so the orchestrators are not launched

#### Scenario: Depth below 2 in the report
- **WHEN** `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` is set below 2
- **THEN** the report names the current value and that it must be raised to 2 where the owner set it: the command `solo-sdd install --hooks` does not change a set value

### Requirement: Merge conflict return
On a merge or transfer conflict (code 6) the dispatcher SHALL once return the change to its orchestrator through SendMessage: update the branch from main (`git -C <WORKTREE> merge <main branch>` and `sdd-worktree.py refresh <MAIN> <WORKTREE>`), resolve the conflict in `WORKTREE`, repeat the checks, hand back the status. A conflict in the same files as at the last return, or the third conflict, means "not merged: conflict" with the files; the worktree and branch stay.

#### Scenario: A conflict in other files
- **WHEN** after the return a conflict arose in other files, because the main branch moved ahead (usual in `pr` mode: while CI runs, neighbours get merged)
- **THEN** it is one more return, not "not merged"

### Requirement: Red check after merge
On a failed check after merge (requirement Local land after a red check of `dispatch-tool`) the dispatcher SHALL act by the code: code 3, the failure belongs to the change or its seam with merged ones: one return to the orchestrator with the command, the failure lines and the same branch update as on a conflict; code 4, the main branch is red: no new launches or merges, the owner is asked (requirement Owner questions) with the command and the failure lines.

#### Scenario: A repeated failure after the return
- **WHEN** after the return on code 3 the check after merge fails again
- **THEN** the change is "not merged: checks"

#### Scenario: Flakiness only with code 4
- **WHEN** a check after merge failed
- **THEN** the failure counts as flakiness only with code 4; with code 3 the branch is updated from main, otherwise the seam cannot be reproduced in `WORKTREE`

### Requirement: Land-local result codes
For the other `land-local` codes the dispatcher SHALL write into the report: code 2 means "not merged: main folder not clean" with the files; code 1 means a step failure: before and during the checks, "not merged: <step>", on a cleanup failure after passed checks, "merged, not cleaned: <step>", with the script's line. The dispatcher SHALL carry the line `not transported: <files>` from the `land-local` output into the report with any code.

#### Scenario: The cleanup failed
- **WHEN** the checks passed, and `sdd-worktree.py remove` failed
- **THEN** the report has "merged, not cleaned: remove" and the script's line

### Requirement: Run change proposals
A proposal to change the course of the run that the dispatcher cannot accept itself (running in parallel changes held by a shared file, taking new changes, stopping the run) SHALL be asked in a question window (requirement Owner questions) when the dispatcher formulates it, not as a line in a status message. For a shared file the options are "Treat <path> as shared until the end of the run" (`--shared <path>`, the plan is recomputed) and "One at a time".

#### Scenario: The answer "One at a time"
- **WHEN** the owner answered "One at a time" to the question about a shared file
- **THEN** the plan does not change, the second change waits for the merge of the first

#### Scenario: Nothing against the plan
- **WHEN** the dispatcher thinks a change the plan holds can be launched
- **THEN** it launches nothing against the script's plan, and asks a question instead

### Requirement: Abandoned claim reason
The waiting reason for an abandoned marker SHALL be "CLAIM abandoned: session <first 8 chars of id> silent <N> h" (without an id, "CLAIM abandoned: label <N> h"); N is whole hours, fraction dropped, since the last edit of the session's files, or if there are none, since the `CLAIM` file time. A branch `change/<id>` wins over the marker: the reason is then "not merged: branch…", with or without `CLAIM` or `WAITING`; a marker and `WAITING` without a branch give the marker reason.

#### Scenario: Fractional hours
- **WHEN** the session's files are silent for 7 hours 50 minutes
- **THEN** the reason is "… silent 7 h"

#### Scenario: A marker and WAITING without a branch
- **WHEN** the change folder has an abandoned `CLAIM` and `WAITING`, there is no branch `change/<id>`
- **THEN** the reason is by the marker: "CLAIM abandoned: …"

### Requirement: Abandoned claims question
The dispatcher SHALL ask the owner one question about all abandoned markers of the first plan that has them, and after consent remove only those still abandoned on the recalculation; on refusal the changes stay in "waiting" until the end of the run, with no repeated question. Markers abandoned after the question stay in "waiting" without a question. Without a question window (`claude -p`) the question is a "Needs from you" line and the markers stay: this equals a refusal.

#### Scenario: A marker came alive before the answer
- **WHEN** the owner agreed to remove the markers, and on the recalculation one of them is no longer abandoned
- **THEN** only the markers still abandoned on the recalculation are removed

#### Scenario: A claude -p session
- **WHEN** the dispatcher works in a `claude -p` session, and the plan has abandoned markers
- **THEN** a "Needs from you" line, the markers are not removed, the changes are in "waiting"

### Requirement: Open and unknown dependencies
If a change has both an open and an unknown dependency, the reason SHALL name both: first the unknown ones, then "depends on <open ones>", so the question to the owner is not postponed until the open one is merged. Several unknown names are listed separated by commas, the mark "(a spec, not a change)" stands at every such name.

#### Scenario: Two unknown ones, one of them a spec
- **WHEN** a change depends on `add-wrods` and on the spec `cli-participants`, neither is among the changes
- **THEN** the reason is "unknown dependency: add-wrods, cli-participants (a spec, not a change)"

### Requirement: No dependency values
The values `none`, `-` and `—` in any case, including with a full stop, a comma or a colon after them, SHALL mean "no dependencies"; such a value first in a `Depends On` item removes the whole item, together with the note after it.

#### Scenario: None with a full stop
- **WHEN** `Depends On` holds "None."
- **THEN** there are no dependencies

#### Scenario: A dash with a note
- **WHEN** `Depends On` holds "—: an independent change"
- **THEN** there are no dependencies: the note does not count as a name

### Requirement: Artifacts outside git
If at least one of the paths `solo-sdd/`, `AGENTS.md`, `CLAUDE.md` is ignored, `sdd-dispatch-plan.py` SHALL print the line "Artifacts outside git: <paths>", and the dispatcher SHALL carry it into the report and continue the work.

#### Scenario: CLAUDE.md is ignored
- **WHEN** git ignores `CLAUDE.md`, and does not ignore `solo-sdd/` and `AGENTS.md`
- **THEN** the plan prints the line "Artifacts outside git: CLAUDE.md", the dispatcher carries it into the report and continues the work

### Requirement: Merged worktree removal
When cleaning up a merged change the dispatcher SHALL call `sdd-worktree.py remove` instead of `git worktree remove`.

#### Scenario: Cleaning up a merged change
- **WHEN** the dispatcher removes the worktree of a merged change
- **THEN** it calls `sdd-worktree.py remove` and does not call `git worktree remove`

### Requirement: Owner-only paths
The dispatcher SHALL treat code 8 from `sdd-pr.py merge`, `sdd-pr.py land` or `sdd-dispatch.py land-local` as the change result "waits for the owner: <paths>": not repeat it, not bypass it, carry it into the report table and into "Needs from you" (`pr` mode: review and merge the PR with the link; `local` mode: review and merge the branch `change/<id>`) and continue the other changes. Changes that depend on it wait for its archive in the main branch, as with any unmerged change.

#### Scenario: A PR waits for the owner
- **WHEN** in `pr` mode `land` returned code 8 for change `ci-cache`
- **THEN** the `ci-cache` PR is open, the report names it in "Needs from you" with the link, the other changes are merged

### Requirement: Loopback before launch
Before the first wave the dispatcher SHALL read the loopback line of `sdd-dispatch-plan.py` (a listen on a free `127.0.0.1` port, a connect with a timeout of at most 2 s). A blocked loopback SHALL stop the run (no orchestrator, no worktree) only when the project's `AGENTS.md` has `- Loopback: needed` in `## Commands` or `## Working copy`; otherwise launches go on. A blocked loopback SHALL put the fix in "Needs from you": `sandbox.network.allowLocalBinding: true` or a session without the sandbox.

#### Scenario: Loopback works
- **WHEN** the session can listen and connect on `127.0.0.1`
- **THEN** the second line of the plan is `loopback: ok`, the launch goes on

#### Scenario: Loopback blocked, needed by the project
- **WHEN** the session's sandbox denies the connect, and the project's `AGENTS.md` has `- Loopback: needed`
- **THEN** the line `loopback: blocked (needed by the project):` with the error, no orchestrator launched, no worktree, the fix in "Needs from you"

#### Scenario: Loopback blocked, not needed
- **WHEN** the session's sandbox denies the connect, and the project's `AGENTS.md` has no `Loopback: needed` item
- **THEN** the line `loopback: blocked:` with the error, the launch goes on, "Needs from you" carries the line as a warning with the fix

### Requirement: Promotion line in the report
After a merge into `delivery.base`, the dispatcher's and `ship`'s report SHALL name the next branch of `delivery.promote` and the `sdd-pr.py promote` command for it, and SHALL NOT run it.

#### Scenario: A line with promotion
- **WHEN** `delivery.base: dev`, `delivery.promote: staging, release/*, main` and a change merged into `dev`
- **THEN** the report has the line `promotion: dev → staging: sdd-pr.py promote dev staging`

### Requirement: Waiting for a human merge
With `delivery.merge-by: human` the dispatcher SHALL stop each accepted change at a green PR, report it as `waits for human merge` with the URL, not count it as failed, and go on with the next change. In `local` delivery `land-local` SHALL exit 8 with `waits for human merge` and keep the branch and worktree. For such changes this SHALL take precedence over Sequential merge and cleanup.

#### Scenario: Two changes
- **WHEN** two changes are accepted with green CI under `merge-by: human`
- **THEN** the report lists both as `waits for human merge` with their URLs, and nothing is merged

#### Scenario: Local delivery
- **WHEN** `delivery.mode: local`, `merge-by: human` and `land-local` runs on an accepted change
- **THEN** code 8, `waits for human merge`, the main branch, the branch and the worktree are unchanged
