# pr-tool Specification

## Purpose
The script `sdd-pr.py` runs a change's PR for the dispatcher: opens it, waits for CI and merges it, printing one summary line per step.

## Requirements

### Requirement: PR merge
`sdd-pr.py merge <url> <method> <hash>` SHALL merge the PR by a GitHub REST API request as the current `gh` login with the given method and `sha` equal to `<hash>`, without `gh pr merge`. Before the request the script SHALL make sure all PR checks passed (`pass` or `skipping`), otherwise code 1 "CI not green" without a request: with an owner bypass GitHub does not check them. `merge` SHALL accept an optional `--title <title>`. An API refusal gives code 1 with the reason text from the response.

#### Scenario: The PR is closed by a rule with an owner bypass
- **WHEN** the PR checks are green, `gh pr merge` would refuse because of the rule "only the owner merges", and the `gh` login is the owner with the bypass right
- **THEN** `merge` ends with code 0 and prints `PR #<n> <url> merged (squash)`

#### Scenario: CI not green
- **WHEN** a required PR check failed, and the `gh` login is the owner with the bypass right
- **THEN** code 1 "CI not green", the merge request is not sent, the PR is open

#### Scenario: No checks
- **WHEN** `gh pr checks` returned no check or failed
- **THEN** code 1 "CI not green", the merge request is not sent, the PR is open

#### Scenario: GitHub refused
- **WHEN** the checks passed, and the API answers with a refusal, for example 409 because of `sha`
- **THEN** code 1, the reason text from the response, the PR is open

#### Scenario: The branch could not be deleted
- **WHEN** the merge passed, and deleting the remote branch returned an error
- **THEN** code 0, the merge summary line and a separate line about the undeleted branch

#### Scenario: A PR branch from a fork
- **WHEN** the merge passed, and the PR head lies in a fork
- **THEN** code 0, there is no branch deletion request

#### Scenario: An empty title
- **WHEN** `--title` is not passed, and PR #118 has an empty title or `gh pr view` failed
- **THEN** code 1, the merge request is not sent, the PR is open; a commit " (#118)" does not get into the main branch

#### Scenario: The title from the local commit
- **WHEN** `merge <url> squash <hash> --title "fix(222-ooxml): read templates"` for PR #118
- **THEN** the commit in the main branch is named "fix(222-ooxml): read templates (#118)", the PR title is not requested for this

#### Scenario: The previous checks before the request
- **WHEN** the PR is already merged, `<hash>` is not the PR head or main moved ahead
- **THEN** respectively code 0, code 1 or code 5; these checks go before the merge request, as before

#### Scenario: The branch is deleted after merge
- **WHEN** the merge passed, and the PR head lies in this repository
- **THEN** the remote branch is deleted by a separate request

#### Scenario: GitHub already deleted the branch
- **WHEN** the branch deletion request returned 404 or 422
- **THEN** GitHub already deleted the branch: no line about it is printed, code 0

#### Scenario: Why a fork branch is not deleted
- **WHEN** the PR head lies in a fork, and this repository has a branch with the same name
- **THEN** the script does not delete it: the PR branch does not live in this repository, and the same name here is someone else's branch

### Requirement: Required checks in CI wait
`sdd-pr.py wait <url>` SHALL take the required checks of the PR's base branch from the GitHub branch rules (`rules/branches/<branch>`) and the classic protection visible in the branch description (`branches/<branch>`), without requests that need admin rights. The `green` result SHALL be printed only when every required check is among the PR checks and passed (`pass` or `skipping`), and there are no failed or cancelled ones.

#### Scenario: A required check did not start
- **WHEN** the checks `Checks` and `CodeQL` passed, and the required `PR title` hangs `pending` 300 s after they finished
- **THEN** `wait` prints `CI: infra` and "required check did not start: PR title", code 4, without waiting for the 1200 s deadline

#### Scenario: A required check is not in the list
- **WHEN** all PR checks passed, and the required `PR title` is not among them for 300 s
- **THEN** the result is `infra` with its name, not `green`

#### Scenario: No required checks
- **WHEN** the base branch has neither a ruleset nor classic protection, and all PR checks passed
- **THEN** the result is `green` without a warning

#### Scenario: The rules cannot be read
- **WHEN** the branch rules request returned an error, and all PR checks passed
- **THEN** the result is `green` and a warning line that the required checks were not checked

#### Scenario: The threshold of a check that did not start
- **WHEN** a required check is not in the list or is `pending` for more than 300 s after all others finished
- **THEN** the result is `infra` (code 4) with the line "required check did not start: <name>"

#### Scenario: Restarting a check that did not start
- **WHEN** `wait` gave the result "required check did not start"
- **THEN** the dispatcher restarts CI with one empty commit in the change branch and a new wait, not with `gh run rerun`: such a check has no failed run

### Requirement: Ship and land
`sdd-pr.py ship <MAIN> <WORKTREE> <main> <title>` SHALL update the `WORKTREE` branch from `origin/<main>`, run `sdd-worktree.py refresh`, push the branch, open or update the PR and wait for CI by the rules of `wait`; no step runs after a failed one.

#### Scenario: ship codes
- **WHEN** `ship` finished
- **THEN** code 0 means `green`, 3 `red`, 4 `infra`, 6 a conflict (the merge undone, the files named, no push), 1 a step failure with its name

#### Scenario: A conflict on refresh
- **WHEN** `sdd-worktree.py refresh` in `ship` returned code 3 and left conflict markers in `WORKTREE`
- **THEN** code 6, the files are named, no push

#### Scenario: Finding sdd-worktree.py
- **WHEN** `ship` looks for `sdd-worktree.py` in the script's own folder under the names `sdd-worktree.py` and `sdd_worktree.py`, and neither exists
- **THEN** code 1, the step `refresh`

#### Scenario: Steps after a failed one
- **WHEN** one of the `ship` steps failed
- **THEN** no next step runs

#### Scenario: The push failed
- **WHEN** the branch push in `ship` ended with an error
- **THEN** code 1, the summary line names the push step and the reason, the CI wait does not start

#### Scenario: A conflict on update
- **WHEN** updating the branch from `origin/main` in `ship` gives a conflict in `docs/cli.md`
- **THEN** the merge in `WORKTREE` is undone, code 6, the line names `docs/cli.md`, no push

### Requirement: Land after green
`sdd-pr.py land <MAIN> <WORKTREE> <url> <method>` SHALL merge the PR (requirement PR merge) with the `sha` of the `WORKTREE` head, then pull the main folder, run `sdd-worktree.py transport`, `remove` and delete the branch `change/<id>`, stopping at the first failure with the step name.

#### Scenario: The merge title
- **WHEN** `land` merges a PR
- **THEN** `--title` equals the first line of the branch's last own commit: along the first parent from the `WORKTREE` head, without merge commits and empty commits; no such commit or an empty line gives code 1 without a merge

#### Scenario: The head is a service commit
- **WHEN** the `WORKTREE` head is a merge commit of an update from `origin/main` or an empty CI restart commit
- **THEN** the commit title in the main branch comes from the change's last own commit, and `sha` stays the head

#### Scenario: The order of steps after merge
- **WHEN** the PR is merged
- **THEN** the main folder gets `fetch` and `merge --ff-only`, then `sdd-worktree.py transport`, `remove` and deleting the branch `change/<id>` run

#### Scenario: land codes
- **WHEN** `land` finished
- **THEN** code 0 means everything done, 5 main moved ahead and nothing is merged, 1 the merge failed and the main folder is untouched, 7 the PR is merged but a step after merge failed ("merged, not finished: <step>")

#### Scenario: A repeated land after code 7
- **WHEN** `land` is repeated after code 7 and sees the PR in the MERGED state
- **THEN** the merge is skipped, the run continues from the first unfinished step; no `WORKTREE` folder means `transport` and `remove` are skipped; no branch `change/<id>` means code 0

#### Scenario: The merge failed
- **WHEN** in `land` the GitHub API refused the merge
- **THEN** code 1, the steps `fetch`, `transport` and cleanup did not run, the main folder is unchanged

#### Scenario: Main moved ahead
- **WHEN** before the merge in `land` main holds commits that are not in the PR branch
- **THEN** code 5, the PR is not merged, `WORKTREE` and the branch are in place

#### Scenario: A failure after merge
- **WHEN** the PR is merged, and `transport` returned code 3
- **THEN** code 7 "merged, not finished: transport", the cleanup did not run; a repeated `land` does not merge again and starts with `transport`

### Requirement: Code scanning in CI wait
When all PR checks passed, `sdd-pr.py wait <url>` SHALL request the open GitHub code scanning alerts on the PR (`ref=refs/pull/<n>/merge`, `state=open`): at least one gives the result `codeql`, code 8, none gives `green`. `sdd-pr.py ship` SHALL pass code 8 as is.

#### Scenario: The format of alert lines
- **WHEN** the result is `codeql`
- **THEN** at most 20 lines of the form "#<number> <rule> <file>:<line> <text>" are printed

#### Scenario: Signs of disabled scanning
- **WHEN** the answer to the alerts request is 403 with text about Advanced Security or code scanning, or 404
- **THEN** the result is `green` without lines

#### Scenario: Another query failure
- **WHEN** the alerts request ended with another error
- **THEN** the result is `green` and one line "code scanning alerts not checked"

#### Scenario: ship passes code 8
- **WHEN** `wait` inside `ship` returned code 8
- **THEN** `ship` ends with code 8 unchanged

#### Scenario: An open alert
- **WHEN** all PR checks passed, and the PR has an open alert `js/bad-code-sanitization` in `src/check.ts:102`
- **THEN** `wait` prints `CI: codeql` and a line with the number, the rule and `src/check.ts:102`, code 8

#### Scenario: Scanning is not enabled
- **WHEN** the checks passed, and the alerts request returned 403 "Advanced Security must be enabled" or 404
- **THEN** the result is `green`, code 0, without extra lines

#### Scenario: A query failure
- **WHEN** the checks passed, and the alerts request returned 500
- **THEN** the result is `green`, code 0, the line "code scanning alerts not checked"

#### Scenario: Many alerts
- **WHEN** the PR has 45 open alerts
- **THEN** the result is `codeql`, code 8, 20 explanation lines

### Requirement: PR merge commit title
For the methods `squash` and `merge` the commit title of `sdd-pr.py merge` SHALL be the value of `--title`, and without it the PR title from the same `gh pr view` response by which the head is checked; " (#<n>)" is appended to it. An empty title or a failure of this request gives code 1 without a merge request.

#### Scenario: The PR title without --title
- **WHEN** `merge <url> squash <hash>` without `--title` for PR #7 with the title "Add stats"
- **THEN** the commit in the main branch is named "Add stats (#7)"

### Requirement: Owner-only paths gate
Before the merge request `sdd-pr.py merge` and `land` SHALL check the PR files, including old names of renamed ones, against the "owner only" paths: `.github/workflows/**` and the backquoted patterns of the "Owner only:" item of the "Delivery" section of the main folder's `AGENTS.md` (`*` within a name, `**` across folders). A match or an edit of this item gives code 8 "waits for the owner: <paths>", no merge request, the PR stays open. Unreadable `AGENTS.md` means only `.github/workflows/**`.

#### Scenario: A CI edit
- **WHEN** a green PR changes `.github/workflows/ci.yml`
- **THEN** code 8 with this path, the PR is open, no merge is requested

#### Scenario: An owner path
- **WHEN** "Delivery" has "Owner only: `global/work_hooks.py`", and the PR changes this file
- **THEN** code 8 with `global/work_hooks.py`

#### Scenario: A change shortens the list
- **WHEN** the PR removes a path from the item "Owner only:" in `AGENTS.md`
- **THEN** code 8: the item is checked by the main folder's `AGENTS.md`, and an edit of the item itself waits for the owner

#### Scenario: land and AGENTS.md outside git
- **WHEN** `AGENTS.md` is ignored by git, and in the WORKTREE `AGENTS.md` the item "Owner only:" differs from the main folder
- **THEN** `land` returns code 8: the transfer after merge would bring this item into the main folder

#### Scenario: The file list failed
- **WHEN** the PR files request failed or returned something other than JSON
- **THEN** code 1, no merge is requested, the PR is open

### Requirement: Base branch from settings
`sdd-pr.py open`, `ship` and `land` and `sdd-worktree.py setup` SHALL use `delivery.base` as the target and the start of a change branch; without the key, the remote's default branch as before. Unreadable settings SHALL exit 1 with the reason, never fall back.

#### Scenario: Integration into dev
- **WHEN** `delivery.base: dev` and the dispatcher prepares and ships a change
- **THEN** the worktree starts from `origin/dev`, the PR targets `dev`, `land` pulls `dev`

#### Scenario: Broken settings
- **WHEN** `solo-sdd/config` has a broken line and `sdd-pr.py ship` runs
- **THEN** exit 1 naming the line; no PR targets the default branch by mistake

### Requirement: Promotion PR
`sdd-pr.py promote <from> <to>` SHALL open a PR from `<from>` to `<to>` or print the URL of an open one, and SHALL NOT merge it. `<to>` given as `release/*` SHALL resolve to the newest existing `release/` branch by version; none existing SHALL exit 1 with a message.

#### Scenario: Next step
- **WHEN** `promote dev staging` runs and no such PR is open
- **THEN** a PR from `dev` to `staging` is opened, its URL printed, nothing merged

#### Scenario: Release pattern
- **WHEN** `release/1.9.0` and `release/1.10.0` exist and `promote staging release/*` runs
- **THEN** the PR targets `release/1.10.0`

### Requirement: Human merge mode
With `delivery.merge-by: human`, `sdd-pr.py merge` and `land` SHALL NOT merge: they SHALL exit with code 8 and `waits for human merge: <url>`, leaving the PR open. `land <MAIN> <WORKTREE> <url> --after-merge` SHALL check the PR is merged, then pull, carry the artifacts and remove the worktree and branch; an unmerged PR SHALL exit 8 again. This gate SHALL apply before Land after green, like Owner-only paths gate.

#### Scenario: Agent tries to merge
- **WHEN** `merge-by: human` and `sdd-pr.py land` runs on a green PR
- **THEN** code 8, the PR stays open, the worktree stays

#### Scenario: After a person merged
- **WHEN** a person merged the PR and `land --after-merge` runs
- **THEN** the main folder is pulled, the worktree and the branch are removed, code 0

#### Scenario: After-merge on an open PR
- **WHEN** the PR is still open and `land --after-merge` runs
- **THEN** code 8, `waits for human merge: <url>`, the worktree stays

### Requirement: Path checklists
When a PR's files match `checklist.<name>.paths`, `sdd-pr.py open` and `ship` SHALL add to the PR body a section `## Checklist: <name>` with the items of `checklist.<name>.file`. `merge` and `land` SHALL exit with code 8 and `checklist <name>: <n> open items` while an item of the section is unticked.

#### Scenario: Billing touched
- **WHEN** `checklist.money-safety.paths: billing/**` and the PR changes `billing/charge.py`
- **THEN** the PR body has `## Checklist: money-safety` with the file's items

#### Scenario: Open items
- **WHEN** two of five items are unticked and `land` runs
- **THEN** code 8, `checklist money-safety: 2 open items`, nothing merged

#### Scenario: All ticked
- **WHEN** a person ticked every item
- **THEN** `land` merges as usual

#### Scenario: No checklist path
- **WHEN** the PR touches no path of any checklist
- **THEN** the body gets no section and `land` merges as usual

#### Scenario: A section edited away
- **WHEN** the PR changes `billing/charge.py` and its body has no `## Checklist: money-safety` section
- **THEN** `merge` counts every item of the file as open: code 8, nothing merged

#### Scenario: A repeated ship keeps the ticks
- **WHEN** the PR body already has `## Checklist: money-safety` with ticked items and `ship` runs again
- **THEN** the section is not rewritten; only a matching checklist without a section is appended

#### Scenario: The PR edits the checklist itself
- **WHEN** the PR changes only `docs/checklists/money-safety.md` or only `solo-sdd/config`
- **THEN** the section is added: a checklist's own file and the settings file are among its paths, and the settings and the file are read from the main folder, not from the PR

#### Scenario: A broken checklist
- **WHEN** a checklist has only one of its two keys, or its file is unreadable or holds no `- [ ]` item, and `open`, `ship` or `merge` runs
- **THEN** code 1 naming the checklist, before the push or the merge request

#### Scenario: A section emptied or replaced
- **WHEN** the PR changes `billing/charge.py` and its section holds only the heading, a `- [x]` line that is not in the file, or the file's items with the unticked ones removed
- **THEN** every item of the file not ticked with its own text counts as open: code 8, nothing merged

### Requirement: Checklist approval
When a PR has a checklist by Path checklists, `merge` and `land` SHALL exit with code 8 and `checklist <name>: no approval on <sha>` until GitHub lists an `APPROVED` review on the PR's head commit by an account other than the PR author, besides the open items gate. A review read that fails or returns data it cannot parse SHALL count as no approval.

#### Scenario: Ticked but not approved
- **WHEN** every item of `## Checklist: money-safety` is ticked and the PR has no approving review
- **THEN** `land` exits 8 with `checklist money-safety: no approval on <sha>`, nothing merged

#### Scenario: Approved on the head commit
- **WHEN** every item is ticked and another account approved the head commit
- **THEN** `land` merges as usual

#### Scenario: Approval before a new commit
- **WHEN** the approval is on an earlier commit and the branch got a new one
- **THEN** code 8: the approval does not cover the head commit

#### Scenario: The author's own review
- **WHEN** the only review is by the PR author, or a later review of the same account requests changes
- **THEN** code 8: only the latest review of each other account counts, and it must be `APPROVED`

#### Scenario: Reviews cannot be read
- **WHEN** the reviews call fails, times out or returns something other than a list of reviews
- **THEN** code 8 with the reason that the reviews were not read, nothing merged

#### Scenario: No checklist path
- **WHEN** the PR touches no path of any checklist
- **THEN** no review is required and `land` merges as usual

### Requirement: Ship through the PR tool
In a project with a `solo-sdd/` tree whose delivery mode (step 1 of `/ship`) is `pr`, the `/ship` skill SHALL open, wait for and merge the PR with `sdd-pr.py open`, `wait` and `merge` and SHALL NOT call `gh pr create` or `gh pr merge` itself. Code 5 from `merge` SHALL update the branch from main, push and repeat `wait` and `merge`; code 8 SHALL end the skill with the printed reason, the PR left open for the owner; code 1 SHALL end it as not done with the reason.

#### Scenario: A checklist path
- **WHEN** `/ship` runs in a project whose change edits a checklist path and the PR has no approval
- **THEN** the skill reports `checklist <name>: …` from `sdd-pr.py` and stops, the PR is open

#### Scenario: A project without the tree
- **WHEN** `/ship` runs in a repository without `solo-sdd/`
- **THEN** the skill uses `gh pr create` and `gh pr merge` as before

#### Scenario: Main moved ahead
- **WHEN** `sdd-pr.py merge` returns code 5
- **THEN** the skill updates the branch from main, pushes it and runs `wait` and `merge` again
