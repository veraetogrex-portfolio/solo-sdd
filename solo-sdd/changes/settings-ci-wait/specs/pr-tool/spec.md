## MODIFIED Requirements

### Requirement: PR merge
`sdd-pr.py merge <url> <method> <hash>` SHALL merge the PR by a GitHub REST API request as the current `gh` login with the method and `sha` `<hash>`, not `gh pr merge`. Before it every PR check SHALL have passed (`pass` or `skipping`), else code 1 "CI not green" without a request (an owner bypass skips GitHub's own check); no checks pass only under `delivery.require-ci: off`. `merge` takes an optional `--title <title>`. An API refusal gives code 1 with the reason text.

#### Scenario: The PR is closed by a rule with an owner bypass
- **WHEN** the PR checks are green, `gh pr merge` would refuse because of the rule "only the owner merges", and the `gh` login is the owner with the bypass right
- **THEN** `merge` ends with code 0 and prints `PR #<n> <url> merged (squash)`

#### Scenario: CI not green
- **WHEN** a required PR check failed, and the `gh` login is the owner with the bypass right
- **THEN** code 1 "CI not green", the merge request is not sent, the PR is open

#### Scenario: No checks
- **WHEN** `gh pr checks` failed, or returned no check while `delivery.require-ci` is `on`
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
- **WHEN** the merge passed, the PR head lies in this repository, and `delivery.delete-branch` is not `off`
- **THEN** the remote branch is deleted by a separate request

#### Scenario: GitHub already deleted the branch
- **WHEN** the branch deletion request returned 404 or 422
- **THEN** GitHub already deleted the branch: no line about it is printed, code 0

#### Scenario: Why a fork branch is not deleted
- **WHEN** the PR head lies in a fork, and this repository has a branch with the same name
- **THEN** the script does not delete it: the PR branch does not live in this repository, and the same name here is someone else's branch

#### Scenario: No checks with CI optional
- **WHEN** `delivery.require-ci` is `off`, and `gh pr checks` returned no check
- **THEN** the merge request is sent, code 0

#### Scenario: The branch kept
- **WHEN** the merge passed, and `delivery.delete-branch` is `off`
- **THEN** there is no branch deletion request, code 0

### Requirement: Required checks in CI wait
`sdd-pr.py wait <url>` SHALL take the required checks of the PR's base branch from the GitHub branch rules (`rules/branches/<branch>`) and the classic protection visible in the branch description (`branches/<branch>`), without requests that need admin rights. The `green` result SHALL be printed only when every required check is among the PR checks and passed (`pass` or `skipping`), and there are no failed or cancelled ones.

#### Scenario: A required check did not start
- **WHEN** the checks `Checks` and `CodeQL` passed, and the required `PR title` hangs `pending` 300 s after they finished
- **THEN** `wait` prints `CI: infra` and "required check did not start: PR title", code 4, without waiting for the `delivery.ci-timeout` deadline (default 1200 s)

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
- **WHEN** a required check is not in the list or is `pending` for more than `delivery.ci-stuck` seconds (default 300) after all others finished
- **THEN** the result is `infra` (code 4) with the line "required check did not start: <name>"

#### Scenario: Restarting a check that did not start
- **WHEN** `wait` gave the result "required check did not start"
- **THEN** the dispatcher restarts CI with one empty commit in the change branch and a new wait, not with `gh run rerun`: such a check has no failed run

#### Scenario: CI optional with a required check
- **WHEN** `delivery.require-ci` is `off`, the base branch requires `PR title`, and the PR has no checks
- **THEN** the result is `infra` with "required check did not start: PR title", not `none`: `none` needs a base branch that requires no check

### Requirement: Ship and land
`sdd-pr.py ship <MAIN> <WORKTREE> <main> <title>` SHALL update the `WORKTREE` branch from `origin/<main>`, run `sdd-worktree.py refresh`, push the branch, open or update the PR and wait for CI by the rules of `wait`; no step runs after a failed one.

#### Scenario: ship codes
- **WHEN** `ship` finished
- **THEN** code 0 means `green` (or `none` under `delivery.require-ci: off`), 3 `red`, 4 `infra`, 6 a conflict (the merge undone, the files named, no push), 1 a step failure with its name

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
`sdd-pr.py land <MAIN> <WORKTREE> <url> <method>` SHALL merge the PR (requirement PR merge) with the `sha` of the `WORKTREE` head, then pull the main folder, run `sdd-worktree.py transport`, `remove` and delete the branch `change/<id>` unless `delivery.delete-branch` is `off`, stopping at the first failure with the step name.

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

#### Scenario: A repeated land with the branch kept
- **WHEN** `delivery.delete-branch` is `off`, the PR is MERGED, there is no `WORKTREE` folder, and `change/<id>` exists
- **THEN** code 0, the branch stays

### Requirement: Code scanning in CI wait
When all PR checks passed and `delivery.code-scanning` is not `off`, `sdd-pr.py wait <url>` SHALL request the open GitHub code scanning alerts on the PR (`ref=refs/pull/<n>/merge`, `state=open`): under `gate` (default) at least one gives the result `codeql`, code 8, none gives `green`; under `warn` the result is `green`, code 0, with the alert lines. `off` sends no request: `green`, no alert line. `sdd-pr.py ship` SHALL pass code 8 as is.

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
