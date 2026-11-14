## 1. Hooks off alone

- [ ] 1.1 Requirement Uninstall hooks only: rows in `tests/test_cli.py` for connected hooks, a person's hook kept, the depth variable set by a person kept, copies kept, broken settings (no write, `_hooks` kept), nothing connected (no write); proof: they fail before 1.2
- [ ] 1.2 `solo-sdd uninstall --hooks` in `solo_sdd/cli.py` through the restore steps of `solo_sdd/hooks.py`, the command list line, `docs/cli.md` and `docs/hooks.md`; proof: the 1.1 rows green

## 2. Machine section

- [ ] 2.1 Requirement Machine section: rows in `tests/test_settings_ui.py` with a temporary home for a fresh deployment, hooks on, global rules on, a drift copy, `doctor` warn and fail lines, a folder without `solo-sdd/`; proof: they fail before 2.2
- [ ] 2.2 The Machine section in `solo_sdd/settings_ui.py`, reading the state, `layout` and the `doctor` rows without printing them, the `doctor` rows computed once when the section opens and again on a refresh key, never on a redraw; proof: the 2.1 rows green
- [ ] 2.3 Requirement Apply machine edits: rows for narrowing the agents, hooks on, hooks off, global rules on and off, hooks without `claude`, a cancelled apply; proof: they fail before 2.4
- [ ] 2.4 The apply step: the command list with the changed folders, the confirmation, the in-process calls of `install` and `uninstall` with their output captured, `docs/settings.md` names the section; proof: the 2.3 rows green
- [ ] 2.5 The stand `tests/stands/settings-tui-home.py` drives step 2 of the Live Scenario through `pty` in a temporary `HOME`; `tests/affected.json` maps it; proof: one PASS line per row and `SUMMARY: all rows passed`

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate settings-tui-home` and archive the change with `solo-sdd archive settings-tui-home --yes`
