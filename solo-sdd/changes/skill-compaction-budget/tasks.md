## 1. Implementation

- [ ] 1.1 Requirement Skill size budget: a test in `tests/test_skill_commands.py` over the `SKILL.md` files git tracks (the same file list as the Line length test of `tests/test_readme.py`), rows for 16,001 bytes, exactly 16,000 bytes and an untracked 40,000-byte skill; fails on the current tree naming `skills/spec-dispatch/SKILL.md`
- [ ] 1.2 Requirement Step files: a test in `tests/test_skill_commands.py`, rows for a missing named file and an orphan `.md` file in a temporary skills folder; `python3 tests/test_skill_commands.py` passes the rows
- [ ] 1.3 Split `skills/spec-dispatch/SKILL.md`: the bodies of the long steps (step 7 merge, the orchestrator prompt, the decisions, the report form, and others until the file fits) into step files of `skills/spec-dispatch/`; each step line names its file and says to read it each time the step starts; the tests of 1.1 and 1.2 pass for this skill
- [ ] 1.4 Split `skills/spec-next/SKILL.md` and `skills/spec-plan/SKILL.md` the same way until each is at most 16,000 bytes; the tests of 1.1 and 1.2 pass
- [ ] 1.5 `targets.json`: one entry per step file that deploys it next to its skill's `SKILL.md` in every root of that skill; `python3 tests/test_sync.py` passes and `python3 sync.py status` lists the new files
- [ ] 1.6 The tests that read a split skill's text for a rule (`tests/test_sdd_dispatch.py`, `tests/test_sdd_dispatch_plan.py`, `tests/test_skill_commands.py`, `tests/test_readme.py`) read the `SKILL.md` joined with its step files, keeping every assertion; requirement Line length: the file list of `tests/test_readme.py` adds `skills/*/*.md` with a row for a 700-character line in a step file; each passes
- [ ] 1.7 The stand `tests/stands/skill-compaction-budget.py` for steps 1-4 of the Live Scenario; `README.md` and the project map of `AGENTS.md` name step files next to `SKILL.md`; then the `Tests` row and the lint pass

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate skill-compaction-budget` and archive the change with `solo-sdd archive skill-compaction-budget --yes`
