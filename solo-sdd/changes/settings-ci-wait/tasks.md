## 1. Implementation

- [ ] 1.1 Rows in `tests/test_settings.py`: the seven keys with type, default and `describe` group `delivery`; then the keys in the settings block of `solo_sdd/settings.py` with `ABOUT` lines, `python3 scripts/sync_blocks.py --check` prints nothing; the rows pass
- [ ] 1.2 Rows in `tests/test_sdd_pr.py` named after CI wait settings and Required checks in CI wait: the limits from the main folder's file, the flag winning, the stderr limits line with sources and stdout unchanged, a stuck limit above the timeout; they fail first
- [ ] 1.3 `global/sdd_pr.py` `cmd_wait`, `cmd_ship` and the command line take the three limits from the settings; the rows of 1.2 pass, the existing wait tests keep every assertion
- [ ] 1.4 Rows in `tests/test_sdd_pr.py` named after Merge gate settings, PR merge, Ship and land and Code scanning in CI wait: `CI: none` with code 0 from `wait` and `ship`, a required check with `require-ci: off` giving `infra`, a red check still blocking, scanning `warn` (`CI: green`, alert lines, code 0) and `off` (no request); they fail first, then `global/sdd_pr.py` passes them
- [ ] 1.5 Rows in `tests/test_sdd_pr.py` named after PR shape settings and Land after green: kept remote and local branch, a repeated land with the branch kept giving code 0, draft open by `open` and `ship`, `pr ready` after the gates and before the merge request, a code 8 gate keeping the draft, a failed ready request giving code 1; they fail first, then `global/sdd_pr.py` passes them
- [ ] 1.6 Rows in `tests/test_sdd_pr.py` named after Delivery settings from the main folder: a WORKTREE config with `require-ci: off` changes nothing, broken main-folder settings exit 1 before the merge request; they fail first, then pass
- [ ] 1.7 `skills/ship/SKILL.md` names `delivery.ci-timeout` instead of the fixed 1200 s and the `CI: none` outcome; `skills/spec-dispatch/merge.md` lands on `none` as on `green`, `skills/spec-dispatch/report.md` lists `none` in the CI column; rows in `tests/test_skill_commands.py` fail first and then pass; `docs/settings.md` rows of the seven keys; `tests/stands/settings-tui.py` gains the rows, every assertion kept
- [ ] 1.8 The stand `tests/stands/settings-ci-wait.py` runs the Live Scenario against a fake `gh`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-ci-wait` and archive the change with `solo-sdd archive settings-ci-wait --yes`
