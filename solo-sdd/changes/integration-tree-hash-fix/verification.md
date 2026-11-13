## Live Scenario

1. On the current code, `python3 -m unittest test_integration_run.RecordReuse` from `tests/` → the new row of the scenario An edit in the second of the index write fails: no new record.
2. After the fix → `OK`, and `python3 scripts/sync_blocks.py --check` exits 0.
3. The PR on the public repository → the `test` workflow on Ubuntu is green.

## Needs

none

## Fallback

none needed

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
