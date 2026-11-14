## 1. Model

- [ ] 1.1 Requirement Edit by type: tests in `tests/test_settings_ui.py` that feed key sequences to the screen model with rows for a choice, a wrong and a right number, checkboxes, a branch text, a path list and reset; proof: they fail before 1.2
- [ ] 1.2 The screen model in `solo_sdd/settings_ui.py`: state, key handling and drawing into a list of lines for a width and height, values checked by `settings.check_value`; proof: the 1.1 tests green
- [ ] 1.3 Requirement Save only edited lines: a property test (Hypothesis, `max_examples=200`, the same number in the test) over generated config texts with comments, blank lines and `\r\n` and random edit sets: after save every line of an unedited key and every comment keeps its bytes, and the result parses to the edited values; plus rows for changed on disk and quit with unsaved edits; proof: the property test fails when save rewrites the whole file, and its generator reaches an empty file and a file of comments only
- [ ] 1.4 Requirements Broken config read-only and Safe display: rows for a broken line, an ESC and other control characters in a comment and a value, a 30-column and a 40x12 screen, a long value cut at the width; proof: they fail before the code, then green

## 2. Command

- [ ] 2.1 Requirement Settings screen: the `curses` loop around the model and `solo-sdd settings [folder]` in `solo_sdd/cli.py` with the refusals for no terminal, a terminal `curses` cannot start (`TERM=dumb`, an unknown `TERM`) and no tree, the command list line, `docs/cli.md` and `docs/settings.md`; `tests/affected.json` maps the new files; proof: rows for the refusals in `tests/test_settings_ui.py` green
- [ ] 2.2 The stand `tests/stands/settings-tui.py` drives `solo-sdd settings` through `pty` with the rows of the Live Scenario at 120x40 and 40x12, with and without `NO_COLOR`; proof: it prints one PASS line per row and `SUMMARY: all rows passed`

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate settings-tui` and archive the change with `solo-sdd archive settings-tui --yes`
