## Live Scenario

1. `python3 tests/test_settings_ui.py` → the new rows of `test_sizes_and_wide_characters` draw a screen whose `delivery.deploy` value holds Thai text with zero-width vowel marks: on an 80-column screen the line holds the whole value; on the previous code it is cut early. `fit` keeps three U+2764 U+FE0F pairs in six columns, as before. The file ends with `OK`.
2. `python3 tests/stands/settings-tui.py` → the real `solo-sdd settings` in a pseudo-terminal still passes every row, and prints its summary line.

## Needs

none

## Fallback

Not needed: the scenario runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: the planned zero width for every Mn mark included U+FE0F; probed: U+2764 U+FE0F counts two columns now and would count one, while a terminal draws it two wide, so the line would run past the screen and break the layout the requirement keeps → U+FE0F keeps one column, and a scenario pins it; the scenario with "a letter with a variation selector" was dropped, the count it promised is not the terminal's.
- analyze: the rule was probed on Python 3.15 (Unicode 17.0) and 3.9 (13.0): `fit("กั"*5, 5)` keeps 5 characters now and 10 with the rule; the count of affected marks depends on the Unicode data, so the proposal names its version.
- analyze: task 1.1 checked `fit` while the Live Scenario drew a screen → the task has both rows; the test file's `columns()` helper counts a mark as one column, so the draw row checks the value text instead.
