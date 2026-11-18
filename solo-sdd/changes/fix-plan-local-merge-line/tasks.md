## 1. Implementation

- [ ] 1.1 Requirement Local merge method, scenario The plan line in local mode: a test in `tests/test_sdd_dispatch_plan.py` next to `test_defaults_without_sources` for a project with `delivery.mode: local` and `delivery.merge: rebase`; it expects `delivery: local (file), local merge: merge (default)` and fails on the current code
- [ ] 1.2 Remove the cause at `global/sdd_dispatch_plan.py:827`: in `local` mode print `local merge:` with `deliver["delivery.local-merge"]`. Update the local-mode expected lines of the existing tests (`test_script_prints_the_probe_as_second_line` and the lines at `tests/test_sdd_dispatch_plan.py:1104`, `:1141`, `:1164`) to the new form, as this MODIFIED requirement says, keeping their `pr` lines and every other assertion. Name both forms in the module docstring and in `skills/spec-dispatch/preparation.md`. Proven by `python3 tests/test_sdd_dispatch_plan.py` and `python3 tests/test_skill_commands.py`
- [ ] 1.3 Write the stand `tests/stands/plan-local-merge-line.py` by the Live Scenario; proven by running it

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-plan-local-merge-line` and archive the change with `solo-sdd archive fix-plan-local-merge-line --yes`
