## 1. Entry

- [ ] 1.1 Requirement Entry point (MODIFIED): the terminal check and the call of the menu in `solo_sdd/cli.py`; the existing bare and unknown-command rows of `tests/test_cli.py` keep their assertions (they run without a terminal); proof: `python3 tests/test_cli.py` green and the stand row "home menu in a project" of 2.5

## 2. Menu

- [ ] 2.1 Requirement Home menu: rows in `tests/test_settings_ui.py` for a project header with open changes, the entries, the read-only changes list, a folder without `solo-sdd/`, a folder that is not a git repository (the `init` refusal shown, no write), a folder with only `openspec/` (no write); proof: they fail before 2.2
- [ ] 2.2 The home menu in `solo_sdd/settings_ui.py`, reusing the screens of the settings changes and `process_cli.list_cmd` data; proof: the 2.1 rows green
- [ ] 2.3 Prepare this folder: leave the full screen, run `init.run` with its questions, return to the menu; a row that the written `solo-sdd/config` equals the one of `init --yes` on a copy; proof: the row green
- [ ] 2.4 `docs/cli.md` and the README quick start name the menu; proof: `python3 tests/test_readme.py` green
- [ ] 2.5 The stand `tests/stands/cli-menu.py` drives the rows of the Live Scenario through `pty`; `tests/affected.json` maps it; proof: one PASS line per row and `SUMMARY: all rows passed`

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate cli-menu` and archive the change with `solo-sdd archive cli-menu --yes`
