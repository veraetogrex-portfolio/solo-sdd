## 1. Implementation

- [ ] 1.1 Requirement Readers of waiting lines: `skills/context-resume/SKILL.md` (its Blockers line "from `docs/waiting.md` only its first table, the rows under `## Closed` are closed"), `skills/spec-next/SKILL.md` and its `closing.md`, `skills/spec-plan/SKILL.md` and `skills/blockers/SKILL.md` write "in the first table of `docs/waiting.md`"; the same in `ALGORITHM.md`, section 4 of `global/AGENTS.md`, and `templates/docs/waiting.md` names "`project-init` for its own `DESIGN.md` row"; proven for `context-resume` and `blockers` by Live Scenario steps 1 and 2, for the rest by the new rows of `test_next_up` in `tests/test_skill_commands.py`, which fail on the text before this change (`python3 -m unittest test_skill_commands.SkillCommandsTest.test_next_up` from `tests/`)
- [ ] 1.2 Requirement Design file rerun: step 5a of `skills/project-init/SKILL.md` writes its row into the first table and, with no empty fields left, moves it to `## Closed` with the evidence `DESIGN.md: no empty fields` and the date, never deleting it, and a later empty field gets a new row in the first table; the move is proven by Live Scenario step 3, a later empty field and a missing `## Closed` by the `project-init` rows of `test_next_up`
- [ ] 1.3 The stand `tests/stands/waiting-readers.py` (`prepare`, `clean`, `--grade`, `--grade-confined`) with the references `tests/stands/waiting-readers/expected-*.md` and `old-*.md`; proven by Live Scenario step 4

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate waiting-readers` and archive the change with `solo-sdd archive waiting-readers --yes`
