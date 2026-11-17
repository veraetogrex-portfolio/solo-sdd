## 1. Implementation

- [x] 1.1 Rows in `tests/test_settings.py`: the five keys with type, default and group `process`, a task limit of 2 and a length of 99 refused; the value strategies of the Config command property gain the five keys from their lower bounds; they fail first; then the keys in the settings block with `ABOUT` lines, `python3 scripts/sync_blocks.py --check` empty; the rows pass
- [x] 1.2 Rows in `tests/test_process_format.py` named after Change size limits: a larger project limit passes, the default names `(default)`, a file limit on requirement length names `(file)`, a broken `solo-sdd/config` fails `validate` with its file and line; they fail first
- [x] 1.3 `solo_sdd/process_format.py` takes both limits from the project's settings instead of `MAX_TASKS` and `MAX_LEN`; the rows of 1.2 pass, the existing validate tests keep every assertion except the two exact items that quote a default limit (`11 > 10`, `Long: 501 > 500`), which gain ` (default)` as Change size limits requires
- [x] 1.4 `skills/spec-plan/SKILL.md`, `skills/spec-plan/creation.md`, `skills/spec-analyze/SKILL.md`, `skills/spec-next/SKILL.md` and `ALGORITHM.md` read the five keys through `solo-sdd config get`, the fixed numbers kept as defaults, and let an agent change them only on the owner's words; rows in `tests/test_skill_commands.py` named after Process cadence settings fail first and then pass
- [ ] 1.5 `docs/settings.md` rows; `tests/stands/settings-tui.py` gains the rows, every assertion kept; the stand `tests/stands/settings-change-limits.py` runs steps 1-3

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-change-limits` and archive the change with `solo-sdd archive settings-change-limits --yes`
