## 1. Implementation

- [ ] 1.1 Requirement Stop gate switches, scenario Other gates in a worktree without a config file: rows in `tests/test_work_hooks.py` next to `test_a_worktree_reads_its_own_config` for the uncommitted, unarchived and ui-check gates; they fail on the current code
- [ ] 1.2 Remove the cause: move the `lacks` check of the open PR gate in `cmd_stop` of `global/work_hooks.py` into one helper and use it in `ui_file`, in the uncommitted and unarchived gates of `cmd_stop` and in the open PR gate; for a project folder below its git root (the unarchived gate's `change_project`) the helper reads the same relative folder of the main checkout; proven by 1.1 and `python3 tests/test_work_hooks.py`, every existing assertion kept (the `removed` row: a tracked config the branch deleted still gives the defaults)
- [ ] 1.3 Add the worktree steps to `tests/stands/settings-stop-hooks.py` by the Live Scenario; proven by running the stand

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-stop-gates-ignored-config` and archive the change with `solo-sdd archive fix-stop-gates-ignored-config --yes`
