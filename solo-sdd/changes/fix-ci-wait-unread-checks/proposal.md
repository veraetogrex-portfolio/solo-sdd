# Proposal

## Why

Reproduction (review finding of the settings-* run, 2026-11-17; read in code on 2026-11-18):
1. The base branch requires the check `PR title`.
2. Every `gh pr checks` call fails, for example with an auth or network error.
3. `sdd-pr.py wait <url>` runs.
4. Expected: `CI: infra` and `checks not read` with gh's error.
5. Got: `CI: infra` and `required check did not start: PR title`. gh's error is printed nowhere. A person or the dispatcher then follows the wrong path: the empty-commit restart for a check that did not start, instead of fixing gh.

Cause: `global/sdd_pr.py:859`, `unread, rows = rows is None, rows or []`, turns unread checks into an empty list. Then `stuck_checks(rows, required)` at `global/sdd_pr.py:862` (body at `:823`) reports every required check as missing. At `global/sdd_pr.py:887` the stuck lines win over `checks not read`.

## What Changes

- While the checks cannot be read, `wait` reports no required check as "did not start". At the deadline it gives `CI: infra` with `checks not read: <gh error>`; the line `checks not read` of every unread case (also under `delivery.require-ci: off`) gains the error.
- A read that succeeds later goes on by the existing rules.

## Capabilities

### New Capabilities

### Modified Capabilities
- `pr-tool`: MODIFIED requirement Required checks in CI wait (a new scenario Checks not read with required checks).

## Impact

- `global/sdd_pr.py`
- `tests/test_sdd_pr.py`
- `tests/stands/required-checks.py`

## Out of Scope

- `delivery.require-ci` and the branch-rules read: unchanged.
- Retrying gh inside one poll: the poll interval already repeats the call.
- Neighbouring changes of this plan: `test-runner-deps-check`, `dispatched-status-self-check`, `fix-settings-entry-scroll`, `fix-worktree-ignored-overwrite`, `fix-stop-gate-worktree-config`, `fix-setup-links-exclude`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create a change" (on the follow-up list after the settings-* run, item: a `gh pr checks` call that keeps failing under require-ci on is reported as "required check did not start")
