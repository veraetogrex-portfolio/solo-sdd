## 1. Implementation

- [ ] 1.1 Requirement Worktree venv link, scenario A later link fails: a test in `tests/test_sdd_worktree.py` next to `test_failed_setup_is_discarded` that makes the second link fail the way the stand does (a read-only worktree root, `node_modules` under a writable `app/`, the mode given back in cleanup); it expects code 1, `node_modules` in `info/exclude`, a clean `git status` and `remove` code 0, and fails on the current code
- [ ] 1.2 Remove the cause at `global/sdd_worktree.py:794`-`799`: add the exclusion pattern for the links made so far also when the loop raises (a `try`/`finally` around the loop, or the pattern added right after each link); proven by 1.1 and `python3 tests/test_sdd_worktree.py`, every assertion kept
- [ ] 1.3 Write the stand `tests/stands/setup-links-exclude.py` by the Live Scenario; proven by running it

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-setup-links-exclude` and archive the change with `solo-sdd archive fix-setup-links-exclude --yes`
