## 1. Implementation

- [ ] 1.1 Requirement Worktree add by shell words (MODIFIED): add the rows of the scenarios The quiet option (three passing commands) and The quiet option with a variable path (two refused ones) to the worktree tests of `tests/test_work_hooks.py`, and change its `PLAIN` constant and the one of `tests/stands/worktree-guard-words.py` to the form with `[-q | --quiet]`, keeping every assertion; add refused rows `git worktree add -q ~/code/wt`, `git worktree add -q ../wt` and `git worktree add -q /tmp/../Users/x/wt` and `git worktree add -q --lock /tmp/wt` (an unknown option next to the quiet one, the reason holding the plain form), and let the existing property test `worktree_property` insert `-q` or `--quiet` before or after the path (its mutation proof and `max_examples` unchanged); proven by `python3 -m unittest test_work_hooks.WorktreeWords` from `tests/` failing on the current code
- [ ] 1.2 Let `-q` and `--quiet` through in the options loop of `wt_plain_problem` and name them in `WT_PLAIN` of `global/work_hooks.py` and in the plain form of `docs/hooks.md`; proven by `python3 tests/test_work_hooks.py` and `python3 tests/stands/worktree-guard-words.py`
- [ ] 1.3 Run `python3 tests/run.py --jobs 5 --tier slow`, the lint and `python3 -m solo_sdd validate --all`; proven by `failed: 0`, no lint output and 0 errors

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate worktree-add-quiet` and archive the change with `solo-sdd archive worktree-add-quiet --yes`
