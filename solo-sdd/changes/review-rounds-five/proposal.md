# Proposal

## Why

Three review rounds are too few for the changes this repository runs, and the owner allows the next round by hand each time. 2026-11-14 the owner wrote "Yes, a 4th round", then "Yes, a 5th round" in one change; 2026-11-12, in another project's run, the agent noted "you allowed the 4th separately". The rounds after the third mostly closed findings on the last fix itself, not on the change. The limit is `process.review-rounds` (default 3) in `skills/spec-next/SKILL.md`, and the main spec still says "at most three rounds".

## What Changes

- `process.review-rounds` defaults to 5: in the settings block of `solo_sdd/settings.py` and its copies, in `docs/settings.md`, in `ALGORITHM.md` and in `spec-next`, whose fallback without a `solo-sdd` command becomes 5 too.
- One extra round runs without asking the owner when the last round is the second or later and every `Important` open after it has all its places in the lines the rework before that round changed (by `git diff` of that rework); after it, or with any other open `Important`, the change is not archived and `Not Verified` gets "reconsider the approach", as now.
- The report names the rounds and whether the extra round ran.

## Capabilities

### New Capabilities

### Modified Capabilities
- `spec-next`: Review rounds is modified (the limit from the setting, default 5); Extra round for fix findings is added.

## Impact

- `solo_sdd/settings.py`, `global/sdd_pr.py`, `global/sdd_dispatch_plan.py`, `global/sdd_worktree.py`, `global/work_hooks.py`
- `skills/spec-next/SKILL.md`, `ALGORITHM.md`, `docs/settings.md`, `docs/stop-conditions.md`
- `tests/test_settings.py`, `tests/test_skill_commands.py`, `tests/stands/settings-tui.py`

## Out of Scope

- A per-change round limit.
- The other items of the same weekly plan: `reply-language-requests`, `codex-hooks-layout`, `dispatch-run-decisions` and the light path edits.

## Depends On

none

## Source

The owner, 2026-11-15, on the weekly review (translated from Russian), on the review rounds (a default of 5, and one extra round on findings of the last fix): "A + B".
