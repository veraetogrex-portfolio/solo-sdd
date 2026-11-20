## 1. Implementation

- [ ] 1.1 Write the journal fixtures `tests/eval/fixtures/signals/` (`honest` and `guess`: dispatcher, orchestrator and subagent journals with `.meta.json`, archived `verification.md`), in the journal form `tests/eval/fixtures/fixture-session.jsonl` already has, with the rows of the scenarios Words that are not signals, No code edit and A false and an unknown signal; proven by `python3 tests/test_sdd_eval.py` loading them
- [ ] 1.2 Requirements Process path signals and What the signals read, metrics: compute the five signals in `session_metrics` of `global/sdd_eval.py` from the journal of the orchestrator that ran the archive, with the archive gate's code edit rule, and `live_in_scenario` of `global/sdd_dispatch.py` loaded by a file loader as `plan_module()` loads its module (the laid-out name has a dash); a test class `ProcessSignals` in `tests/test_sdd_eval.py` over the fixtures, copies built in a temporary folder, with rows for the scenarios; `tests/test_sdd_eval.py` in the `global/sdd_dispatch.py` entry of `tests/affected.json`; proven by `python3 tests/test_sdd_eval.py`
- [ ] 1.3 Requirement Metrics by one method: widen `role_of` and the role count to `lookup`, `analyze`, `attack`, `judge`, `check`, and the assertion of the existing role count test; proven by `python3 tests/test_sdd_eval.py`
- [ ] 1.4 Requirement Process path signals, compare: show the signals per change and run in the report and mark `done, path incomplete` and `done, path unknown`; rows in `ProcessSignals`; proven by `python3 tests/test_sdd_eval.py`
- [ ] 1.5 Write the stand `tests/stands/eval-process-signals.py` by the Live Scenario, and describe the signals, their sources and `null` in `tests/eval/README.md`; proven by running the stand and `python3 tests/test_repo_language.py`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate eval-process-signals` and archive the change with `solo-sdd archive eval-process-signals --yes`
