## Why

Reproduction: on a checkout of `main` at b02d433, `python3 tests/stands/skill-ablation.py prepare debug-profile --budget 6` and the three `dp-service` prompts run as subagents → expected: the work folder holds the import service's logs the task names, and the full variant can pass → got: the work folder has only `README.md`, `config.yaml` and `deploy.txt`, every agent reports that `logs/` does not exist, and `grade` gives `fail` for all three variants (`compare: full 1 of 2, cut 1 of 2, none 1 of 2`, run of 2026-11-22).

Cause: `.gitignore:26` holds `*.log`, so `tests/stands/skill-ablation/debug-profile/dp-service/fixture/logs/fetch.log`, `transform.log` and `load.log`, written by the change `skill-ablation`, never reached git; its stand passed only in the worktree that still held them. `task_errors` in `tests/stands/skill-ablation.py:369` checks the files of a task folder but never whether git tracks the fixture's files.

## What Changes

- `.gitignore` keeps `*.log` and re-includes only `*.log` under a stand's `fixture/`; `.env`, `.DS_Store` and every other ignore rule keep applying there.
- The three `dp-service` logs are committed with the contents the reference transcript and the task expect.
- `task_errors` reports every file under a task's `fixture/` that git does not track, and one error line for a root outside git or a failed git call.
- The lesson of this bug refines the `ignored-paths` line of `## Lessons` and its text in `LESSONS.md`.

## Capabilities

### New Capabilities

### Modified Capabilities

- skill-ablation

## Impact

- `.gitignore`
- `tests/stands/skill-ablation/debug-profile/dp-service/fixture/logs/fetch.log`
- `tests/stands/skill-ablation/debug-profile/dp-service/fixture/logs/transform.log`
- `tests/stands/skill-ablation/debug-profile/dp-service/fixture/logs/load.log`
- `tests/stands/skill-ablation.py`
- `tests/test_skill_ablation.py`
- `AGENTS.md`
- `LESSONS.md`

## Out of Scope

- A rerun of the `debug-profile` measurement: the run of 2026-11-22 with the logs restored in the working folder is already in `docs/skills-audit.md`.
- Other stands' fixtures: they hold no git-ignored file today; the new check covers them from now on.
- The `*.log` rule for the rest of the repository.
- Empty directories under a fixture: git keeps none, and no fixture needs one today.

## Depends On

none

## Source

The owner, 2026-11-23 (translated from Russian), answering "Make a change to fix the fixture here?": "Yes, do it"
