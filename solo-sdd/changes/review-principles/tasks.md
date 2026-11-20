## 1. Implementation

- [ ] 1.1 Requirements Review rules from the owner's feedback, Only the owner's remarks and Unconfirmed patterns kept apart: write `skills/review-principles/SKILL.md` (the sources, the owner login and owner lines, skipped remarks counted, a failed or missing source named, at most 25 rules with one or two links, the `## Unconfirmed` section) and `templates/REVIEW.md`, with `targets.json` entries; proven by `python3 tests/test_skill_commands.py` (the size budget) and `python3 sync.py status`
- [ ] 1.2 Requirement Reviewer match measured: the parallel mode section of the skill (K, the `agent-quality` set, the two `Review:` variants, the table); proven by step 5 of the Live Scenario
- [ ] 1.3 Requirement Review rounds: `skills/spec-next/acceptance.md` hands the reviewer `REVIEW.md` without its `## Unconfirmed` section; a row in the laid-out skill text test of `tests/test_skill_commands.py` for that line; proven by `python3 tests/test_skill_commands.py`
- [ ] 1.4 List `/review-principles` in section 14 of `global/AGENTS.md`, the README table and `docs/layout.md`, and add its section to `docs/skills-audit.md`; proven by `python3 tests/test_skill_commands.py` (the audit table test) and `python3 tests/test_repo_language.py`
- [ ] 1.5 Build the fixture `tests/stands/review-principles/` (the project, the fake `gh` with a failing mode, the archived changes, the diff) and `tests/stands/review-principles.py` with `--grade`, `--grade-review` and `--grade-table`; proven by each on reference outputs giving every check right and by `--grade` on an empty `REVIEW.md` giving `rules 0 of 3`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate review-principles` and archive the change with `solo-sdd archive review-principles --yes`
