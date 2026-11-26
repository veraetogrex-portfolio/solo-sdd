## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository), run from a script file, since a Bash line that holds `env` next to `$(` is refused by the deployed hook itself; an empty answer means the command passes, a `deny` answer prints its reason.

1. On the branch's base commit, named by hash at the start of the work (main after `fix-env-dump-text-words` is merged; the forms were reproduced on dfc9500), its hook run as `python3 <worktree>/global/work_hooks.py guard` from a temporary worktree of that commit, `env -u X printenv`, `env -C /tmp printenv`, `sudo -u root printenv`, `sudo -u root printenv GITHUB_TOKEN`, `env -u X sh -c env` and `caffeinate -t 5 printenv` → no answer (each passes).
2. On the branch, the same six commands and every command of the refused half of the scenario A wrapper option with a value → each `deny`, "The command prints the whole environment or a secret".
3. On the branch, every passing command of that scenario and every command of the scenario An interpreter prints the environment → no answer; `docs/hooks.md` names an interpreter's script that runs or reads the environment and a dump word run by another program from its arguments in its list of known bypasses.
4. In a Claude Code session after `sync.py push` of the merged change (the delivery's layout step): `env -u X printenv` run through the Bash tool is refused with the same reason instead of printing the environment.

## Needs

none

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan: the awk form is listed as a known bypass, not fixed: in a plain command the guard does not read interpreters' scripts, and awk, python, perl, node and ruby each print the environment in their own syntax; the guard is an accident guard, the boundary is `Read(**/.env)` and secrets kept only in `.env`.
- plan: the fix goes into `env_dump` (one `wrapper_values_cut` call, as `archive_runs` does), not into `cmd_start`, which is in the shell block shared with `global/process-guard.py` and read by eight callers of other guards.
- plan: the delta's Environment dumps refused block is the one `fix-env-dump-text-words` writes, with one scenario added, since that change is archived first.
- analyze (judge J2): the copied block can go stale if `fix-env-dump-text-words` edits its block before its archive → task 1.1 first re-copies the block from the main spec after that archive and keeps only the added scenario — a stale copy would revert the dependency's text on this archive.
- analyze (judge J3): `caffeinate -t`, `exec -a` and `npx -p` have the same cause → fixed here through one map of each wrapper's valued options in `wrapper_values_cut`, not listed as bypasses — the same function and cause, and the map also serves `archive_runs`; `cmd_start` still stays as it is.
- analyze (judge J4): `env -u X sh -c env` passed through the words `env_dump` hands to `shell_text` → those words are cut too — the same function and cause.
- analyze (judge J5, J7): `xargs printenv`, sed's `e` command and `env -S env` → listed as known bypasses, not fixed — another program runs the dump word from its arguments, which the guard does not read in a plain command; `-S` is not added to `ENV_VALUED`, since its value is a command line.
- analyze (repeat A1, judge J1): `fix-env-dump-text-words` is not archived → no artifact edit — at plan time the plan's own dependency is open by design; `Depends On` names it and `/spec-next` takes this change only after its archive.
- analyze (repeat A2): one map for `wrapper_values_cut` would also change the archive guard (`archive_runs` of `caffeinate -t 5 solo-sdd archive x` gives `x`), a behaviour of `work-hooks-subagents` without a delta → the map is passed by `env_dump` only, `archive_runs` keeps `sudo` and `env`, and the archive guard's forms go to Out of Scope — the bug is the environment dump.
- analyze (judge J9): no owner quote names this bug → Source names its origin (the dependency's analysis judge, the plan the owner approved) and quotes the planning session's task.
- sibling (fix-env-dump-text-words archive, 2026-11-26): its scenario Shell forms the exemption cannot read, which the main requirement Environment dumps refused now holds, is copied into this MODIFIED block; nothing else in the block changed.
