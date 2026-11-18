## Live Scenario

1. `python3 tests/test_sdd_worktree.py` → the row of `test_links_excluded_without_gitignore` runs the real `sdd-worktree.py setup` on a temporary main repository with `.venv`. It checks that `info/exclude` holds the line `/.venv` and no bare `.venv` line, and that `git status --short` is empty; the suite file ends with `OK`.
2. `python3 -m solo_sdd validate --all` → `0 errors`, and the archived main spec names `/.venv`.

## Needs

none

## Fallback

Not needed: the scenario runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: the bug fix rule wants a first test that fails on the current code; here the code is right and the spec text is the defect (`add_exclude` in `global/sdd_worktree.py` writes `"/" + x` for every link but `node_modules`) → the first task pins the code's form with a passing row; the failing side is the main spec, fixed by the archive of this delta.
- analyze: the Live Scenario checks that no bare `.venv` line is written, task 1.1 did not → the task asserts both lines.
