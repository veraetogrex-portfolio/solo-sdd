## 1. Implementation

- [ ] 1.1 Requirement Edit by type, scenario A long text entry: add a row to the text-entry rows of `tests/test_settings_ui.py` (near the Text settings rows): `select` `delivery.deploy`, `press` Enter and 150 characters, `draw(80, 24)`; the entry line ends with `_` and the last typed characters. It fails on the current code
- [ ] 1.2 Remove the cause at `solo_sdd/settings_ui.py:706`: build the entry line so that `> `, the visible tail of `shown(self.buffer)` and `_` fit `width - 1` columns (wide characters counted as `fit` counts them); proven by the row of 1.1 and `python3 tests/test_settings_ui.py`
- [ ] 1.3 Add the long-entry step to `tests/stands/settings-tui.py` by the Live Scenario, keeping every earlier assertion; proven by running the stand

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-settings-entry-scroll` and archive the change with `solo-sdd archive fix-settings-entry-scroll --yes`
