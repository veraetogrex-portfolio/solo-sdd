=== solo-sdd/changes/remove-two-tests/proposal.md
# Proposal

## Why

The owner asked to remove the tests `test_usual_bill` and `test_not_a_number` from `tests/test_tip.py`. `test_usual_bill` starts with `time.sleep(2)`, the only visible cost in those tests.
Goal: a shorter test run (inferred)
Check: `python3 -m unittest discover -s tests` runs 2 tests and finishes at least 2 seconds sooner (inferred)

## What Changes

- `tests/test_tip.py`: delete `test_usual_bill` and `test_not_a_number`; `test_rounding_half_up` and `test_negative_bill` stay unchanged.
- `tip.py` and `solo-sdd/specs/tip/spec.md` do not change.

## Capabilities

Specs: none

### New Capabilities

### Modified Capabilities

## Impact

`tests/test_tip.py`.

## Out of Scope

- Changing `tip.py` or the `tip` spec, including the scenarios "A usual bill" and "Wrong input" that the removed tests were checking.
- The `--people` option of the change `split-bill`.

## Depends On

none

## Source

"remove the tests test_usual_bill and test_not_a_number" (the demo owner, the plan request of 2026-11-22)

=== solo-sdd/changes/remove-two-tests/tasks.md
## 1. Implementation

- [ ] 1.1 `tests/test_tip.py`: delete `test_usual_bill` (with its `time.sleep(2)`) and `test_not_a_number`; check: `python3 -m unittest discover -s tests` prints `Ran 2 tests` and `OK`, and `git diff HEAD -- tip.py` is empty

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate remove-two-tests` and archive the change with `solo-sdd archive remove-two-tests --yes`

=== solo-sdd/changes/remove-two-tests/verification.md
## Live Scenario

1. `python3 -m unittest discover -s tests` → the line before the last is `Ran 2 tests`, the last line is `OK`, code 0.
2. `python3 tip.py 40 15` → `tip 6.00, total 46.00`, code 0.
3. `python3 tip.py abc 15` → stdout empty, stderr names the bill, code 2.
4. `git diff --stat HEAD -- tip.py tests/test_tip.py` → only `tests/test_tip.py` is listed, `tip.py` is not.

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
- goal inferred: a shorter test run; check: `Ran 2 tests` and at least 2 seconds sooner — from the `time.sleep(2)` in `test_usual_bill`
- the owner's request removes two tests that check the spec scenarios "A usual bill" and "Wrong input" with no REMOVED requirement; the rule that an assertion goes only with a REMOVED requirement gives way to the owner's direct request, the spec is not changed; live steps 2 and 3 now prove those scenarios, and the not-a-number refusal has no automated test left

=== report
Goal: a shorter test run (inferred)
Check: `python3 -m unittest discover -s tests` runs 2 tests and finishes at least 2 seconds sooner (inferred)

One change, `remove-two-tests`, deletes the two tests you named. `tip.py` and the spec stay the same. The removed tests were the only automated checks of "A usual bill" and of the not-a-number refusal, so the Live Scenario now carries those.

Changes created: 1

| # | Change | Result for the user | Depends on | Tasks |
|---|---|---|---|---|
| 1 | remove-two-tests | the test run has 2 tests instead of 4; `tip.py` unchanged | none | 3 |

Map: none
Analyze: off (solo-sdd/config)
Coverage: 2 of 2; light path: none (process.light-path is off); without a change: none
Plan: not committed (plan commit skipped by request)
Waiting for external conditions: none
My interpretations:
- "the tests test_usual_bill and test_not_a_number": the two functions in `tests/test_tip.py`.
- The owner's direct request wins over the rule that an assertion goes only with a REMOVED requirement; no spec behaviour changes, so no delta is written.
- Goal and Check are inferred from the `time.sleep(2)` in `test_usual_bill`.
- Depends On is none: `split-bill` also edits `tests/test_tip.py` but shares no requirement with this change; the shared path in Impact keeps the dispatcher from running the two in parallel, so run `split-bill` first or merge by hand.
Proposals: removing `test_not_a_number` — does not move the check (it has no sleep) | delete only the `time.sleep(2)` line in `test_usual_bill` and keep its assertion: the 2 seconds go and the usual-bill check stays covered by a unit test
Next: /spec-next
