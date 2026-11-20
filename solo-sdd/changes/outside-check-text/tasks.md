## 1. Implementation

- [ ] 1.1 Requirements Outside fact check before handover and Fact check without a subagent tool: add the `Check:` rule with its bounds, its table form and the in-session case to the analysis and text kinds of done in section 3 of `global/AGENTS.md`, and `Check:` to the subagents of section 10; rows in the laid-out skill text test of `tests/test_skill_commands.py` that section 3 names `Check:`, `confirmed`, `wrong`, `no primary source`, `Not confirmed:` and `Check: in session (no subagent tool)`; proven by `python3 tests/test_skill_commands.py`
- [ ] 1.2 Requirement Fixes and a counter-argument after the check: add the step "Outside check" to `skills/evidence-research/SKILL.md` after step 8, before the answer form, and the `Not confirmed:`, counter-argument and `Check: confirmed <n>, fixed <n>, not confirmed <n>` lines to the answer form, or without a subagent tool `Check: in session (no subagent tool)`; rows in `tests/test_skill_commands.py` for the step and that the answer form names both lines; proven by `python3 tests/test_skill_commands.py` (with the size budget)
- [ ] 1.3 Build `tests/stands/outside-check-text/` (`text.md`, `sources/`, `planted.json`, reference outputs `expected-table.md` and `expected-answer.md`) and `tests/stands/outside-check-text.py --grade|--grade-answer`; proven by both on the reference outputs giving the lines of Live Scenario steps 3-4, by a table with one correct fact marked `wrong` giving `touched correct 1`, and by an answer without `Not confirmed:` giving `not confirmed: no`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate outside-check-text` and archive the change with `solo-sdd archive outside-check-text --yes`
