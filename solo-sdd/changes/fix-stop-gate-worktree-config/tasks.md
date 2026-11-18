## 1. Implementation

- [ ] 1.1 Requirement Stop gate switches, scenarios A worktree with its own config and A worktree without a config file: rows in `tests/test_work_hooks.py` next to `test_settings_of_the_edited_repository`; the first fails on the current code
- [ ] 1.2 Remove the cause at `global/work_hooks.py:2772`-`2773`: read both settings from `root` when `root` has `solo-sdd/config`, else from `main_checkout(root)`; proven by 1.1 and the existing open PR rows of `python3 tests/test_work_hooks.py`, every assertion kept
- [ ] 1.3 Add the worktree steps to `tests/stands/settings-stop-hooks.py` by the Live Scenario; proven by running the stand

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-stop-gate-worktree-config` and archive the change with `solo-sdd archive fix-stop-gate-worktree-config --yes`
