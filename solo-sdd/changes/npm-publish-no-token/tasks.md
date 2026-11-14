## 1. Implementation

- [ ] 1.1 Requirement Registry publishing (MODIFIED): `test_npm_job` in `tests/test_release.py` asserts the npm job holds neither `NPM_TOKEN` nor `_authToken` instead of the token branch; `python3 -m unittest test_release` from `tests/` fails on the current workflow
- [ ] 1.2 Drop the `NPM_TOKEN` env entry, its comment and the `_authToken` line from the npm job of `.github/workflows/release.yml`; `python3 -m unittest test_release` from `tests/` passes

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate npm-publish-no-token` and archive the change with `solo-sdd archive npm-publish-no-token --yes`
