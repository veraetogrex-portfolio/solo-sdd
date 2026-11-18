## 1. Implementation

- [ ] 1.1 Requirements Test imports found before the run and What the import check passes by: in `tests/run.py`, before the first file starts, read the statements directly in the module body of every selected test file with `ast` (a file that does not parse is left out), skip a first name part that is a `.py` file or package under `tests/` or directly in the root, look the rest up with `importlib.util.find_spec` of the first name part with `tests/` and the repository root on `sys.path`, and on any missing one print one line per module (module, importing files, `sys.executable`, the backquoted command of the `Install` row of `AGENTS.md` or `install command: see the Install row of AGENTS.md`) and exit 2; proven by step 1 of the Live Scenario stand (task 1.3), with no second test of the same case
- [ ] 1.2 Add a class `ImportsFound` (docstring naming both requirements) to `tests/test_runner.py`, on its temporary `Tree`, for the cases the stand does not reach: a module of `tests/`, a dotted module of the root and a `check` module of a folder under `tests/stands/` count as found; a missing module imported only by an unselected file is not reported; an import inside a function, class, `if` or `try` is not collected; a file with a syntax error runs and fails on its own; a tree without `AGENTS.md` prints `install command: see the Install row of AGENTS.md`; proven by `python3 tests/test_runner.py`
- [ ] 1.3 Write the stand `tests/stands/test-runner-deps-check.py` by the Live Scenario: an isolated interpreter (`-I`, an empty temporary `PYTHONUSERBASE`), both runs, the summary line; proven by running it

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate test-runner-deps-check` and archive the change with `solo-sdd archive test-runner-deps-check --yes`
