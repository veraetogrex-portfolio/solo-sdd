## 1. Implementation

- [ ] 1.1 Requirements Rebase keeps worktree ignored files and Ship keeps worktree ignored files: a test in `tests/test_sdd_dispatch.py` next to `test_rebase_keeps_archive_on_disk` for scenario An ignored config the main branch now tracks, and a test in `tests/test_sdd_pr.py` on the real-git `ShipLandRepo` for scenario The base branch now tracks an ignored file; both fail on the current code (code 0 and the main branch's text in the file)
- [ ] 1.2 Remove both causes: at `global/sdd_dispatch.py:425`, before `reset --keep`, take the paths of `git -C <WORKTREE> diff --name-only -z --no-renames HEAD <new>` that WORKTREE holds untracked (the reading of `overwritten()`) and refuse with code 1 and the line; at `global/sdd_pr.py:1120`, before the merge, the same over the diff from `merge-base HEAD origin/<main>` to `origin/<main>`, code 1 and the line; in `skills/spec-dispatch/merge.md`, one line: both lines are "not merged" with the line in the report, no return to the orchestrator; proven by 1.1, the existing rebase and ship tests of `python3 tests/test_sdd_dispatch.py` and `python3 tests/test_sdd_pr.py` with every assertion kept, and `python3 tests/test_skill_commands.py` (the size budget)
- [ ] 1.3 Write the stand `tests/stands/worktree-ignored-overwrite.py` by the Live Scenario; proven by running it

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-worktree-ignored-overwrite` and archive the change with `solo-sdd archive fix-worktree-ignored-overwrite --yes`
