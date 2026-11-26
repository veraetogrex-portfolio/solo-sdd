## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` a temporary git repository with one commit and a bare remote), the way `entry` in `tests/test_work_hooks.py` runs it; an empty answer means the command passes, a `deny` answer prints its reason.

The base is commit e262b7e (main when the change was planned): its hook runs from a temporary worktree of that commit (`git worktree add --detach "${TMPDIR:-/tmp}/wt-base-e262b7e" e262b7e`, removed after); the branch hook runs from the change's own worktree.

1. On the base commit, `git push --force origin main` and `git reset --hard HEAD` → no answer (they pass).
2. On the branch, the same two commands → `deny`; the reasons name the rule, a new commit and `git stash`.
3. On the branch, `git commit -m "never git push --force"`, `python3 sync.py push --force` and `git push origin main` → no answer.
4. In a Claude Code session after `sync.py push` of the merged change (the delivery's layout step), in a temporary repository with a bare remote: ask the agent to run `git push --force origin main` → the Bash call is refused by the hook and the remote branch keeps its commit (`git ls-remote` shows the same hash before and after).

## Needs

- Step 4: the layout of the merged change on the owner's machine (`sync.py push`) and one Claude Code session there.

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: the first run's judge kept five HIGH (no hostile-input task, no property for `--hard`, an unnamed audit test, a bypass list given only by reference, git's abbreviated options); all fixed in the delta and tasks 1.2, 1.4, 1.6 and 1.7. Kept MEDIUM `--force-if-includes` without a row, the undefined generator slots, the test name, the `python3` heredoc and the Needs of step 4 are fixed too.
- analyze (repeat): options follow git's own parsing: a force letter after `-o` in a cluster is its value, and `--hard` after `--` is a path; both pass.
- plan: `--force-with-lease` counts as a forced push: the global rule says "No `--force`" and a lease still rewrites the remote branch.
