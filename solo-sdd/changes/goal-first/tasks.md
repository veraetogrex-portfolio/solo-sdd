## 1. Implementation

- [ ] 1.1 Requirements Goal and check for a step-only request and Named steps kept, extras proposed: add the two rules to the Why item of `skills/spec-plan/creation.md` and a `Proposals:` line to the report form of `spec-plan`; if `skills/spec-plan/SKILL.md` would pass the size budget, move its `## Report` section into a step file `skills/spec-plan/report.md` with its `targets.json` and `tests/affected.json` entries; rows in the laid-out skill text test of `tests/test_skill_commands.py` for both rules and the `Proposals:` line; proven by `python3 tests/test_skill_commands.py` (with the size budget and step files tests)
- [ ] 1.2 Add the goal-first lines, with the report opening outside `spec-plan`, to section 6 of `global/AGENTS.md`; a row in `tests/test_skill_commands.py` that section 6 names them; proven by `python3 tests/test_skill_commands.py`
- [ ] 1.3 Write `tests/stands/goal-first.py` (the demo copy as a git project, `process.analyze: off`, the slow test, the requests, `--grade` and `--grade-report`); proven by `--grade` on a reference change folder and report written by hand giving five `yes` lines and on a change without a goal in Why giving `goal in Why: no`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate goal-first` and archive the change with `solo-sdd archive goal-first --yes`
