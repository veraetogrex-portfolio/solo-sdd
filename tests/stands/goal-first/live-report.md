Goal: make the two test names say what they check (inferred)
Check: grep finds 0 uses of `test_usual_bill` and `test_not_a_number`, and `python3 -m unittest discover -s tests` prints `Ran 4 tests` and `OK` (inferred)

The two tests are renamed in `tests/test_tip.py`, and nothing is needed from you.
- `test_usual_bill` is now `test_tip_and_total_of_a_usual_bill`.
- `test_not_a_number` is now `test_refuses_a_bill_or_percent_that_is_not_a_number`.

Checks done:
- The suite ran `Ran 4 tests` and `OK`. I re-ran it just now and got the same result.
- A grep of `tests/`, `solo-sdd/`, `WALKTHROUGH.md` and `AGENTS.md` shows the old names are gone. The file has four test functions and the two new names are among them.
- The rename is in git as commit `c1c1bdb rename the tests`, and the working tree is clean.

Checks not done:
- `solo-sdd validate --all` and a live run of `tip.py`, which the project's checks list asks for, were not run. Only test names changed and no behaviour did.
- Nothing was pushed, because the project has no remote.

Proposals:
- rename `test_usual_bill` — moves the check: yes, the old name is gone and the new one states what the test covers.
- rename `test_not_a_number` — moves the check: yes, same reason.

Decisions made:
- I picked the new names myself, since you did not give them.
- I treated this as a light-path edit: one file, no spec behaviour touched, no dependency or data touched.

No lesson to record.
