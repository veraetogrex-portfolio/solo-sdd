# security-pass stand

`bad/` and `good/`: one small Python CLI (`notes.py`) with its spec (`SPEC.md`), for the security pass of `spec-audit`. `analyze/`: an OpenSpec tree with the change `add-project-delete`, for the trust boundary check of `spec-analyze`. The expected results are in `EXPECTED.md`; an auditor gets a copy of one folder without it.

Readiness without models: `python3 tests/stands/security-pass.py` from the solo-sdd root (steps 1 and 2 of the Live Scenario and the planted places). Nothing in the stand is run by the audit: the CLI is read, not started.
