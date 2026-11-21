## Live Scenario

From the solo-sdd root:

1. `python3 sync.py push`, then `python3 sync.py status` → the laid-out `spec-analyze` and `ALGORITHM.md` match the repository, no unexpected `drift`.
2. `python3 tests/stands/analyze-drift.py prepare new` → prints the temporary project path and the subagent prompt: run `/spec-analyze add-retry` there, edit no file, print the findings table and the report.
3. The lead launches the prompt as an `Agent` subagent of its own session with the description `Analyze: add-retry` and without `model` (never `claude -p`; the tag is allowed from an orchestrator subagent too) and saves its final message to a file.
4. `python3 tests/stands/analyze-drift.py grade <that file>` → `found 3 of 3, false positives 0, retell block: yes`, with the per-hole lines for pass 7 `3`/`5`, pass 7 `process.retry-limit`/`process.retry-max` and pass 1 `docs/retry.md`.
5. `python3 tests/stands/analyze-drift.py prepare base` (the `spec-analyze` text of the base commit `214ff16`, read by `git show`, apart from the working folder), launched and graded the same way → the per-hole lines go into `Result` as is, naming which pass 7 holes the base text already found; acceptance is step 4, the comparison is a record.

## Needs

- Two `Analyze:` subagents in the lead's Claude Code session on the subscription (steps 3 and 5); no `claude -p`, no paid API calls.

## Fallback

Not needed: both runs are subagents of the lead session. A subagent that fails or is stopped is named in `Not Verified` with the commands to repeat.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- plan: the retell and the value check are lines of existing passes 1 and 7, not new pass numbers → the attacker groups of `analyze-outside` (1, 2, 3, 3a; 4, 4a; 5, 6, 7, 7a, 7b) need no edit.
- plan: no separate `Retell:` subagent → its clean context is what `analyze-outside` gives every pass; a new role tag would need a hook change for one block of output.
- analyze: the retell assumes a reader who has not seen the proposal → `analyze-outside` goes into `Depends On` instead of a retell the author writes in its own session; the group-1 attacker returns the block and the judge passes it unchanged.
- analyze: one condition, a backquoted task value differing from its requirement, had two levels (pass 5 term drift MEDIUM, pass 7 HIGH) → reported once, under pass 7, HIGH; pass 5 keeps prose terms.
- analyze: `grade` reads a file the lead saves, not foreign input, but a failed read must never look like `found 0 of 3` → task 1.4 tests broken input anyway.
