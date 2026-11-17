## ADDED Requirements

### Requirement: CI wait settings
`sdd-pr.py wait` and `ship` SHALL take the whole time limit from `delivery.ci-timeout` (default 1200 s), the stuck check limit from `delivery.ci-stuck` (300 s) and the no-checks limit from `delivery.ci-no-checks` (180 s). A `--timeout` or `--stuck` flag of `wait` SHALL win over the setting; a line on stderr before the CI line SHALL name each limit with its source, stdout unchanged.

#### Scenario: A slow CI
- **WHEN** the file has `delivery.ci-timeout: 3600`, and `sdd-pr.py wait <url>` runs without `--timeout`
- **THEN** stderr names `timeout 3600 s (file)`, and the wait gives up only after 3600 s

#### Scenario: The flag wins
- **WHEN** the file has `delivery.ci-timeout: 3600`, and `wait <url> --timeout 60` runs
- **THEN** stderr names `timeout 60 s (flag)`

#### Scenario: A stuck limit above the timeout
- **WHEN** the file has `delivery.ci-stuck: 900` and `delivery.ci-timeout: 600`, and a required check never starts
- **THEN** `wait` gives `CI: infra` after 600 s: no limit extends the whole wait

### Requirement: Merge gate settings
With `delivery.require-ci: off` a PR whose checks stay empty past `delivery.ci-no-checks`, while the base branch requires no check, SHALL give `CI: none`, code 0 from `wait` and `ship`, and be merged by `merge` and `land`; a red, pending, stuck or missing required check SHALL still block. `delivery.code-scanning: warn` SHALL print the open alerts and merge, `off` SHALL not request them; `gate` (default) keeps code 8.

#### Scenario: A project without CI
- **WHEN** `delivery.require-ci` is `off` and the PR has no checks
- **THEN** `wait` prints `CI: none` with code 0, `merge` merges with code 0

#### Scenario: A red check with CI optional
- **WHEN** `delivery.require-ci` is `off` and one check is red
- **THEN** `wait` prints `CI: red`, `merge` refuses with code 1

#### Scenario: Scanning alerts as a warning
- **WHEN** `delivery.code-scanning` is `warn` and the PR has one open alert
- **THEN** `wait` prints `CI: green` and the alert line with code 0, and the PR is merged

### Requirement: PR shape settings
`delivery.delete-branch: off` SHALL keep the remote and the local branch after a PR merge by `merge` and `land`; `land-local` always deletes. `delivery.draft: on` SHALL make `sdd-pr.py open` and `ship` create a draft, and `merge`/`land` mark a draft PR ready for review after every gate, right before the merge request; a code 8 gate leaves it a draft, a failed ready request SHALL give code 1 without a merge.

#### Scenario: Keep the branch
- **WHEN** `delivery.delete-branch` is `off` and `land` merges `change/a`
- **THEN** the remote and the local `change/a` exist after the merge

#### Scenario: A draft PR
- **WHEN** `delivery.draft` is `on` and `sdd-pr.py open` runs
- **THEN** the fake `gh` log has `pr create --draft`, and `merge` later calls `pr ready` before the merge request

#### Scenario: A failed ready request
- **WHEN** `delivery.draft` is `on`, the checks passed, and `gh pr ready` fails
- **THEN** code 1 naming the ready step, no merge request, the PR stays a draft

### Requirement: Delivery settings from the main folder
`sdd-pr.py` SHALL read the keys of CI wait settings, Merge gate settings and PR shape settings from the main folder's `solo-sdd/config`, never from the PR or the WORKTREE; broken settings SHALL exit 1 before any merge request. Who may change them is the owner, by Owner-only paths gate of `pr-tool`: a PR that edits `solo-sdd/config` waits for the owner.

#### Scenario: A PR switches CI off for itself
- **WHEN** the WORKTREE `solo-sdd/config` has `delivery.require-ci: off`, the main folder's has none, and the PR has no checks
- **THEN** `wait` gives `CI: infra` "no checks", `merge` refuses with code 1
