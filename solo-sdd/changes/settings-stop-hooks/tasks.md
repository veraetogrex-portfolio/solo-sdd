## 1. Implementation

- [x] 1.1 Rows in `tests/test_settings.py` named after Stop gate switches and Interface settings: the seven keys with type, default and groups `hooks` and `ui`, `config describe` naming extensions and whole numbers, `html`, `.a b` and `wide` refused with exit 1 and the file unchanged; they fail first; then the keys in the settings block with `ABOUT` lines and `GROUPS`, `python3 scripts/sync_blocks.py --check` empty; the rows pass
- [x] 1.2 Rows in `tests/test_work_hooks.py` named after Stop gate switches: each gate off, the open PR gate off under `delivery.merge-by: human` with its switch `on`, edits in a second repository read by that repository's settings, auto-claim off with a foreign `CLAIM` and a `WAITING` still refused, a broken config keeping the gates; they fail first
- [x] 1.3 `global/work_hooks.py` reads each switch from the settings of the repository its gate checks (each edited root, the change's repository, the session's repository for the open PR); the rows of 1.2 pass, the existing stop tests keep every assertion
- [x] 1.4 Rows in `tests/test_work_hooks.py` named after Interface settings: a project extension counts; then the hook takes `ui.extensions`; the rows pass
- [x] 1.5 `skills/ui-check/SKILL.md`, `skills/spec-plan/creation.md`, `skills/spec-plan/SKILL.md`, `skills/project-init/SKILL.md` and `ALGORITHM.md` take the widths and extensions through `solo-sdd config get`; rows in `tests/test_skill_commands.py` named after Interface settings: each laid-out text names `ui.widths` (`ui.extensions` in `project-init`) and none keeps a fixed `1280 and 390` or the extension list
- [x] 1.6 `docs/settings.md`, `docs/hooks.md` and `docs/stop-conditions.md` name the switches; `tests/stands/settings-tui.py` gains the rows, every assertion kept; the stand `tests/stands/settings-stop-hooks.py` runs the Live Scenario

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-stop-hooks` and archive the change with `solo-sdd archive settings-stop-hooks --yes`
