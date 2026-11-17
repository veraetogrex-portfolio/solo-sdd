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
- analyze: a rebase conflict had no scenario and no test → the rebase aborted (later: in a temporary worktree, see review round 1), code 6 with the files, main and the branch on their previous commits; a row in task 1.2.
- analyze: the squash subject had no rule for a branch without an own commit → the rule `land` uses for a PR title (first parent, no merge or empty commits); none gives code 1 "not merged: merge: no title in the last own commit of the branch" without a merge — one rule for both delivery modes.
- analyze: the MODIFIED Local land command text dropped "before the merge" and the printed `not transported:` line, which the change does not mean to alter → "before the merge" is back in the text, the transport line is kept by a scenario (the text stays under 500 characters).
- analyze: a red check after `rebase` → `reset --keep` rolls the main branch back as now, the branch stays rebased in the worktree; "the worktree and branch stay" holds, and a repeated land rebases again without harm.
- analyze: the `land` title rule (`git log -1 --first-parent --no-merges --diff-filter=ACDMRTB`) reads from the branch head with no range, so a branch without an own commit would take a main branch subject → land-local reads it over `<main head>..change/<id>`; the rule stays the same and "own" holds — the scenario Squash without an own commit requires code 1 there.
- implementation: a squash conflict and a rebase conflict print the same line as a merge conflict, `not merged: merge conflict: <files>` — one line for the dispatcher to read whatever the method.
- implementation: a squash conflict is rolled back with `reset --merge` to the previous commit (no `MERGE_HEAD` to abort), which also takes the files the squash staged off the disk; a default merge conflict keeps `merge --abort`.
- review round 1, Important (rebase data loss): a rebase in WORKTREE checked out the main head over its ignored archive copies and replayed their removal from git, so the archive was gone after the fast-forward → the rebase runs in a temporary detached worktree, removed after it, and WORKTREE moves to the result with `reset --keep`, which touches only files the rebase changed; the scenario A rebase conflict and the proposal say so, a scenario Rebase keeps ignored copies and the row `test_rebase_keeps_archive_on_disk` (fails on the in-WORKTREE rebase) are added — a rebase must not run where the ignored copies live.
- review round 1, Important (`delivery.merge` in local delivery): `skills/spec-dispatch/preparation.md` now names `delivery.merge` the pull request method and says `land-local` reads `delivery.local-merge` itself; the plan line `delivery: …, merge: <delivery.merge>` of `sdd_dispatch_plan.py` stays: its exact form is a requirement of another capability with assertions, the line names the key's value, and the dispatcher passes no method to `land-local` — changing it is a separate change.
- review round 1, Important (tests repeating the stand): the unit rows default merge, squash, rebase and squash conflict are removed; the stand runs them on real input, and its step 4 `git status --short` empty also covers the staged squash files left on disk.
- review round 1, Nit: the `-D` comment no longer claims git sees a rebased branch as unmerged; the spec keeps `-D` for both. A stale `sdd-pr.py` without the key gives `not merged: settings: …` (KeyError caught) instead of a traceback. `rebase --abort` is gone with the temporary worktree. Squash of a branch with nothing left to commit keeps git's own message with code 1: rare, and it names the cause. The describe `type` row and the TUI row stay: task 1.1 and 1.4 name them.
- review round 2, Important (cleanup scope): `git worktree prune` after the temporary rebase worktree would drop other worktrees' registrations → removed; `worktree remove --force` deletes only its own entry, the folder goes with `rmtree`.
- review round 2, Important (coverage): `test_squash_without_own_commit` was deleted with the stand duplicates → restored, plus `test_squash_title_skips_empty_commit` for the title rule over an empty last commit, which the stand's branch lacks.
- review round 2, Nit: the `-D` reason in the spec and the proposal names only the squash; `rebase` refuses a WORKTREE that is not on `change/<id>` (code 1) before `reset --keep` could move another branch; the reset failure prints one line; the rebase conflict row asserts the temporary worktree is gone instead of a `rebase-merge` folder that can no longer exist. The plan line (round 1, finding 2) stays out of this change, named in the report for a new change.
- review round 2, Pre-existing: `reset --keep` overwrites an ignored WORKTREE file at a path the rebased commit tracks, as the old in-WORKTREE rebase did; not changed here.
