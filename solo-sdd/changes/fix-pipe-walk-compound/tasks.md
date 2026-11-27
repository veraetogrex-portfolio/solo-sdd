## 1. Implementation

- [x] 1.1 Requirements Environment dumps refused (scenario a redirection glued to the shell word), Direct merge refused in a process tree and Archive run behind runners and options (scenarios eval ends its options), Known bypasses of the Bash guard (scenario pipe walk forms outside the guard): in `tests/test_work_hooks.py` add `echo env | sh>out`, `echo env | sh&>out` and `echo env | (sh)>out` as refused rows of `test_environment_dumps_refused_a_shell_dump` and `echo ls | sh>out` as a passing row, `eval -- gh pr merge 1` to `test_direct_merge_refused_in_a_process_tree_a_process_tree`, `eval -- solo-sdd archive add-words` to `test_archive_run_behind_runners_and_options_end_of_options_before_the_c_string`, and the nine pipe-walk forms to `KNOWN_BYPASSES`; proven by the new refused rows failing on the base code and the known-bypass test passing on both
- [x] 1.2 Remove the cause in `global/work_hooks.py`: `part_words` splits a redirection glued after text from its word; `archive_runs` and `gh_merges` read eval's words through `eval_words`; `docs/hooks.md` names the pipe-walk forms as known bypasses; proven by the tests of 1.1 green, a replay of the base's test and stand literals with only the new refused rows changing verdict, then `python3 tests/run.py --jobs 5 --tier slow` with `failed: 0` and no lint output
- [x] 1.3 Rewrite the stand `tests/stands/pipe-walk-compound.py` for steps 1-3 of the Live Scenario; proven by the stand printing `pipe-walk-compound: 17 of 17 checks passed`

## 2. Acceptance

- [ ] 2.1 Run the Live Scenario (or its Fallback) from verification.md and record the Result, Not Verified and Decisions Without Owner sections
- [ ] 2.2 Run `solo-sdd validate fix-pipe-walk-compound` and archive the change with `solo-sdd archive fix-pipe-walk-compound --yes`
