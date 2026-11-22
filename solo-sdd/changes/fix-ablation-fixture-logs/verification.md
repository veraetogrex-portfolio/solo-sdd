## Live Scenario

Tasks 1.1-1.3 are committed on the change branch first; that commit's hash `<C>` is recorded in `Result`. Steps 1, 2 and 4 run in a detached worktree of it (`git worktree add --detach <tmp>/wt <C>`), which holds only what git tracks, so no git-ignored file of the working folder takes part. On `main` at b02d433 steps 1-3 give the error; after the fix, the expected result.

1. `git -C <tmp>/wt ls-files tests/stands/skill-ablation/debug-profile/dp-service/fixture` → `README.md`, `config.yaml`, `deploy.txt`, `logs/fetch.log`, `logs/load.log`, `logs/transform.log` (before: the first three only).
2. In `<tmp>/wt`: `python3 tests/stands/skill-ablation.py prepare debug-profile --budget 6` → each `dp-service` work folder has `logs/` whose last lines end with `fetch: read 120 orders of 2026-11`, `transform: kept 0 of 120 rows (period 2025-11)` and `load: wrote 0 rows to sales` (before: no `logs/`); then `python3 tests/stands/skill-ablation.py remove <run>`.
3. In the working folder: a file `tests/stands/skill-ablation/debug-profile/dp-service/fixture/probe.txt` added and not tracked → `python3 -m unittest test_skill_ablation.TaskSets.test_the_sets` from `tests/` fails with `task set debug-profile/dp-service: fixture file not tracked by git: probe.txt` (before the fix: passes); the file removed → passes.
4. In `<tmp>/wt`: `python3 tests/stands/skill-ablation/stand.py` → `skill-ablation stand: N of N checks passed`, the same N on both sides; then `git worktree remove --force <tmp>/wt`.

## Needs

none: no model run. The three `dp-service` subagent runs on the fixture with its logs are already recorded (2026-11-22, `docs/skills-audit.md`).

## Fallback

Not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->
