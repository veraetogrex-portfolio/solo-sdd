## 1. Implementation

- [x] 1.1 A row in `tests/test_settings.py` named after Local merge method: default `merge`, source `default`, the `describe` text of `delivery.merge` naming `delivery.local-merge`; then the key in the settings block with its `ABOUT` line and the new `delivery.merge` description, `python3 scripts/sync_blocks.py --check` empty; the row passes
- [x] 1.2 Rows in `tests/test_sdd_dispatch.py` named after Local land command and Local land checks and cleanup: squash without an own commit (code 1, main unchanged), a rebase conflict (code 6, main and branch on their previous commits), a red check after a rebase, a rebase keeping the ignored archive; squash, rebase and a squash conflict are the stand's steps; they fail on the current code
- [x] 1.3 `global/sdd_dispatch.py` land-local merges by the setting, aborts a squash conflict back to the previous commit and rebases in a temporary worktree and moves WORKTREE with `reset --keep`, deletes the branch with `-D` after squash and rebase; the rows of 1.2 pass and the existing land-local tests keep every assertion
- [x] 1.4 `skills/spec-dispatch/merge.md` names the setting for local delivery; `docs/settings.md` row; `tests/stands/settings-tui.py` gains the row, every assertion kept
- [x] 1.5 The stand `tests/stands/settings-local-merge.py` runs the Live Scenario

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate settings-local-merge` and archive the change with `solo-sdd archive settings-local-merge --yes`
