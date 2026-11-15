## 1. Implementation

- [ ] 1.1 Rows of `test_reply_language` in `tests/test_work_hooks.py` named after Reply language check for the `:::writing` block and the `>` quote lines, failing on the current code; then `wrong_language` in `global/work_hooks.py` leaves both out; `python3 tests/test_work_hooks.py` passes
- [ ] 1.2 Tests named after Requested translation passes, one per scenario, failing first; then the last user-written message read from the transcript (text parts of user entries only; tool results and the entries the harness writes for hook feedback skipped, their form read from a real transcript here) and the skip in `cmd_stop`, the Russian stems as `\u` escapes; the tests pass
- [ ] 1.3 Tests named after Question window language, one per scenario; then the `AskUserQuestion` branch of `cmd_guard` joining questions, labels and descriptions, the deny reason in the project's language name, the unreadable input passing; the tests pass
- [ ] 1.4 `AskUserQuestion` in the `guard` matcher of `solo_sdd/hooks.py`; the repeated install row of the existing hook registration test in `tests/test_work_hooks.py` also counts `AskUserQuestion` once; a Hypothesis test named after Question guard registration: for any settings (no `hooks`, no `PreToolUse`, a `guard` matcher with or without `AskUserQuestion`, foreign entries before and after) applying twice equals applying once, `AskUserQuestion` and `SubagentHandback` are in the matcher once and foreign entries keep their order; a mutant that appends the tool without the check fails it; the tests pass
- [ ] 1.5 Line 14 of `global/AGENTS.md` replaced with the rule text of the proposal; `python3 tests/test_init.py` and `python3 tests/test_skill_commands.py` pass
- [ ] 1.6 `docs/hooks.md`: the question window check, the skipped writing blocks, quotes and translation requests, and that it acts only with `reply.language` `ru` or `en`; `python3 tests/test_repo_language.py` passes
- [ ] 1.7 `tests/stands/reply-language.py` for steps 1 to 7 of the Live Scenario, Russian text as `\u` escapes; it prints `reply-language: 7 of 7 checks passed`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate reply-language-requests` and archive the change with `solo-sdd archive reply-language-requests --yes`
