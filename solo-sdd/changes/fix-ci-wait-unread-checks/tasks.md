## 1. Implementation

- [x] 1.1 Requirement Required checks in CI wait, scenario Checks not read with required checks: a test in `tests/test_sdd_pr.py` next to `test_ci_optional_with_unread_checks`, with `rules_json` that requires `PR title` and `fail_json` on the `checks` call; expect `[INFRA_LINE, "checks not read: boom checks"]` (the fake's stderr); it fails on the current code
- [x] 1.2 Remove the cause at `global/sdd_pr.py:859`-`887`: an unread poll computes no `stuck` and leaves the stuck timer `since` as it was; `checks()` hands back the brief stderr of the failed call (`gh exit <code>` when it is empty); the deadline with the last poll unread prints `checks not read: <error>`; the expected line of `test_ci_optional_with_unread_checks` becomes `checks not read: boom checks` on purpose (the MODIFIED requirement's new line), every other existing assertion kept; proven by 1.1 and `python3 tests/test_sdd_pr.py`
- [x] 1.3 Add the unread-checks step to `tests/stands/required-checks.py` by the Live Scenario; proven by running the stand

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-ci-wait-unread-checks` and archive the change with `solo-sdd archive fix-ci-wait-unread-checks --yes`
