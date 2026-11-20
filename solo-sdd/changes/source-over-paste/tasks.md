## 1. Implementation

- [ ] 1.1 Requirement Read the source of a pasted excerpt: add the rule (how the source is found, the `Based on an excerpt:` line) to section 1 of `global/AGENTS.md`, next to the line on rereading the chat and the project folder; a row in the laid-out skill text test of `tests/test_skill_commands.py` that section 1 names `Based on an excerpt:`; proven by `python3 tests/test_skill_commands.py` and steps 2-4 of the Live Scenario
- [ ] 1.2 Requirement Relay reads the report's source: add the source lookup to step 1 of `skills/relay/SKILL.md`; a row in `tests/test_skill_commands.py` that step 1 names the session log, the change folder and the PR; proven by `python3 tests/test_skill_commands.py` (with the size budget) and step 5 of the Live Scenario
- [ ] 1.3 Build the fixture `tests/stands/source-over-paste/` (the project, the four prompts, reference answers) and `tests/stands/source-over-paste.py --grade-cut|--grade-far|--grade-missing|--grade-relay`; proven by each grade giving `yes` on its reference answer and `no` on an answer without the quoted line, the marker line or the refutation

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate source-over-paste` and archive the change with `solo-sdd archive source-over-paste --yes`
