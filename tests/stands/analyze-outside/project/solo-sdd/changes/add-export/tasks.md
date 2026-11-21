## 1. Implementation

- [ ] 1.1 `tests/test_export.py`: a test for each scenario of the requirements Export to a bundle, Full history in the bundle, Export size and Merge an earlier bundle; check: the new tests fail on the current `notes.py`
- [ ] 1.2 `notes.py`: the `export` command with `--merge`, writing the bundle with `zipfile`; check: `python3 -m unittest discover -s tests` passes, the old tests included

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate add-export` and archive the change with `solo-sdd archive add-export --yes`
