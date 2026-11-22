## 1. Implementation

- [ ] 1.1 Requirement Readers of waiting lines: name the first table in `skills/context-resume/SKILL.md`, `skills/spec-next/SKILL.md` and its `closing.md`, `skills/spec-plan/SKILL.md`, `skills/blockers/SKILL.md` and `skills/project-init/SKILL.md`, and the move to `## Closed` in `project-init`; the same in `ALGORITHM.md` and section 4 of `global/AGENTS.md`; rows in `test_next_up` of `tests/test_skill_commands.py`; proven by `python3 tests/test_skill_commands.py`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate waiting-readers` and archive the change with `solo-sdd archive waiting-readers --yes`
