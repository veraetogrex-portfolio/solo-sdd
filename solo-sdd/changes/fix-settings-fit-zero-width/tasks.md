## 1. Implementation

- [ ] 1.1 Requirement Safe display, scenarios Zero-width marks and An emoji with a presentation selector: rows in `tests/test_settings_ui.py::test_sizes_and_wide_characters` for `fit("กั"*5, 5)` (all 10 characters kept), `fit("\u2764\ufe0f"*3, 6)` (6 kept, as now: it guards the selector rule) and a screen drawn at 80 columns whose `delivery.deploy` value holds Thai text, its line holding the whole value; the Thai rows fail on the current code; the draw row does not use the file's `columns()` helper, which counts a mark as one column
- [ ] 1.2 Remove the cause at `solo_sdd/settings_ui.py:43`: width 0 for `unicodedata.category(c)` in `Mn`, `Me` except U+FE0F and for U+1160-11FF, keeping the wide and combining rules; proven by 1.1, `python3 tests/test_settings_ui.py` and `python3 tests/stands/settings-tui.py`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-settings-fit-zero-width` and archive the change with `solo-sdd archive fix-settings-fit-zero-width --yes`
