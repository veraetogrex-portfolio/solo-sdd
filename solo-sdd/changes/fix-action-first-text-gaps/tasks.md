## 1. Implementation

- [ ] 1.1 Requirement Goal lines before the actions and Requirement Analysis data delivered as a file: add `selftest` checks to `tests/stands/action-first.py` that the rules block of every prompt file holds each of these two strings, and that `prepare` writes a prompt `steps-empty-prompt.md` (the steps request of `steps-prompt.md` on the `empty` folder) and prints `steps-empty-prompt:`; proven by `python3 tests/stands/action-first.py selftest` failing on the current code with those checks `FAIL`

  ```
  before the actions or the `No action follows:` line
  holds the same action lines
  ```

  compared after the stand's `norm` (backquotes kept in the rule as written)
- [ ] 1.2 Edit the analysis rule of section 1 in `global/AGENTS.md` (the bullet that holds the 5-line window) so it holds the two strings of 1.1 with their meaning (the goal lines first, before the actions or `No action follows:`, also for a lookup with nothing to fix, unless a prescribed form puts another line first; the analysis file holds the same action lines), the rule staying one bullet; write `steps-empty-prompt.md` in `prepare` and name `steps-empty-prompt:` in the module docstring; proven by `python3 tests/stands/action-first.py selftest` printing `<n> of <n> checks passed` and `python3 tests/test_repo_language.py`
- [ ] 1.3 Run `python3 tests/run.py --jobs 5 --tier slow`, the lint and `python3 -m solo_sdd validate --all`; proven by `failed: 0`, no lint output and 0 errors

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-action-first-text-gaps` and archive the change with `solo-sdd archive fix-action-first-text-gaps --yes`
