## Live Scenario

In a temporary main repository with a worktree on `change/b` (three commits, the last `b: done`), run `python3 global/sdd_dispatch.py land-local <MAIN> <WORKTREE> b`:
1. Without `delivery.local-merge` → code 0, `git log -1 --format=%P` in MAIN has two parents.
2. `delivery.local-merge: squash` → code 0, one parent, subject `b: done`, `git branch --list change/b` empty.
3. `delivery.local-merge: rebase` with the main branch moved ahead → code 0, `git log --merges` empty, the three commits on top.
4. `squash` with a conflicting `README.md` → code 6 naming `README.md`, `git status --short` in MAIN empty, the branch in place.

All in one call: `python3 tests/stands/settings-local-merge.py` → `4 of 4 checks passed`.

## Needs

none

## Fallback

not needed.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: the cleanup with `branch -D` after squash and rebase contradicted the main requirement Local land checks and cleanup (`git branch -d`) without MODIFIED → it is MODIFIED with the old scenario kept and a squash cleanup scenario — a delta that contradicts the main spec without MODIFIED is CRITICAL.
- analyze: a rebase conflict had no scenario and no test → `rebase --abort` in the worktree, code 6 with the files, main and the branch on their previous commits; a row in task 1.2.
- analyze: the squash subject had no rule for a branch without an own commit → the rule `land` uses for a PR title (first parent, no merge or empty commits); none gives code 1 "not merged: merge: no title in the last own commit of the branch" without a merge — one rule for both delivery modes.
- analyze: the MODIFIED Local land command text dropped "before the merge" and the printed `not transported:` line, which the change does not mean to alter → "before the merge" is back in the text, the transport line is kept by a scenario (the text stays under 500 characters).
- analyze: a red check after `rebase` → `reset --keep` rolls the main branch back as now, the branch stays rebased in the worktree; "the worktree and branch stay" holds, and a repeated land rebases again without harm.
