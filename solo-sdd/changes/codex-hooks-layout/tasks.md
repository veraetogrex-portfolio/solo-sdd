## 1. Implementation

- [ ] 1.1 `tests/stands/provider-probe.py codex`: the no-op hook trusted in the temporary `CODEX_HOME` the way the owner's real `~/.codex/config.toml` records its trusted hooks; the probe prints the version or `hooks: unverified` with the reason; a dry run without Codex (`PATH` without `codex`) prints `hooks: unverified` and names the missing command
- [ ] 1.2 Tests named after Install for chosen agents (the modified Hooks without Claude scenario) and Codex hook layout, one per scenario, in `tests/test_providers.py`; they fail on the current code
- [ ] 1.3 The two hook files laid out into `~/.codex/hooks/` for a choice with `codex` and `--hooks` (`targets.json`, `solo_sdd/layout.py`), foreign copies kept by the existing rule; the tests of 1.2 for files pass
- [ ] 1.4 `~/.codex/hooks.json` entries written by `solo_sdd/hooks.py`: one per event, foreign entries kept, a backup before a rewrite, the matcher the same as the hand-made `~/.codex/hooks.json` on this computer, a broken `hooks.json` refused before any write, the entries removed when `codex` leaves the choice; a Hypothesis test named after Codex hook layout: for any `hooks.json` (empty, foreign entries, stale or doubled solo-sdd entries) writing twice equals writing once, one solo-sdd entry per event, foreign entries unchanged and in order; a mutant that appends without removing the old entries fails it; the tests of 1.2 for entries pass
- [ ] 1.5 A test named after Codex hook layout (A translation in Codex) with a Codex transcript fixture copied from the format of a real rollout file here; then the last user message read from a Codex transcript in `global/work_hooks.py`; `python3 tests/test_work_hooks.py` passes
- [ ] 1.6 `solo_sdd/doctor.py` prints `ok agent codex` with hooks once laid out; `docs/agents.md` and `docs/hooks.md` name the Codex hooks and the trust step; `python3 tests/test_cli.py` passes
- [ ] 1.7 `tests/stands/codex-hooks.py` for step 2 of the Live Scenario; it prints `codex-hooks: <n> of <n> checks passed`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate codex-hooks-layout` and archive the change with `solo-sdd archive codex-hooks-layout --yes`
