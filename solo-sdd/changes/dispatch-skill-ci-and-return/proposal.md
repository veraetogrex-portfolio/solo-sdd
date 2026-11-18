# Proposal

## Why

Two gaps in the skill text the dispatcher and `ship` follow, found by the reviewers of the 2026-11-18 run (read in code the same day).

1. `sdd-pr.py wait` prints `CI: infra` with `checks not read: <gh error>` when `gh pr checks` keeps failing (`global/sdd_pr.py:889`-`892`, added by fix-ci-wait-unread-checks). The skills offer only reruns for `infra`: `skills/ship/SKILL.md:27` says "rerun the failed run, repeat `wait`", and `skills/spec-dispatch/merge.md:40` says "one rerun without edits: `gh run rerun --failed <run>`". Line 42 adds the empty commit for "required check did not start". Neither fits an unread check list: there is no failed run, and an empty commit does not fix gh.
2. The Return on conflict message (`skills/spec-dispatch/merge.md:46`) tells the orchestrator to run `git -C <WORKTREE> merge <main branch>`. A merge overwrites a git-ignored WORKTREE file that the main branch now tracks, without a word. The guards of fix-worktree-ignored-overwrite cover only `ship`'s own merge and `land-local`'s rebase (`untracked_written` in `global/sdd_pr.py` and its copy in `global/sdd_dispatch.py`). Its archive names this command as out of scope. git has no native guard here: `git merge --no-overwrite-ignore` refuses only a fast-forward; when the branch has its own commits (the usual case for a change branch) the merge still replaces the ignored file, code 0 (probed with git 2.54 on 2026-11-18, `ort` and `resolve` strategies alike).

## What Changes

- `skills/ship/SKILL.md` and `skills/spec-dispatch/merge.md` give `CI: infra` with `checks not read: <error>` its own step. The agent fixes gh (auth, network), runs `wait` again, and does not rerun CI or push an empty commit. If gh still cannot read the checks, the change is "not merged: PR" with the gh error.
- A new read-only command `sdd-pr.py overwrites <WORKTREE> <ref>` runs the existing `untracked_written` guard: no output and code 0 when merging `<ref>` writes over no untracked WORKTREE file, otherwise code 1 with `merge would overwrite ignored files in WORKTREE: <paths>` (or the failed git step).
- The Return on conflict message runs that command before its `git -C <WORKTREE> merge <main branch>` (in `pr` mode, `origin/<main>`); a non-zero code means no merge, and the orchestrator hands back `not_ready` with the printed line in `NOTES`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `spec-dispatch`: ADDED requirements Unread checks in CI wait and Return keeps worktree ignored files.
- `pr-tool`: ADDED requirement Overwrite check command.

## Impact

- `skills/ship/SKILL.md`
- `skills/spec-dispatch/merge.md`
- `global/sdd_pr.py`
- `tests/test_sdd_pr.py`
- `tests/test_skill_commands.py`
- `tests/stands/dispatch-skill-ci-and-return.py`

## Out of Scope

- `ship`'s own merge in `global/sdd_pr.py`: already guarded by fix-worktree-ignored-overwrite.
- `git merge --no-overwrite-ignore`: rejected, it does not refuse a non-fast-forward merge (see Why).
- The `/ship` skill's own `git merge origin/<main branch>` on `merge` code 5 (`skills/ship/SKILL.md`, step of the merge codes): the same overwrite class in the session's working folder; a separate change.
- The other `infra` lines (`no checks`, `timeout: checks did not finish`): they keep the rerun step.
- Neighbouring changes of this plan: `fix-venv-exclude-line`, `fix-stop-gates-ignored-config`, `fix-settings-fit-zero-width`.

## Depends On

none

## Source

The owner, 2026-11-18 (translated from Russian): "Yes, create them" (on the list of new review findings after the 2026-11-18 dispatcher run, item: ship and spec-dispatch have no step for `checks not read`; the Return on conflict merge can overwrite an ignored file)
