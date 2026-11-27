## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` a temporary git repository with a `solo-sdd/` tree for the merge rows), the way `entry` in `tests/test_work_hooks.py` runs it; an empty answer means the command passes, a `deny` answer prints its reason. The hook only reads the command: nothing is pushed or merged.

The base is main 4ec331e: its hook from a temporary worktree of that commit (`git worktree add --detach "${TMPDIR:-/tmp}/wt-base-4ec331e" 4ec331e`, removed after).

1. On the base, `TS=$(date +%s) git push -f`, `TS=$(date +%s) git reset --hard` and `TS=$(date +%s) gh pr merge 5 --squash` → no answer (all pass).
2. On the branch, the same three commands, `TS=$(date +%s) sudo git push -f` and `TS=$(date +%s git push -f` → `deny`, the merge one naming `sdd-pr.py merge`, the others the forced-push and hard-reset rule.
3. On the branch, `TS=$(date +%s) git push origin main` and `TS=$(date +%s) git commit -m "x"` → no answer.
4. In a Claude Code session after `sync.py push` of the merged change, inside a temporary repository whose `origin` is a local bare repository in the same temporary folder (so a command the hook let through could not reach a real remote): `TS=$(date +%s) git push --force --dry-run origin HEAD:refs/heads/probe-spaced` run through the Bash tool is refused with the forced-push rule; the folder is removed after.

## Needs

none

## Fallback

Step 4 needs the layout after merge (the delivery's step, which agents run without asking): until then steps 1-3 run the hook from the branch by its entry point, and Not Verified names step 4 with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge 12): a backquote substitution holding a space is in scope, as `$(…)` is; a quoted spaced value is out (already refused).
- plan (repeat analyze 5): `TS=$(date +%s) git reset --hard` stays a row of the forced-push scenario, since both forms read through the same `gh_merges` and the shared rule names both a new commit and `git stash`; Hard reset refused is not modified.
- plan (repeat analyze 7): Known bypasses win: `A=($(date +%s) x) bash -c 'git push -f'` passes, pinned in the known-limit test.
- plan (judge 1): this change waits for `fix-pipe-walk-compound` (Depends On), which MODIFIES the same requirement Direct merge refused in a process tree; its delta is rebased on that one's archived text if they differ.
