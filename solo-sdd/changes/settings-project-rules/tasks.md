## 1. Implementation

- [ ] 1.1 Rows in `tests/test_settings.py` named after Project rules in config, Project lines as the old source and Config command: the four keys with group `process`, a bad language code refused, the `project.md` lines as source `project.md`, a final dot dropped, the file value winning with `project.md` unchanged, `Mode: staging` left out and named on stderr; the value strategies of the Config command property gain the four keys; they fail first
- [ ] 1.2 The keys, the language code kind and the `project.md` source in the settings block of `solo_sdd/settings.py` with `ABOUT` lines; `python3 scripts/sync_blocks.py --check` empty; the rows of 1.1 pass, the existing settings tests keep every assertion
- [ ] 1.3 `global/AGENTS.md` sections 11 and 15, `ALGORITHM.md`, `skills/project-init/SKILL.md`, `skills/spec-plan/SKILL.md` and `templates/solo-sdd/project.md` name the keys, the file value over the `project.md` line, the `Lesson (not written)` line for `lessons.write: off`, the prose language with format words in English, and the rule that an agent changes the four keys only on the owner's words; rows in `tests/test_skill_commands.py` fail first and then pass
- [ ] 1.4 `docs/settings.md` rows; `tests/stands/settings-tui.py` gains the rows, every assertion kept; the stand `tests/stands/settings-project-rules.py` runs steps 1-3 of the Live Scenario

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-project-rules` and archive the change with `solo-sdd archive settings-project-rules --yes`
