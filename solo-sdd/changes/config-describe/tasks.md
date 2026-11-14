## 1. Descriptions

- [ ] 1.1 Requirement Key descriptions: a test in `tests/test_settings.py` that every registry key and every pattern has a group and a description (the existing `Readme` test already keeps the `docs/settings.md` table on the registry keys); proof: it fails before 1.2
- [ ] 1.2 Add the group and description of every key to `solo_sdd/settings.py` outside the `settings:begin`/`settings:end` block (so `scripts/sync_blocks.py` copies nothing new); proof: the 1.1 test and `python3 tests/test_settings.py` green

## 2. Command

- [ ] 2.1 Requirement Describe a setting: tests in `tests/test_settings.py` with rows for one key, all keys, a team default, an `AGENTS.md` source, the patterns and a pattern key set in the file, `list --json`, an unknown key and a broken file; proof: they fail before 2.2
- [ ] 2.2 `config describe [<key>]` and `config list --json` in `solo_sdd/settings.py`, the `config` line of the command list in `solo_sdd/cli.py`, `docs/settings.md` and `docs/cli.md` name them, `tests/affected.json` keeps its keys; proof: the 2.1 tests green, plain `config list` output unchanged in the existing tests

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate config-describe` and archive the change with `solo-sdd archive config-describe --yes`
