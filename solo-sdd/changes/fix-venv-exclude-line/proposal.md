# Proposal

## Why

Reproduction (review finding of 2026-11-18, read in code the same day):
1. `sdd-worktree.py setup` runs with `MAIN/.venv` and an empty `info/exclude`.
2. Expected by the spec scenario The .venv link is invisible to git: the line `.venv`.
3. Got: `/.venv`. The link stays out of `git status` either way.

Cause: the spec drifted from the code. `global/sdd_worktree.py:757` writes `node_modules` and every other link at its path from the root (`"/" + x`), as `solo-sdd/specs/settings/spec.md` says for `worktree.links` ("another item at its path from the root"). `solo-sdd/specs/worktree-env/spec.md` still says `.venv` in its requirement text and scenario. `tests/test_sdd_worktree.py::test_links_excluded_without_gitignore` checks only the link and an empty `git status`, so neither form is pinned.

## What Changes

- The Worktree venv link requirement and its scenario name the line `/.venv`, as the code writes it.
- The existing test also checks that line, so the spec and the code cannot drift apart again.

## Capabilities

### New Capabilities

### Modified Capabilities
- `worktree-env`: MODIFIED requirement Worktree venv link (the exclusion line is `/.venv`).

## Impact

- `tests/test_sdd_worktree.py`

## Out of Scope

- Changing the code to write `.venv`: the anchored form excludes only the root link, which is the intent.
- An existing unanchored `.venv` line still gets `/.venv` added; harmless and out of this fix.
- Neighbouring changes of this plan: `dispatch-skill-ci-and-return`, `fix-stop-gates-ignored-config`, `fix-settings-fit-zero-width`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create them" (on the list of new review findings after the 2026-11-18 dispatcher run, item: the scenario The .venv link is invisible to git names the line `.venv`, the code writes `/.venv`)
