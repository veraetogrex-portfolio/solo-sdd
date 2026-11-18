## Live Scenario

1. `python3 tests/stands/required-checks.py` → the stand runs the repository's `global/sdd_pr.py wait` with a fake `gh` whose branch rules require `PR title`. A new step makes every `gh pr checks` call exit 1 with `HTTP 401: Bad credentials`.
2. The new step sees code 4, `CI: infra` and a line `checks not read: HTTP 401: Bad credentials`, and no `required check did not start` line. On the previous code it sees `required check did not start: PR title`.
3. The earlier steps of the stand still pass, and it prints its summary line with every check passed.

## Needs

none

## Fallback

Not needed: the scenario runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: the new line `checks not read: <gh error>` and "every existing assertion kept" clashed: `test_ci_optional_with_unread_checks` expects the bare `checks not read` → the error is added to every unread case and that one expected line changes on purpose — two forms of one outcome would read worse than one changed assertion.
- analyze: no rule for a poll that fails between polls that read → an unread poll leaves the stuck timer as it was and the deadline line follows the last poll — a failed read is no evidence that a check started or did not.
- analyze: an empty stderr had no text → `gh exit <code>` — the line never ends in a bare colon.
- analyze: the proposal placed the body of `stuck_checks` at `:830`; it starts at `global/sdd_pr.py:823` → corrected.
