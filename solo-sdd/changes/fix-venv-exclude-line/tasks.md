## 1. Implementation

- [ ] 1.1 Requirement Worktree venv link, scenario The .venv link is invisible to git: in `tests/test_sdd_worktree.py::test_links_excluded_without_gitignore` add the assertions that `info/exclude` has the line `/.venv` and no bare `.venv` line; they pass on the current code, as the code is right and the spec text is the defect, so this row pins the form the spec now states; proven by `python3 tests/test_sdd_worktree.py`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-venv-exclude-line` and archive the change with `solo-sdd archive fix-venv-exclude-line --yes`
