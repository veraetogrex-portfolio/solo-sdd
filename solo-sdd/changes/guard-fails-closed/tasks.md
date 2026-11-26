## 1. Implementation

- [ ] 1.1 Requirement Secret checks fail closed (ADDED): add rows to `tests/test_work_hooks.py` for the scenarios A raising Bash secret check, A raising read check, A raising Write check, Preparation raises and Another check raises, run in-process through `main()` with the named check replaced by one that raises (the way the module's other in-process tests patch it); proven by `python3 -m unittest test_work_hooks` from `tests/` failing on the current code in the two deny rows
- [ ] 1.2 In `global/work_hooks.py`, catch an exception of the three secret checks and of the preparation of their input inside `cmd_guard`, write it with `log_error` and `deny` with the check's name and `~/.claude/hook-state/errors.log`; leave `main()` and the other checks as they are; proven by 1.1 passing
- [ ] 1.3 Requirement Guard entry fails closed (ADDED): add to `tests/test_cli.py` rows for the scenarios A fresh home, An earlier install, A guard that cannot start and No script or no interpreter, in a temporary `HOME` the way the existing `install --hooks` tests run; keep every assertion of the existing hooks tests and of the `settings_strategy` property test; proven by `python3 tests/test_cli.py` failing on the current code in A fresh home, An earlier install and the interpreter row
- [ ] 1.4 In `solo_sdd/hooks.py`, connect `guard` with `onFailure="block"`, add `/usr/bin/python3 -c "" >/dev/null 2>&1 || exit 0` to `G` before the `exec`, so a missing interpreter and the macOS stub both pass, and reword the `DENY` comment; proven by 1.3 passing
- [ ] 1.5 Reword the fail-open line of `AGENTS.md`, the docstring of `global/work_hooks.py` and the failure lines of `docs/hooks.md` (the internal-error line and the `guard` row) to name the exception: the secret checks and a crash or timeout of the whole `guard` refuse; add to the test of 1.1 an assertion that `AGENTS.md` and `docs/hooks.md` name `Secret checks fail closed` behaviour by the words `secret checks` and `onFailure`; proven by that assertion failing before and passing after the edit
- [ ] 1.6 Run `python3 tests/run.py --jobs 5 --tier slow`, the lint and `python3 -m solo_sdd validate --all`; proven by `failed: 0`, no lint output and 0 errors

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate guard-fails-closed` and archive the change with `solo-sdd archive guard-fails-closed --yes`
