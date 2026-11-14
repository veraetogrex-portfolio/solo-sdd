## 1. Decision without writing

- [ ] 1.1 Move the decision of `project_rules` in `solo_sdd/init.py` into a function that reads and returns the outcome and the new text without writing; `init` calls it and writes as before; the existing tests of `tests/test_init.py` keep every assertion; proof: `python3 tests/test_init.py` green

## 2. Doctor line

- [ ] 2.1 Requirement Stale project rules named: rows in the `Doctor` class of `tests/test_cli.py` for a current block, an older unedited block, an edited block, broken markers, erased markers, global scope and a folder without `solo-sdd/`, each asserting `AGENTS.md` keeps its bytes; proof: they fail before 2.2
- [ ] 2.2 The `project-rules` line in `solo_sdd/doctor.py` through the 1.1 function; `docs/first-project.md` names it; `tests/affected.json` keeps its keys; proof: the 2.1 rows green

## 3. Checks

- [ ] 3.1 `python3 tests/run.py --jobs 5 --tier slow`, `python3 -m pyflakes solo_sdd global scripts sync.py` without output, `python3 -m solo_sdd validate --all`

## 4. Acceptance

- [ ] 4.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 4.2 Run `solo-sdd validate project-rules-stale` and archive the change with `solo-sdd archive project-rules-stale --yes`
