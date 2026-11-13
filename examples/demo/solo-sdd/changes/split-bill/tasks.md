## 1. Implementation

- [ ] 1.1 `tests/test_tip.py`: a test for each scenario of "Split between people" in `specs/tip/spec.md`; check: the new tests fail on the current `tip.py`
- [ ] 1.2 `tip.py`: the `--people` option and the `each` line; check: `python3 -m unittest discover -s tests` passes, the old tests included

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate split-bill` and archive the change with `solo-sdd archive split-bill --yes`
