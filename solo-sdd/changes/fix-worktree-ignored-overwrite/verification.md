## Live Scenario

1. `python3 tests/stands/worktree-ignored-overwrite.py` → the stand builds a temporary `MAIN` with a bare `origin` and a worktree of `change/b` that holds an ignored `solo-sdd/config` with the text `mine`. Then `MAIN` commits `solo-sdd/config` with `git add -f`.
2. It runs the repository's `global/sdd_dispatch.py land-local` under `delivery.local-merge: rebase` and sees code 1, the line `not merged: rebase would overwrite ignored files in WORKTREE: solo-sdd/config`, and `mine` still in WORKTREE's file. On the previous code it sees code 0 and the text of `MAIN`.
3. It pushes the `MAIN` commit to `origin` and runs `global/sdd_pr.py ship` with a fake `gh` (no network). It sees code 1 with `not shipped: merge would overwrite ignored files in WORKTREE: solo-sdd/config`, the file still `mine`, and no push of `change/b`.
   The stand also reads `skills/spec-dispatch/merge.md` as `HOME=<temporary home> python3 sync.py push` lays it out and finds both lines named as "not merged" without a return to the orchestrator.
4. The stand prints `worktree-ignored-overwrite: 3 of 3 checks passed`.

## Needs

none

## Fallback

Not needed: the scenario runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: the bug fix had 8 tasks, over `process.bugfix-max-tasks` 5 → one task of the two failing tests, one of both fixes with the `merge.md` line, one of the stand — splitting into two changes was rejected: both causes are one class, one stand proves both.
- analyze: task 1.2 took `git diff <prev> <new>` with `prev` the main branch's commit; that diff holds only the branch's own edits and misses `solo-sdd/config`, which the main branch added (checked in a scratch repository: the diff `HEAD..<new>` names it, `<main>..<new>` does not) → the diff from WORKTREE's `HEAD` to the rebased commit, files WORKTREE holds untracked as `overwritten()` reads them.
- analyze: the `ship` diff `HEAD origin/<main>` also lists paths the branch itself removed → the diff from the merge base to `origin/<main>`, the paths the merge writes.
- analyze: code 6 sends the dispatcher to "Return on conflict", whose `git -C <WORKTREE> merge <main branch>` overwrites the same ignored file (checked: a merge in a scratch clone replaced an ignored `c` with the tracked text, code 0) → code 1, "not merged" in the report, the branch and WORKTREE stay for the person — the return would cause the very loss the change prevents. `git merge --no-overwrite-ignore` was tried as a native guard and did not refuse here, so the comparison is done by the tools.
- analyze: proof of the `merge.md` line read the real agent folders after `python3 sync.py push`, a prod action before merge → a temporary `HOME`.
