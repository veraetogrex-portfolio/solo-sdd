## Live Scenario

1. `python3 tests/stands/settings-tui.py` → the stand drives the real `solo-sdd settings` in a pseudo-terminal. A new step opens `delivery.deploy`, types 150 characters on an 80-column screen and reads the screen. The entry line ends with the last typed characters and `_`; on the previous code it ends with the 77th character and no `_`.
2. The stand saves, and `solo-sdd config get delivery.deploy` in its temporary project prints all 150 characters.
3. The stand prints its summary line with every check passed.

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

- analyze: the reproduction said the cut line keeps 76 characters; drawing 150 characters at 80 columns on the current code shows 77 (`fit` keeps `width - 1` = 79 columns, minus `> `) → 77 in the proposal and step 1 — the stand's old-code expectation must match the real cut.
