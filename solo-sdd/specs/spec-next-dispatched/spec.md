# spec-next-dispatched Specification

## Purpose
How `spec-next` runs a change when the dispatcher launched it: work in the given worktree, no delivery, the choice "itself or through executors", and a status handback instead of a report.

## Requirements

### Requirement: Dispatched mode differences
When the orchestrator prompt names the mode "Under the dispatcher" and passes `MAIN`, `WORKTREE` and the branch, `spec-next` SHALL run with these differences: no step 0; `CLAIM` goes into `MAIN/solo-sdd/changes/<id>/`; all code, artifacts and commits go in `WORKTREE`; executors and the reviewer get the absolute `WORKTREE` path and a ban on writing outside it; no merge into the main branch and no `/ship`; after the branch commit `CLAIM` is deleted from `MAIN`; the next change is not started.

#### Scenario: The orchestrator finished the change
- **WHEN** all tasks are done, the Live Scenario passed and the change is archived in `WORKTREE`
- **THEN** the changes are committed in the `WORKTREE` branch, `CLAIM` in `MAIN` is deleted, the main branch is unchanged

#### Scenario: A line in an ignored AGENTS.md
- **WHEN** a change adds the line of its stand to `AGENTS.md`, which git ignores
- **THEN** the line is added to `WORKTREE/AGENTS.md`; `MAIN/AGENTS.md` is unchanged until the dispatcher's transfer

### Requirement: Status instead of report
In the "Under the dispatcher" mode the orchestrator's last message SHALL be only a status block in the format of the capability `orchestrator-status`, without the `spec-next` report. If the change did not reach the archive, the status is `not_ready` or `blocked` with the reason in `NOTES`.

#### Scenario: The Live Scenario failed
- **WHEN** the live scenario did not pass and the Fallback did not help
- **THEN** the change is not archived, the orchestrator hands back `STATUS: not_ready` with what failed in `NOTES`

### Requirement: Foreground team
In the "Under the dispatcher" mode the orchestrator SHALL launch executors and the reviewer as foreground subagents (several independent ones in one message) and SHALL NOT end its turn while at least one of its subagents or a background command it started is running. The status block is handed back only after all have returned.

#### Scenario: Two executors in parallel
- **WHEN** a change has two independent task groups
- **THEN** the orchestrator launches two executors in one message in the foreground, gets both results and only then goes to the review; the dispatcher gets no intermediate notifications about the orchestrator's background work

#### Scenario: Rework after review
- **WHEN** the reviewer found five remarks, and the executor works on them
- **THEN** the orchestrator waits for the executor, repeats the review and only then hands back the status; there is no `not_ready` handback in the middle of the rework

### Requirement: Handback without leftovers
The executor prompt in the "Under the dispatcher" mode SHALL require running long-lived processes only as managed background tasks and stopping them before the report, and that a stand creates and deletes its temporary folders itself. Before the status block the orchestrator SHALL stop by id the background tasks it started itself, and list the processes, ports and folders left after its commands in `NOTES` as a line "Leftovers: …" above the `NOTES` line limit; no leftovers, no line.

#### Scenario: A stand server
- **WHEN** the live scenario needs a local HTTP server
- **THEN** the executor runs it as a managed task and stops it before the report; after the status nobody listens on the server port

#### Scenario: A folder cannot be removed
- **WHEN** a stand left a temporary folder, and deleting in the system TMP is forbidden by the environment check
- **THEN** the status `NOTES` has a "Leftovers:" line with the folder path

### Requirement: Live stand for status
In the "Under the dispatcher" mode the status field `LIVE` SHALL be one command that runs from the `WORKTREE` root without manual steps, without files outside `WORKTREE` and without preparation known only to the orchestrator, and gives the same output as stated in the status. If the Live Scenario has several steps or needs fixtures, the orchestrator SHALL make it a stand (a script in the repository that prepares and removes its data itself) and give the stand call in `LIVE`.

#### Scenario: A scenario with fixtures
- **WHEN** the Live Scenario needs four fixtures described in `verification.md`
- **THEN** the orchestrator writes a stand that creates the fixtures itself and hands back `LIVE` with this stand's call; the dispatcher repeats it without reading `verification.md`

#### Scenario: A window check
- **WHEN** the scenario is a walk through an application window
- **THEN** `LIVE` has the call of a stand that opens the window and prints the summary of the checks, not a description of a manual walk

### Requirement: Dispatched worktree environment
In the "Under the dispatcher" mode the orchestrator SHALL NOT prepare the environment: the worktree is already prepared by the dispatcher (ignored artifacts and dependency links in place); if something is missing it SHALL hand back `blocked` with what is missing. Into the main folder it SHALL write only `CLAIM`, and edit ignored files (`AGENTS.md`, documents, specs) in `WORKTREE`; it SHALL NOT delete or commit the dependency symlinks.

#### Scenario: A dependency is missing
- **WHEN** `WORKTREE` lacks a dependency the tests need
- **THEN** the orchestrator does not install it itself, but hands back `blocked` with the dependency name

#### Scenario: A node_modules link
- **WHEN** the orchestrator commits work in `WORKTREE`, where `node_modules` is a folder of links
- **THEN** the links are in place and did not get into the commit

### Requirement: Orchestrator writes code
In the "Under the dispatcher" mode the orchestrator SHALL do all tasks of the change itself, whatever their number and the number of code areas. It launches subagents only for independent acceptance (step 7a, tag `Review:`) and heavy reading (tag `Lookup:`). The other steps of the mode and the status block do not change.

#### Scenario: A large change
- **WHEN** a change has seven tasks in two code areas
- **THEN** the orchestrator does them itself, its subagents carry only the tags `Review:` and `Lookup:`, the change is handed back as a status block

#### Scenario: A small change
- **WHEN** a change has two tasks in one module
- **THEN** the orchestrator does them itself and launches only the reviewer
