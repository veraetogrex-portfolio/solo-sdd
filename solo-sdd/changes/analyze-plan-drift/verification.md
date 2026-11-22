## Live Scenario

From the solo-sdd root:

1. `python3 sync.py status` → the edited deployed files (`spec-analyze`, `ALGORITHM.md`) show `outdated` and the new step file `outside-run.md` `missing`, no `drift`; `sync.py push` is left to the delivery after merge.
2. `python3 tests/stands/analyze-drift.py prepare new` → prints `project: <path>` and `prompt: <path>`; the prompt tells an `Analyze:` subagent to run the embedded laid-out `spec-analyze` text of the working folder on `add-retry` there without loading the skill, edit no file and hand back the report.
3. The lead launches an `Agent` subagent of its own session with the description `Analyze: add-retry` and without `model` (never `claude -p`; the tag is allowed from an orchestrator subagent too), telling it to read and follow that prompt file, and saves its final message verbatim to `live-new.md` in this change folder.
4. `python3 tests/stands/analyze-drift.py grade solo-sdd/changes/analyze-plan-drift/live-new.md` → `found 3 of 3, false positives 0, retell block: yes`, with the per-hole lines for pass 7 `3`/`5`, pass 7 `process.retry-limit`/`process.retry-max` and pass 1 `docs/retry.md`; after the archive the same record is graded by `python3 tests/stands/analyze-drift.py grade solo-sdd/changes/archive/2026-11-22-analyze-plan-drift/live-new.md`.
5. `python3 tests/stands/analyze-drift.py prepare base` (the `spec-analyze` text of the base commit `214ff16`, read by `git show`, apart from the working folder), launched the same way, saved to `live-base.md` and graded → the per-hole lines go into `Result` as is, naming which pass 7 holes the base text already found; acceptance is step 4, the comparison is a record.
6. `python3 tests/stands/analyze-drift.py clean <path>` for both projects → `removed <folder>`.

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
- analyze: the same thing for a drifted key was undefined, so the requirement ruled out its own scenario (J1, CRITICAL) → the same thing is known by what both texts say it is for, so a key spelled otherwise names the same setting; the fixture's task and scenario both call their key the retry limit.
- analyze: the `Retell:` block named the author's `spec-next` report as its reader, which has no place for it (J3, HIGH) → the block stands above the findings table of the `spec-analyze` report, the judge reads it to mark the retell findings and gives it to the author; `spec-next` and `spec-plan` stay as they are.
- analyze: the outside-run route of the retell had no check (J2, HIGH) → `test_analyze_plan_drift` asserts the `Outside run` wording; the live run takes the `Analyze:` route only, as three attackers and a judge for one fixture add four subagent runs for the same text.
- analyze: `grade` matched bare digits anywhere and left the retell block undefined (J4, J5) → whole-token matching with every hole token required, the Pass cell by its leading token, and a rule for the block; a pass 5 row on `3` and `5` is a second decoy (part of J6).
- analyze: J6 kept by the judge, not fixed for "Work without a promise", "Retell and proposal agree" and "The requirement is the wrong one" → those are wording of the skill text checked by `test_analyze_plan_drift`; the stand grades the three planted holes, and a fourth MEDIUM hole would change the stand's scope.
- analyze: two group-one attackers would return two blocks (J7) → each block is named by its attacker; the judge's other duties in `analyze-outside` stay unchanged.
- analyze: J10 (hostile input), J11 (a property test for an LLM pass) and J12 (an unnamed test) dropped by the judge; J12's point is still taken, the test is named `test_analyze_plan_drift`.
- analyze repeat: the skill had 662 bytes left of its budget for the new wording (R1, HIGH) → the body of `Outside run` after `Passes in place` moves into the step file `outside-run.md`; pass text stays in `SKILL.md`, which older stands read raw.
- analyze repeat: `grade` ignored the Level column and where the block stands (R2, HIGH) → a hole needs its level in the Level cell, and the block must stand above the first findings table and name no pass 1 hole token.
- analyze repeat: the J6 reason named no assertion (R3) → `test_analyze_plan_drift` names the MEDIUM level, the block kept with no finding and the fix into the delta; stale "open change" wording in the proposal (R4) fixed.
- implementation: `prepare new` embeds the laid-out skill text like `prepare base` → both runs read their text the same way, and step 1 proves the deployed copy equals it.
