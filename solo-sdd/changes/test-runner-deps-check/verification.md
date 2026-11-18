## Live Scenario

The stand runs the real `tests/run.py` of the working folder on two interpreters: one with an isolated site (`-I`, a temporary empty `PYTHONUSERBASE`, so `hypothesis` is not found) and the one that has the test dependencies.

1. `python3 tests/stands/test-runner-deps-check.py` → the stand first confirms that the isolated interpreter cannot find `hypothesis` (if it can, the stand fails with `hypothesis is visible to the isolated interpreter` instead of passing), then runs `tests/run.py --jobs 2 tests/test_readme.py tests/test_runner.py` on it (`tests/test_runner.py` imports `hypothesis` at top level) and sees code 2, the line `missing module hypothesis` naming `tests/test_runner.py`, the isolated interpreter's path and the install command of the `Install` row, and no `ok` or `FAIL` line.
2. The same stand runs `tests/run.py --jobs 2 tests/test_readme.py` on the same isolated interpreter (`tests/test_readme.py` imports only the standard library) → code 0 and an `ok tests/test_readme.py` line.
3. The stand prints its summary: `test-runner-deps-check: 2 of 2 checks passed`.

## Needs

none

## Fallback

Not needed: the stand runs locally without access or paid calls.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- analyze: steps 1 and 2 used `tests/test_runner.py` as the file without a missing import, but it imports `hypothesis` at top level → step 2 runs `tests/test_readme.py`, step 1 relies on `tests/test_runner.py` as the importing file — the old step 2 would have ended with code 2.
- analyze: `tests/test_map_check.py` puts `tests/stands/map-stand` on its own path and imports `check` at top level, so a lookup with only `tests/` and the root on the path would refuse the whole suite → a first name part that is a `.py` file or package under `tests/` or directly in the root counts as found without a lookup — reading each file's own `sys.path` edits was rejected as running the file's logic.
- analyze: `find_spec` of a dotted name imports its parent package → only the first part of a module name is looked up.
- analyze: a file that does not parse, an import inside a function, class, `if` or `try`, and a missing `Install` row had no outcome → not collected / left out of the check / a fixed `see the Install row of AGENTS.md` text — the runner must not crash before the file reports its own error.
- analyze: the stand hides `hypothesis` with `-I` and an empty `PYTHONUSERBASE`, which works only while it is in the user site (here and in CI, `pip install --user`) → the stand checks that first and fails loudly otherwise, never passes on a visible module.
