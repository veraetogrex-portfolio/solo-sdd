# Proposal

## Why

The `Tests` row of `AGENTS.md` names a bare `python3`. On the owner's machine (checked 2026-11-18) `python3` on `PATH` is Homebrew Python 3.15.2 at `/opt/homebrew/bin/python3`, and it has no `hypothesis`. Every orchestrator of the settings-* run (2026-11-17, ten changes) had to find that out from failing test files and switch to `/usr/bin/python3` by hand. `tests/run.py` starts every file anyway, so a missing module looks like 11 broken test files instead of one missing install.

## What Changes

- `python3 tests/run.py` checks, before any file runs, that every module the selected test files import at top level can be found by its own interpreter.
- A missing one ends the run with code 2 and a line naming the module, the test files that import it, the interpreter path (`sys.executable`) and the `Install` row command of `AGENTS.md`. No test file runs.
- The list of modules comes from the selected test files themselves, not from a list kept in `run.py`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `test-runner`: ADDED requirement Test imports found before the run.

## Impact

- `tests/run.py`
- `tests/test_runner.py`
- `tests/stands/test-runner-deps-check.py`

## Out of Scope

- The `Lint` row and `pyflakes`: lint is its own CI step and its own command.
- Changing the `Tests` row to a pinned interpreter path: the row stays portable across machines.
- Installing the missing module: the runner names the command, the person or agent runs it.
- Neighbouring changes of this plan: `dispatched-status-self-check`, `fix-settings-entry-scroll`, `fix-worktree-ignored-overwrite`, `fix-ci-wait-unread-checks`, `fix-stop-gate-worktree-config`, `fix-setup-links-exclude`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create a change" (on the follow-up list after the settings-* run, item: the `Tests` row names a bare `python3` that can resolve to an interpreter without the test dependencies)
