## 1. Implementation

- [ ] 1.1 Requirements Retry a failed copy and Default retry limit: `tests/test_retry.py` with a test for each scenario, the failing copy made by a `backups/` folder without write permission; check: the new tests fail on the current `backup.py`
- [ ] 1.2 Requirement Default retry limit: `backup.py` tries a failed copy again in a loop, up to the retry limit, default `5` when `backup.json` sets none; check: `python3 -m unittest discover -s tests` passes, the old test included
- [ ] 1.3 `backup.py` reads the retry limit from the key `process.retry-limit` of `backup.json`; check: the scenario "A limit the person set" of `tests/test_retry.py` passes

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate add-retry` and archive the change with `solo-sdd archive add-retry --yes`
