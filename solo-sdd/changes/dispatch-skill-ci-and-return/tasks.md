## 1. Implementation

- [ ] 1.1 Requirement Unread checks in CI wait: add the step for `CI: infra` with `checks not read: <error>` to `skills/ship/SKILL.md` (its PR step, next to code 4) and `skills/spec-dispatch/merge.md` (next to the `infra` rerun line), with the repeated-failure outcome of each; keep each skill under its size budget; proven by step 1 of the stand, and the budget by `test_skill_size_budget_rows` in `python3 tests/test_skill_commands.py`
- [ ] 1.2 Requirement Overwrite check command: rows in `tests/test_sdd_pr.py` next to the `not shipped: merge would overwrite ignored files` row for both scenarios plus a no-match row (code 0, no output); they fail on the current code (`overwrites` gives the usage, code 2); then `sdd-pr.py overwrites <WORKTREE> <ref>` in `global/sdd_pr.py` over the existing `untracked_written`, with its `USAGE` line; proven by `python3 tests/test_sdd_pr.py`
- [ ] 1.3 Requirement Return keeps worktree ignored files: the Return on conflict message of `skills/spec-dispatch/merge.md` runs `python3 ~/.local/bin/sdd-pr.py overwrites <WORKTREE> <main ref>` before its `merge` and, on a non-zero code, hands back `STATUS: not_ready` with the printed line in `NOTES`, no merge; proven by step 2 of the stand
- [ ] 1.4 Write the stand `tests/stands/dispatch-skill-ci-and-return.py` by the Live Scenario (a temporary HOME, temporary repositories); proven by running it

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate dispatch-skill-ci-and-return` and archive the change with `solo-sdd archive dispatch-skill-ci-and-return --yes`
