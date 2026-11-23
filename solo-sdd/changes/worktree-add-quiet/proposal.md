# Proposal

## Why

The `guard` hook refuses `git worktree add -q …` with "git worktree add refused: option -q", because its plain form (`WT_PLAIN` and the options loop of `wt_plain_problem` in `global/work_hooks.py`) knows only `-b`, `-B`, `--detach` and `-f`. In the week 16-22.11.2026 five Codex sessions hit it (16.11 …2c6d96, 17.11 …ec727e, 20.11 …6c04d1, 21.11 …0674ba and …e150d8), and each time the agent rewrote the command and ran it again. `-q` / `--quiet` only silences git's progress output and does not move the path, so refusing it guards nothing. Reproduced on 2026-11-23: `git worktree add -q "$TMPDIR/wt-x" -b x main` and `git worktree add --quiet /tmp/wt-q` are refused naming the option.

## What Changes

- The plain form of `git worktree add` takes `-q` and `--quiet` anywhere among its options: `git worktree add [-q | --quiet] [-b <name> | -B <name> | --detach | -f] <path> [<commit>]`; the refusal text (`WT_PLAIN`) and the plain form in `docs/hooks.md` name the same form.
- Every other check of the plain form stays: a path with a variable other than the allowed prefixes, an unknown option, a clustered option and a path outside the temporary folder are still refused.

## Capabilities

### New Capabilities

### Modified Capabilities
- `command-guards`: MODIFIED requirement Worktree add by shell words.

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `docs/hooks.md`
- `tests/stands/worktree-guard-words.py`

## Out of Scope

- Other `git worktree add` options (`--lock`, `--reason`, `--track`, `--orphan`, `-c` clusters): no refusal of them was seen in the week's sessions.
- Neighbouring changes of this plan: `action-first-project-repo`, `fix-env-dump-text-words`, `plan-input-skill`.

## Depends On

none

## Source

The owner, 2026-11-23, on the decisions of the weekly review of 16-22.11 (translated from Russian): "all except the proxy, yes", then "do it". Item C of the owner's input file "2026-11-23 input for spec-plan" (name translated): "the `git worktree add` hook: let `-q` / `--quiet` through".
