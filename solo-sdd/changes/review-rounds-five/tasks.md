## 1. Implementation

- [x] 1.1 A row of the existing default test in `tests/test_settings.py` named after Review rounds: `config get process.review-rounds` without a file value prints `5` with `source: default`; it fails on the current code
- [x] 1.2 The default `"5"` of `process.review-rounds` in the settings block of `solo_sdd/settings.py`, copied by `python3 scripts/sync_blocks.py` into `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py` and `global/work_hooks.py`; `--check` prints nothing and the row of 1.1 passes
- [x] 1.3 Rows in `tests/test_skill_commands.py` named after Review rounds and Extra round for fix findings: `spec-next` names default 5, the fallback 5, the extra round only after the second or later round and for findings in the lines of the last rework, no second extra round and the report line; they fail first
- [x] 1.4 `skills/spec-next/SKILL.md` (the Rounds item and the table row: the extra round decided by the finding places against `git diff` of the last rework), `ALGORITHM.md`, `docs/settings.md` and the review row of `docs/stop-conditions.md`; every reader that `grep -rn "review-rounds\|review rounds\|three rounds\|third round"` finds outside the archive names the setting and 5; the rows of 1.3 pass
- [x] 1.5 `tests/stands/settings-tui.py`: its expected default line for `process.review-rounds` becomes 5 under the modified Review rounds, every other assertion kept; the stand passes

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate review-rounds-five` and archive the change with `solo-sdd archive review-rounds-five --yes`
