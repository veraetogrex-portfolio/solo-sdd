## 1. Implementation

- [ ] 1.1 Requirement Plan committed: a row in `tests/test_skill_commands.py` that step 9 of `skills/spec-plan/SKILL.md` names the branch `plan/<first id>`, a temporary worktree, `delivery.mode` and `ship` for `pr`, and the main branch for `local`; fails on the current text
- [ ] 1.2 Step 9 and the `Plan:` line of the report form in `skills/spec-plan/SKILL.md` by the requirement; the row of 1.1 passes, the Line length test of `tests/test_readme.py` passes, `python3 sync.py push` deploys the skill and `python3 sync.py status` shows no unexpected drift

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate plan-commit-branch-fix` and archive the change with `solo-sdd archive plan-commit-branch-fix --yes`
