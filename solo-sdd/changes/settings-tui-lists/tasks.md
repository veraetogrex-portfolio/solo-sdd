## 1. Integrations

- [ ] 1.1 Move the enable and disable path of `integrations.run` in `solo_sdd/integrations.py` into a function that returns the exit code and the message lines, and call it from the command; the tests of `tests/test_integrations.py` keep every assertion; proof: `python3 tests/test_integrations.py` green
- [ ] 1.2 Requirements Integrations section and Same result as the command: rows in `tests/test_settings_ui.py` for a bundled one off, a home one on, a project one on, a broken one, a shadowed one, a read-only `AGENTS.md`, and the bytes of `solo-sdd/config` and `AGENTS.md` against the command on a copy; proof: they fail before 1.3
- [ ] 1.3 The Integrations section in `solo_sdd/settings_ui.py`, its save through the 1.1 function, Enter on the raw `integrations` and `integrations.off` keys opening it (Requirement Integration keys through the section, a row in 1.2), `docs/integrations.md` names it; proof: the 1.2 rows green
- [ ] 1.4 Requirement Same result as the command: a property test (Hypothesis, `max_examples=40`, the same number in the test; each example copies a temporary project twice) over generated sets of bundled, home and project integrations, a starting `solo-sdd/config` and a toggle: the screen save and the command leave equal bytes of `solo-sdd/config` and `AGENTS.md`; proof: it fails when the screen writes the config without the rules block, and its generator reaches no integration found, every one enabled and a broken one

## 2. Checklists

- [ ] 2.1 Requirement Checklists section: rows in `tests/test_settings_ui.py` for add, a wrong name, a path with `..`, edit paths, remove, an incomplete pair and a missing file; proof: they fail before 2.2
- [ ] 2.2 The Checklists section in `solo_sdd/settings_ui.py` through the pattern keys of `solo_sdd/settings.py`, `docs/settings.md` names it; proof: the 2.1 rows green
- [ ] 2.3 The stand `tests/stands/settings-tui-lists.py` drives the rows of the Live Scenario through `pty` at 120x40 and 40x12, with and without `NO_COLOR`; `tests/affected.json` maps it; proof: one PASS line per row and `SUMMARY: all rows passed`

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate settings-tui-lists` and archive the change with `solo-sdd archive settings-tui-lists --yes`
