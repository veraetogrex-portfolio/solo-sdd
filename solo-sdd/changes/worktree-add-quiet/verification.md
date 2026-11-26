## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository), the way `entry` in `tests/test_work_hooks.py` runs it; an empty answer means the command passes, a `deny` answer prints its reason.

The base is commit 286817e (main when the change was planned): its hook runs as `python3 <worktree>/global/work_hooks.py guard` from a temporary worktree of that commit (`git worktree add --detach "${TMPDIR:-/tmp}/wt-base-286817e" 286817e`, removed after); the branch hook runs from the change's own worktree.

1. On the base commit, `git worktree add -q "$TMPDIR/wt-x" -b x main` and `git worktree add --quiet /tmp/wt-q` → `deny`, "git worktree add refused: option -q" and "option --quiet".
2. On the branch, the same two commands, `git worktree add -q -b x "$TMPDIR/wt-x" main` and `git worktree add /tmp/wt-q -q` → no answer (the command passes).
3. On the branch, `git worktree add -q "$W" x` and `git worktree add -qb x /tmp/wt` → `deny`, the reason holds `git worktree add [-q | --quiet] [-b <name> | -B <name> | --detach | -f] <path> [<commit>]`.
   Steps 2-3 as one stand call, with the scenario commands of the earlier worktree changes and the dispatcher's launch: `python3 tests/stands/worktree-guard-words.py` → its last line `worktree-guard-words: 27 of 27 checks passed`.
4. In a Claude Code session after `sync.py push` of the merged change (the delivery's layout step): `git worktree add -q "${TMPDIR:-/tmp}/wt-quiet-check" -b wt-quiet-check main` run through the Bash tool passes and makes the worktree; then `git worktree remove "${TMPDIR:-/tmp}/wt-quiet-check"` and `git branch -D wt-quiet-check`.

## Needs

- Step 4 needs the merged change laid out by `sync.py push` (the delivery's layout step, a prod action on the agent folders done after merge, outside this change's run).

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge J10): the MODIFIED requirement says "a guard against a misplaced worktree" instead of "a guard against an accidental worktree placement": a rewording of the same meaning, made so the body with `[-q | --quiet] ` stays within the 500-character limit (it is exactly 500; any added word needs an equal cut).
- spec-next analyze (judge J1, J2, J3, all MEDIUM or LOW): step 4's layout became a Needs item with the existing Fallback; `skills/spec-dispatch/SKILL.md`, whose launch step listed `-q` as refused, joined Impact and task 1.2; the after-path `git worktree add /tmp/wt-q -q` joined the scenario The quiet option and Live Scenario step 2. Dropped J4 (the property refuses outside paths whatever options are inserted).
- plan (spec-analyze judge J1): `-q` and `--quiet` stand anywhere among the options, as `-b`, `--detach` and `-f` already do; the bracket form is a synopsis in git's style, not an order.
