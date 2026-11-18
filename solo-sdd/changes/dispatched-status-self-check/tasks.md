## 1. Implementation

- [ ] 1.1 Requirement Status self-check before handback: in the "Under the dispatcher" section of `skills/spec-next/SKILL.md`, next to the status-block item, add the step: write the block to a file outside `WORKTREE`, run `python3 ~/.local/bin/sdd-dispatch.py accept <file>`, correct a stated field from the real output or rework on code 1 or 2, repeat, hand back `archived` only after `status matches`; the `LIVE` text after `->` is one printed line copied verbatim; proven by step 3 of the Live Scenario stand (task 1.3), with no second test of the same text
- [ ] 1.2 Add the same rule as one line of `skills/spec-dispatch/orchestrator-prompt.md`, keeping the skill under its size budget (`tests/skill_text.py`); proven by step 3 of the stand and `python3 tests/test_skill_commands.py` (the size budget)
- [ ] 1.3 Write the stand `tests/stands/dispatched-status-self-check.py` by the Live Scenario (a temporary worktree and archive, both `accept` runs, the skill text check, the summary line); proven by running it

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate dispatched-status-self-check` and archive the change with `solo-sdd archive dispatched-status-self-check --yes`
