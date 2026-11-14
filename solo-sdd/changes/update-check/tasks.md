## 1. Check

- [ ] 1.1 Requirements Version check and Skip and switch off: rows in `tests/test_update_check.py` with the network request replaced at its single boundary for: newer, equal, installed newer, a pre-release answer, a fresh and a stale cache, a timeout, an npm install asking npm, a clone asking nothing, a skipped version and a newer one, the variable and the state switch; proof: they fail before 1.2
- [ ] 1.2 `solo_sdd/update_check.py` (install method from `upgrade_hint` of `solo_sdd/cli.py`, request, cache, skip, switch) and the `version` line of `solo_sdd/doctor.py`; `docs/cli.md` and the README update section name them; proof: the 1.1 rows green
- [ ] 1.3 Requirement Registry answer checked, tests on hostile input in `tests/test_update_check.py`: a body over 1 MB, a truncated body, not JSON, a JSON of another shape, a version with letters, non-ASCII digits, a control character or shell text, a broken cache file; each gives no notice, stores nothing of the answer and shows nothing of it; proof: they fail before the checks are written, then green
- [ ] 1.4 Requirement No network elsewhere: a property test (Hypothesis, `max_examples=60`, the same number in the test; in process through `solo_sdd.cli.main` with a temporary `HOME` and a stale cache) over generated command lines of the command list other than the menu and `doctor`: the request boundary is never called and the cache keeps its bytes; proof: it fails when `main` starts the check for every command, and its generator reaches a bare command with no terminal and an unknown command

## 2. Update

- [ ] 2.1 Requirement Update from the menu: rows in `tests/test_update_check.py` for the notice drawn after the menu, the command and link per install method, cancel, a failed upgrade, success with `install` from the upgraded program and the `init` offer when `doctor` names the rules block as older, the restart request; the commands run through the process boundary only; proof: they fail before 2.2
- [ ] 2.2 The notice, the Update entry and Skip this version in the home menu and the update check switch in the Machine section of `solo_sdd/settings_ui.py`; proof: the 2.1 rows green
- [ ] 2.3 The stand `tests/stands/update-check.py` with the local registry, the two wheels and the fake `uv`, driving the rows of the Live Scenario through `pty`; `tests/affected.json` maps the new files; proof: one PASS line per row and `SUMMARY: all rows passed`

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate update-check` and archive the change with `solo-sdd archive update-check --yes`
