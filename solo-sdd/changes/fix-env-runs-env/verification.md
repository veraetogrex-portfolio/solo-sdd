## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository), run from a script file; an empty answer means the command passes, a `deny` answer prints its reason.

1. On the base commit 58c1d41, its hook run from a temporary worktree of that commit: `env env`, `env -i env`, `env -u X env`, `env FOO=1 env`, `env env -i`, `/usr/bin/env env`, `env /usr/bin/env`, `sudo env env`, `timeout 5 env env`, `env "env"`, `env -- env`, `env -uX env`, `env --unset=X env`, `printf x | env env` and `env -S env` → no answer (each passes).
2. On the branch, the same fifteen commands and `echo "$(date)"; env env` → each `deny`, "The command prints the whole environment or a secret".
3. On the branch, `env env ls`, `env -i env HOME=/x true`, `env env printenv HOME` and `env -S 'A=1 env'` → no answer; `docs/hooks.md` names `env -S 'A=1 env'` among the known bypasses.
Steps 1-3 run in one call of the stand, which makes and removes its temporary home and base worktree: `python3 tests/stands/env-runs-env.py`, printing `env-runs-env: 36 of 36 checks passed`.

4. In a Claude Code session after `sync.py push` of the merged change: `env env` run through the Bash tool is refused with the same reason instead of printing the environment.

## Needs

- Step 4: `sync.py push` of the merged change, the delivery's layout step (a prod action of this repository, AGENTS.md Security), then a Claude Code session that loads the deployed hook.

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan: the `eval` pipe forms (`eval echo env | sh`, `echo env | eval sh`), the `archive_runs` gaps and `SUDO_VALUED` holding `-h` stay out of this change → `shell_text` and `archive_runs` are other readers with their own grammar, and sudo's `-h` alone prints the help; the first two are proposed to the starting session as separate changes — the bug here is one line of `env_dump`.
- plan: the split string of `env -S` stays a known bypass, refusing it was rejected → its value is a command line the guard does not split; only a split string that is one dump word is refused now, by the same reading as `env env`.
- analyze (2026-11-26, judge J1): hostile input — a long run of `env` words → a row of 100,000 `env` words, refused with `env_dump` under 1 s, in `test_environment_dumps_refused_hostile_input`; open quotes do not apply, since bash runs nothing with one.
- analyze (2026-11-26, judge J2): the property's passing segments held no nested `env` followed by a program → `env env ls` and `env -i env HOME=/x true` join the passing samples.
- analyze (2026-11-26, judge J3, J5): forms the fix refuses were named nowhere, `env -S env` among them → the scenario env runs env, the rows and the stand name `timeout 5 env env`, `env "env"`, `env -- env`, `env -uX env`, `env --unset=X env`, `printf x | env env` and `env -S env`.
- analyze (2026-11-26, judge J4): Needs named no layout step → the post-merge `sync.py push` is in Needs, and the Fallback keeps the `docs/waiting.md` line.
- analyze repeat (2026-11-26, A5): the archived stand `tests/stands/env-dump-valued-options.py` expects `env -S env` to pass on the current tree, so it goes red after this fix → left as it is — a stand is a one-off record of its change on its pinned base, `tests/run.py` does not run stands, and its row moves to this change's stand.
- analyze repeat (2026-11-26, A6): the Known bypasses text named `env -S` as a whole while the new scenario refuses `env -S env` → its item narrows to a spaced `env -S` (a split string with a space); to stay within 500 characters, `with no space` reads `unspaced` and `SHALL be` the boundary reads `is` — the boundary sentence keeps its meaning.
- analyze repeat (2026-11-26, A1, A2, A4): the stand in What Changes, a test of its own for the scenario and the Source wording → not changed, as the judge marked the same findings dropped (J9, J10, J11).
