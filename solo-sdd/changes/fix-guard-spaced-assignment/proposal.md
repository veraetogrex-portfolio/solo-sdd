# Proposal

## Why

The history guard and the merge guard let a forced push and a direct merge through when an assignment with a spaced command substitution stands before the program.

Reproduction (2026-11-27, `/usr/bin/python3`, the module loaded from `global/work_hooks.py`): `git_history_runs(command_text(c), c)` for `c = "TS=$(date +%s) git push -f"` → expected `True` (refused, as `git push -f` and `TS=$(date) git push -f` are) → got `False`; `gh_merges(command_text("TS=$(date +%s) gh pr merge 5"))` → `False`. Found by the orchestrator of `history-guard` (PR #108) as a pre-existing gap of both guards.

Cause: `shell_words` keeps `TS=$(date +%s)` as one word, but `gh_merges` splits every kept word again with `split_words` (`raw = [x for y in kept for x in split_words(y)]`, `global/work_hooks.py:2680`), which cuts it at the space into `TS=$(date` and `+%s)`; the assignment rule (`:2683`) then turns only the first piece into `A=x`, so `cmd_start` takes `+%s` for the program and `git` and `gh` are never read. `git_history_runs` (`:2773`) reads through the same `gh_merges`, so every program family after such an assignment passes: wrappers, `-C`, a `+` refspec, a hard reset, `bash -c`, the API merge (all verified on main 4ec331e by the analysis).

## What Changes

- A command whose program follows an assignment holding a command substitution with a space but no `;`, `|` or `&` inside (`$(…)` or a backquote) is read with that program: every forced push, hard reset and direct merge form refused in its plain form is refused after `TS=$(date +%s) `, and an unclosed substitution or quote in the assignment is refused as Broken input. An assignment with a quoted spaced value (`FOO="a b" git push -f`) is already refused and stays so.

## Capabilities

### New Capabilities

### Modified Capabilities
- `history-guard`: requirement Forced push refused gains the scenario An assignment with a spaced substitution.
- `work-hooks-subagents`: requirement Direct merge refused in a process tree gains the scenario An assignment with a spaced substitution.

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`

## Out of Scope

- A substitution holding a separator in the assignment (`TS=$(date | cat) git push -f`, `TS=$(date;echo) git push -f`): there `split_cmd` cuts the command at the separator, a cause in another function; a change of its own.
- `A=(1 2) FOO='a b' gh pr merge 5`, pinned by Known bypasses of the merge guard (`KNOWN_MERGE_BYPASSES`): it stays a known bypass.
- A guard refusing a text argument that only names a forced push in a form its reader cannot follow (`printf` text holding backslashes and `push --force`, seen on 2026-11-26): by design under Known bypasses of the history guard (A known false refusal), not changed.
- `fix-env-word-backtrack` and `fix-pipe-walk-compound` (another session) also edit `global/work_hooks.py`; the dispatcher runs them one at a time.

## Depends On

fix-pipe-walk-compound

## Source

The owner, 2026-11-27: `/spec-plan`, given right after the dispatcher report that named this open item (translated from Russian): "`TS=$(date +%s) git push -f` passes the guard".
