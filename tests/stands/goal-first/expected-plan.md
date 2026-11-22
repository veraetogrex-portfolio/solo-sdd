A reference plan answer written by hand: every grade line of `--grade` gives `yes`.

=== solo-sdd/changes/drop-two-tests/proposal.md
# Proposal

## Why

The owner asked to remove two tests and gave no reason.

Goal: a shorter test round (inferred)
Check: `python3 -m unittest discover -s tests` finishes in under 1 s (inferred)

## Source

The owner: "remove the tests test_usual_bill and test_not_a_number"

=== solo-sdd/changes/drop-two-tests/tasks.md
## 1. Implementation

- [ ] 1.1 Remove `test_usual_bill` from `tests/test_tip.py`
- [ ] 1.2 Remove `test_not_a_number` from `tests/test_tip.py`

=== solo-sdd/changes/drop-two-tests/verification.md
## Live Scenario

1. `python3 -m unittest discover -s tests` → finishes in under 1 s.

## Decisions Without Owner

- goal inferred: a shorter test round; check: the round in under 1 s — `test_usual_bill` sleeps 2 s

=== report
Changes created: 1

Proposals: test_not_a_number — does not move the check, it runs in milliseconds
