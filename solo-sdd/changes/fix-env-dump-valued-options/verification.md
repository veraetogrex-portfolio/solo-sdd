## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository), run from a script file, since a Bash line that holds `env` next to `$(` is refused by the deployed hook itself; an empty answer means the command passes, a `deny` answer prints its reason.

1. On the branch's base commit 46d45ad (main after `fix-env-dump-text-words` is merged; the forms were reproduced on dfc9500), its hook run as `python3 <worktree>/global/work_hooks.py guard` from a temporary worktree of that commit, `env -u X printenv`, `env -C /tmp printenv`, `sudo -u root printenv`, `sudo -u root printenv GITHUB_TOKEN`, `env -u X sh -c env` and `caffeinate -t 5 printenv` → no answer (each passes).
2. On the branch, the same six commands, every command of the refused half of the scenario A wrapper option with a value and the refused commands of the scenario A dump nested past the parsed depth → each `deny`, "The command prints the whole environment or a secret".
3. On the branch, every passing command of those scenarios and every command of the scenario An interpreter prints the environment → no answer; `docs/hooks.md` names an interpreter's script that runs or reads the environment and a dump word run by another program from its arguments in its list of known bypasses.
Steps 1-3 run in one call of the stand, which makes and removes its temporary home and base worktree: `python3 tests/stands/env-dump-valued-options.py`, printing `env-dump-valued-options: 42 of 42 checks passed`.

4. In a Claude Code session after `sync.py push` of the merged change (the delivery's layout step): `env -u X printenv` run through the Bash tool is refused with the same reason instead of printing the environment.

## Needs

none

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

- 2026-11-26, worktree of branch `change/fix-env-dump-valued-options` on base 46d45ad: `python3 tests/stands/env-dump-valued-options.py` printed `env-dump-valued-options: 42 of 42 checks passed` (steps 1-3: the six forms pass on the base hook; on the branch 19 forms are refused with "The command prints the whole environment or a secret", 15 forms pass, and `docs/hooks.md` names both known bypasses).
- Before the fix `python3 -m unittest test_work_hooks.SecretFiles` from `tests/` failed in the two new tests and the property on their first refused row; after it 19 tests OK. Removing the `wrapper_values_cut` call in `env_dump` makes `test_environment_dumps_refused_property` fail on `sudo -u root printenv; …` (mutation checked, then restored).
- `python3 tests/run.py --jobs 5 --tier slow`: files 42, failed 0; lint without output.

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

- Step 4 (the deployed hook in a Claude Code session) waits for `sync.py push` of the merged change, a prod action of the delivery; by the Fallback, steps 1-3 ran with the hook from the branch. Row in the first table of `docs/waiting.md`.

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan: the awk form is listed as a known bypass, not fixed: in a plain command the guard does not read interpreters' scripts, and awk, python, perl, node and ruby each print the environment in their own syntax; the guard is an accident guard, the boundary is `Read(**/.env)` and secrets kept only in `.env`.
- plan: the fix goes into `env_dump` (one `wrapper_values_cut` call, as `archive_runs` does), not into `cmd_start`, which is in the shell block shared with `global/process-guard.py` and called at twelve places of `global/work_hooks.py` by other guards.
- plan: the delta's Environment dumps refused block is the one `fix-env-dump-text-words` writes, with one scenario added, since that change is archived first.
- analyze (judge J2): the copied block can go stale if `fix-env-dump-text-words` edits its block before its archive → task 1.1 first re-copies the block from the main spec after that archive and keeps only the added scenario — a stale copy would revert the dependency's text on this archive.
- analyze (judge J3): `caffeinate -t`, `exec -a` and `npx -p` have the same cause → fixed here through one map of each wrapper's valued options in `wrapper_values_cut`, not listed as bypasses — the same function and cause; `cmd_start` still stays as it is.
- analyze (judge J4): `env -u X sh -c env` passed through the words `env_dump` hands to `shell_text` → those words are cut too — the same function and cause.
- analyze (judge J5, J7): `xargs printenv`, sed's `e` command and `env -S env` → listed as known bypasses, not fixed — another program runs the dump word from its arguments, which the guard does not read in a plain command; `-S` is not added to `ENV_VALUED`, since its value is a command line.
- analyze (repeat A1, judge J1): `fix-env-dump-text-words` is not archived → no artifact edit — at plan time the plan's own dependency is open by design; `Depends On` names it and `/spec-next` takes this change only after its archive.
- analyze (repeat A2): one map for `wrapper_values_cut` would also change the archive guard (`archive_runs` of `caffeinate -t 5 solo-sdd archive x` gives `x`), a behaviour of `work-hooks-subagents` without a delta → the map is passed by `env_dump` only, `archive_runs` keeps `sudo` and `env`, and the archive guard's forms go to Out of Scope — the bug is the environment dump.
- analyze (judge J9): no owner quote names this bug → Source names its origin (the dependency's analysis judge, the plan the owner approved) and quotes the planning session's task.
- sibling (fix-env-dump-text-words archive, 2026-11-26): its scenario Shell forms the exemption cannot read, which the main requirement Environment dumps refused now holds, is copied into this MODIFIED block; nothing else in the block changed.
- spec-next (task 1.1, 2026-11-26): the delta block was stale against the main spec after that archive (two scenario lines of `env runs a program next to a substitution` and `Dumps still refused`) → re-copied from the main spec, keeping only the added scenarios.
- analyze (2026-11-26, judge J1): `time` is a wrapper whose `-o FILE` and GNU `-f FORMAT` make the next word look like the program → `time`: `-o`, `-f` added to the map with refused rows; npm's own options of `npx` (`--loglevel` and others) → Out of Scope, not added — they are npm's open option set, not the wrapper's, and the guard is an accident guard.
- analyze (2026-11-26, judge J2): hostile input — a long run of wrapper options and a nesting past the parsed depth → a 20,000-pair row timed under 1 s, and past depth 3 any dump word counts, as `env_read` counts any `.env` name there; a known bypass was rejected, since `env_read` already fails closed at the same depth.
- analyze (2026-11-26, judge J3): the property's generator never reached a wrapper prefix in a plain command → the samples and a plain-form assertion are added, and the mutation it must catch is named in task 1.1.
- analyze (2026-11-26, judge J4, J5, J7): `caffeinate -w` and `npx --package` get scenario rows; task 1.2 names the tests that turn from red to green; Out of Scope counts the `cmd_start` callers as twelve.
- analyze repeat (2026-11-26, A1): the depth rule would also refuse a third-level exempt form (`eval eval eval env X=1 python3 -V`) → only the text handed on past the third level counts by its dump words, the third level's program word is still read, and the scenario names both outcomes; the rule stays in the scenario, not in the requirement text — that text is the sibling's block and the scenario's THEN states the rule.
- analyze repeat (2026-11-26, R1): no row held that `archive_runs` keeps its reading → a row that `archive_runs("caffeinate -t 5 solo-sdd archive x")` still gives `[]`.
- analyze repeat (2026-11-26, A2, L1): `in a plain command` now stands before both the interpreter's script and the dump word another program runs (the requirement text is not longer); the plan line counts the `cmd_start` callers as twelve.
