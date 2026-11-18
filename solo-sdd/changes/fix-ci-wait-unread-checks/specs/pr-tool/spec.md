## MODIFIED Requirements

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

#### Scenario: Checks not read with required checks
- **WHEN** the base branch requires `PR title`, and every `gh pr checks` call of `wait` fails until the deadline
- **THEN** the result is `CI: infra` with `checks not read: <the gh error>`, code 4, and no line "required check did not start"
