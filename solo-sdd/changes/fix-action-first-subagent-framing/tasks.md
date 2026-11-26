## 1. Implementation

- [x] 1.1 Requirement Prescribed forms and failed reads: add `selftest` checks to `tests/stands/action-first.py` that the text of every prompt file `prepare` writes, after its rules block, holds `Your final message is passed to the owner as your answer.` as a whole line (whitespace collapsed), and that its rules block holds `unless its prompt holds the line` and `which makes it a report to the owner`; proven by `python3 tests/stands/action-first.py selftest` failing on the current code with those two checks `FAIL`
- [x] 1.2 Write that line in both prompt builders of `prepare` (`tests/stands/action-first.py`, the catalog prompts and `repo.md`/`repo-exp.md`), repoint the stand docstring's `selftest` line to the checks themselves, and add the clause to the analysis rule of section 1 in `global/AGENTS.md`; proven by `python3 tests/stands/action-first.py selftest` printing `<n> of <n> checks passed` and `python3 tests/test_repo_language.py` exiting 0
- [x] 1.3 Run `python3 tests/run.py --jobs 5 --tier slow`, the lint and `python3 -m solo_sdd validate --all`; proven by `failed: 0`, no lint output and 0 errors

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-action-first-subagent-framing` and archive the change with `solo-sdd archive fix-action-first-subagent-framing --yes`
