=== solo-sdd/changes/remove-two-tip-tests/proposal.md
# Proposal

## Why

The owner asked to remove two tests, `test_usual_bill` and `test_not_a_number`, and named no reason. `python3 -m unittest discover -s tests` runs 4 tests in 2.188 s on 22.11.2026, and 2 s of that is the `time.sleep(2)` in `test_usual_bill` (`tests/test_tip.py`).

Goal: a fast test run (inferred)
Check: `python3 -m unittest discover -s tests` reports `Ran 2 tests` in under 0.5 s, from 2.188 s on 22.11.2026 (inferred)

## What Changes

- `tests/test_tip.py` no longer has the test `test_usual_bill` (class `TipAndTotal`) and the `import time` that only it used.
- `tests/test_tip.py` no longer has the test `test_not_a_number` (class `WrongInput`).
- `tests/test_tip.py` keeps `test_rounding_half_up` and `test_negative_bill` with their assertions unchanged.
- `tip.py` and the behaviour in `solo-sdd/specs/tip/spec.md` do not change: the command prints and refuses the same as before.

## Capabilities

### New Capabilities

### Modified Capabilities

Specs: none

## Impact

`tests/test_tip.py`

## Out of Scope

- Any change of `tip.py` or of a requirement in `solo-sdd/specs/tip/spec.md`.
- Removing the `time.sleep(2)` line and keeping the test instead (a proposal in the plan report, not a task).
- The open change `split-bill`, which adds tests to the same file for `--people`.

## Depends On

none

## Source

"remove the tests test_usual_bill and test_not_a_number" (the demo owner, 22.11.2026)

=== solo-sdd/changes/remove-two-tip-tests/verification.md
## Live Scenario

1. `python3 tip.py 40 15` → stdout is the one line `tip 6.00, total 46.00`, code 0: the behaviour of the removed `test_usual_bill` still holds.
2. `python3 tip.py abc 15`, `python3 tip.py 40 nan` and `python3 tip.py 40 -1`, each run alone → each prints a message on stderr, stdout is empty, code 2: the behaviour of the removed `test_not_a_number` still holds.
3. `grep -c -e test_usual_bill -e test_not_a_number -e "import time" tests/test_tip.py` → `0`.
4. `time python3 -m unittest discover -s tests -v` → code 0, the output lists `test_rounding_half_up` and `test_negative_bill` and ends with `Ran 2 tests` and `OK`, the run takes under 0.5 s.

## Needs

none

## Fallback

Not needed: the scenario needs nothing external.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- goal inferred: a fast test run; check: `python3 -m unittest discover -s tests` reports `Ran 2 tests` in under 0.5 s — inferred from the test file: `test_usual_bill` holds `time.sleep(2)` and the suite took 2.188 s with 4 tests on 22.11.2026; the owner's words name no goal.

=== solo-sdd/changes/remove-two-tip-tests/tasks.md
## 1. Implementation

- [ ] 1.1 `tests/test_tip.py`: remove the test `test_usual_bill` and the `import time` that only it used; check: `grep -c -e test_usual_bill -e "import time" tests/test_tip.py` prints `0` and `python3 -m unittest discover -s tests` passes
- [ ] 1.2 `tests/test_tip.py`: remove the test `test_not_a_number`, keep `test_rounding_half_up` and `test_negative_bill` with every assertion unchanged; check: `grep -c test_not_a_number tests/test_tip.py` prints `0` and `python3 -m unittest discover -s tests -v` ends with `Ran 2 tests` and `OK`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate remove-two-tip-tests` and archive the change with `solo-sdd archive remove-two-tip-tests --yes`

=== report
Goal: a fast test run (inferred)
Check: `python3 -m unittest discover -s tests` reports `Ran 2 tests` in under 0.5 s, from 2.188 s on 22.11.2026 (inferred)

One change is planned: it removes the two tests you named from `tests/test_tip.py`. Nothing is needed from you. The tip calculator itself does not change. Nothing was written to disk in this run, and the plan commit was skipped.

Changes created: 1

| # | Change | Result for the user | Depends on | Tasks |
|---|---|---|---|---|
| 1 | remove-two-tip-tests | `tests/test_tip.py` has no `test_usual_bill` and no `test_not_a_number`; the suite runs 2 tests in under 0.5 s | none | 4 (2 implementation, 2 acceptance) |

Map: none
Analyze: off (solo-sdd/config)
Coverage: 2 of 2; light path: none (`process.light-path` is `off`, so no item is light); without a change: none
Plan: commit skipped (this run writes no files); `solo-sdd validate --all` and `solo-sdd new` were not run for the same reason, so the artifacts are not validated
Waiting for external conditions: none
My interpretations:
- the two names are the tests `test_usual_bill` and `test_not_a_number` in `tests/test_tip.py` — the only files with those names.
- the requirements stay: you asked to remove tests, not behaviour, so no REMOVED requirement and the change has `Specs: none`. The rule that an assertion goes only through a REMOVED or MODIFIED requirement is set aside on your direct instruction. Unit coverage of the scenario "A usual bill" and of `abc`, `nan` and a negative percent is lost; the Live Scenario runs those inputs once, and `test_negative_bill` still covers a negative bill.
- `import time` goes with `test_usual_bill`, because nothing else uses it.
- `Depends On: none`: the open change `split-bill` also edits `tests/test_tip.py` (it adds tests and does not touch these two), so the shared path in `Impact` makes the dispatcher run them one after the other. In a manual run, `split-bill` can go first or second.
- The change name `remove-two-tip-tests` follows the project's plain kebab-case pattern, with no numbers.
Proposals: test_usual_bill — moves the check: yes, it holds `time.sleep(2)`, 2 s of the 2.188 s run; test_not_a_number — moves the check: no, three short process starts that together with `test_rounding_half_up` and `test_negative_bill` take under 0.2 s; cheaper way to the goal: delete only the `time.sleep(2)` line in `test_usual_bill`, which keeps all 4 tests and gives a suite of about 0.2 s (not done: the request names the removal of both tests)
Next: /spec-next
