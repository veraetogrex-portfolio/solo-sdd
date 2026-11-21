## 1. Fix

- [ ] 1.1 `test_background_agents_still_running` in `tests/test_work_hooks.py` gets rows for the scenarios of `Stop waits for background agents`, a new `session_id` per row: a running `shell` (with `command`) and a running `monitor` alone return the uncommitted edits block; `shell` first then `subagent`, a `teammate`, an unknown type `x` and an entry without `type` stay silent; the `subagent` and `completed` rows stay. The `shell` and `monitor` rows fail on the current code, the others pass on it and guard the kept behaviour (`python3 tests/test_work_hooks.py`)
- [ ] 1.2 `cmd_stop` in `global/work_hooks.py` returns early only on a running entry whose `type` is not `shell` or `monitor` (no `type`: counts); 1.1 passes, then `python3 tests/run.py --jobs 5 --affected global/work_hooks.py`, `python3 tests/run.py --jobs 5 --tier slow` and the lint row of `AGENTS.md` without output
- [ ] 1.3 The `stop` row of `docs/hooks.md` says only running tasks other than `shell` and `monitor` keep it silent; `python3 sync.py status` without unexpected `drift`; `python3 sync.py push` is the delivery's step after merge (`Deploy: no` of `AGENTS.md`), recorded in Not Verified with the `--deployed` stand call

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-stop-background-shell` and archive the change with `solo-sdd archive fix-stop-background-shell --yes`
