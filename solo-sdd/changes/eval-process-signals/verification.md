## Live Scenario

The committed fixtures hold only journals in the form Claude Code writes them: `tests/eval/fixtures/signals/` has, for two copies, the dispatcher session journal, the orchestrator and subagent journals with their `.meta.json` files, and the copy's archived `verification.md`. `honest`: a review after the last code edit, then a `tasks.md` edit, an `Analyze:` line, a `LIVE` command of its Live Scenario. `guess`: a code edit after the last review, a `LIVE` command outside the Live Scenario, no `Analyze:` line. `tests/stands/eval-process-signals.py` builds the copies as git projects with their oracle commits and the four run logs `r1` to `r4` in a temporary folder (as the `compare` tests build them), lays the journals into a temporary HOME under `.claude/projects/` and runs the real `global/sdd_eval.py` there.

1. The stand runs `sdd_eval.py metrics <tmp> --label r1` → exit 0; `runs/r1.metrics.json` holds for `honest` `review_after_last_edit: true`, `review_rounds: 2`, `important: 1`, `live_in_scenario: true`, `analyze_findings: 6`, and for `guess` `review_after_last_edit: false`, `live_in_scenario: false`, `analyze_findings: null`; the role count of `honest` holds `lookup: 1`, `attack: 1`, `judge: 1`, `check: 1`.
2. The stand runs `sdd_eval.py compare <tmp> --a r1 r2 --b r3 r4` → the report table shows `done` for `honest` and `done, path incomplete` for `guess`.
3. The stand removes the `honest` orchestrator journal and runs both again → `honest` has `null` signals and `done, path unknown`.
4. The stand prints `eval-process-signals: 3 of 3 checks passed`; nothing is written into the tracked tree.

## Needs

none

## Fallback

Not needed: the fixtures are local, no replay run and no model call.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: order against `goal-first` and `practitioner-techniques`, which also edit `tests/affected.json` → `practitioner-techniques` in Depends On; the plan's chain is linear from here.
