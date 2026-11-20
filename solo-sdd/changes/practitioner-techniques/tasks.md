## 1. Implementation

- [ ] 1.1 Requirement Practitioner list in a new field: add the rule to section 14 of `global/AGENTS.md`, worded without quoting a persona line; a row in the laid-out skill text test of `tests/test_skill_commands.py` that section 14 names the practitioner list; proven by `python3 tests/test_skill_commands.py` and step 2 of the Live Scenario
- [ ] 1.2 Requirement Practitioner list in a plan: add the proposal and task rule to `skills/spec-plan/creation.md`; a row in `tests/test_skill_commands.py` that `creation.md` names it; proven by `python3 tests/test_skill_commands.py` (with the size budget and step files tests) and step 3 of the Live Scenario
- [ ] 1.3 Requirement No persona prompts: a test class `NoPersonaPrompts` in `tests/test_skill_commands.py` over `skills/`, `global/AGENTS.md`, `ALGORITHM.md` and `templates/`, failing with the file and line of a persona and passing a role line; `tests/test_skill_commands.py` in the `templates/` entry of `tests/affected.json`; proven by `python3 tests/test_skill_commands.py` and by its failure on a temporary copy with an added persona line
- [ ] 1.4 Write `tests/stands/practitioner-techniques.py --grade|--grade-plan`; proven by both on reference outputs giving `yes` lines and on an answer without sources giving `list with sources: no`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate practitioner-techniques` and archive the change with `solo-sdd archive practitioner-techniques --yes`
