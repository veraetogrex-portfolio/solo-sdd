## ADDED Requirements

### Requirement: Unread checks in CI wait
When `sdd-pr.py wait` gives `CI: infra` with `checks not read: <error>`, the `ship` and `spec-dispatch` skills SHALL send the agent to fix what gh reports (auth, network) and run `wait` again, with no CI rerun and no empty commit; a second `checks not read` SHALL make the change "not merged: PR" with the gh error.

#### Scenario: gh cannot read the checks
- **WHEN** `wait` prints `CI: infra` and `checks not read: HTTP 401: Bad credentials`
- **THEN** the laid-out `ship` and `spec-dispatch` texts name this line with the step: fix gh, run `wait` again, no `gh run rerun` and no empty commit

#### Scenario: gh still cannot read the checks
- **WHEN** the repeated `wait` prints `checks not read` again
- **THEN** the laid-out `spec-dispatch` text makes the change "not merged: PR" with the gh error, and the `ship` text stops as not done with it

### Requirement: Return keeps worktree ignored files
The branch update of the Return on conflict message SHALL first run `sdd-pr.py overwrites <WORKTREE> <main ref>` (`<main branch>`, in `pr` mode `origin/<main>` after `fetch`) and merge only on code 0; on any other code the orchestrator SHALL NOT merge and SHALL hand back `STATUS: not_ready` with the printed line in `NOTES`.

#### Scenario: The main branch tracks an ignored worktree file
- **WHEN** WORKTREE holds an ignored `solo-sdd/config` with its own text and a commit of its own branch, and the main branch now tracks `solo-sdd/config`
- **THEN** the check of the laid-out Return on conflict text names `solo-sdd/config` with code 1, no merge runs, the file keeps its text, and the orchestrator hands back `not_ready` with the line in `NOTES`

#### Scenario: Nothing would be overwritten
- **WHEN** the main branch tracks no path WORKTREE holds untracked
- **THEN** the check prints nothing with code 0, and the return merges as before
