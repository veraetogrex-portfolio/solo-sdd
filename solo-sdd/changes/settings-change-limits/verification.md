## Live Scenario

1. In a temporary project with a change of 12 tasks: `python3 -m solo_sdd validate <id>` → fails with `too many tasks: 12 > 10 (default)`.
2. `python3 -m solo_sdd config set process.max-tasks 14` → `validate <id>` passes.
3. `process.requirement-max-chars: 300` and a requirement of 400 characters → `validate` fails naming `400 > 300 (file)`.
4. `HOME=<temporary home> python3 sync.py push` → the laid-out `spec-plan`, `spec-analyze` and `spec-next` name the five keys and the `Analyze: off (solo-sdd/config)` line.

Steps 1-3 in one call: `python3 tests/stands/settings-change-limits.py` → `3 of 3 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: main requirements Task list limits and Requirement format (`process-format`), Requirement text length (`spec-plan`), Writing rules in spec-plan (`skill-commands`) and Hostile input analyze finding (`plan-untrusted-input`) name 10, 5 and 500 as fixed numbers, which a set limit contradicts → one sentence in Change size limits reads those numbers as the defaults; five `MODIFIED` copies were rejected: they change no behaviour beyond the number.
- analyze: `process.max-tasks` 1 or 2 would make every change invalid (the `Acceptance` group holds two tasks), and a tiny length limit would refuse every requirement → `config set` refuses a task limit below 3 and a length below 100.
- analyze: a bug fix limit above `process.max-tasks` had no outcome → the smaller limit holds: `validate` checks only `process.max-tasks` anyway.
- analyze: `process.analyze: off` and a raised limit let an agent skip the check before code or grow a change on its own → the skills and `ALGORITHM.md` let an agent change the five keys only on the owner's words in the chat.
- analyze: "after every N archives" did not say which count → the archive folder count after this archive is a multiple of `process.audit-every`, as `spec-next` counts today.
- analyze: a broken `solo-sdd/config` under `validate` had no row → `validate` fails naming the file and line, as Settings file says for every command; a row in task 1.2.
- spec-next analyze: Change size limits makes every limit error name its source, so the two existing exact items `11 > 10` and `Long: 501 > 500` of `tests/test_process_format.py` read ` (default)` after the change, while task 1.3 kept every assertion → task 1.3 names the two items as the only assertions that change; the main `process-format` scenarios name the file and the count, not the text, and stay.
- spec-next analyze: `process.analyze: off` would also skip the dependency check of `spec-next` step 4a → only the `spec-analyze` pass is skipped, the `Depends On` check stays.
