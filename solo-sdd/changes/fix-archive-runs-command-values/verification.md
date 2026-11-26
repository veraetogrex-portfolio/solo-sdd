## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` a temporary repository), run from a script file; an empty answer means the command passes, a `deny` answer prints its reason.

1. A transcript where the session edits `src/app.py` and runs no `Review:` agent: `env -S 'solo-sdd archive add-words'`, `env --split-string 'solo-sdd archive add-words'`, `env -iS 'solo-sdd archive add-words'`, `env -S 'solo-sdd archive' add-words`, `npx -c 'solo-sdd archive add-words'`, `npx --call 'solo-sdd archive add-words'`, `npx --call='solo-sdd archive add-words'`, `sudo -u root npx -c 'bash -c "solo-sdd archive add-words"'`, `time --output /tmp/x solo-sdd archive add-words`, `/usr/bin/time --format %e solo-sdd archive add-words` and `time --output=/tmp/x solo-sdd archive add-words` → each `deny` naming `src/app.py`, with every form the stand already holds.
2. The same forms against a change with a foreign CLAIM and no edits → each `deny`, "taken by another agent"; `env -S'solo-sdd archive add-words'` and `env --split-string='solo-sdd archive add-words'` → `deny`, "The command prints the whole environment or a secret".
3. `env -S 'solo-sdd validate --all'`, `npx -c 'echo solo-sdd archive add-words'`, `env -u S 'solo-sdd archive add-words'` and `echo env -S 'solo-sdd archive add-words'` → no answer.
4. `time --output /tmp/x printenv` and `/usr/bin/time --format %e printenv` → `deny`, "The command prints the whole environment or a secret"; `time --output /tmp/x ls` and `env -S 'A=1 env'` (the listed known bypass) → no answer.
Steps 1-4 run in one call of the stand, which makes and removes its temporary home: `python3 tests/stands/archive-run-words.py`, its last line `archive-run-words: <n> of <n> checks passed`; with `SOLO_SDD_HOOK=~/.claude/hooks/work_hooks.py` the same stand drives the deployed copy after `sync.py push`.

5. In a Claude Code session after `sync.py push` of the merged change, against a throwaway change `live-archive-probe` with a foreign CLAIM in the main checkout (the guard reads changes from the git root of the session folder): `env -S 'solo-sdd archive live-archive-probe'`, `npx -c 'solo-sdd archive live-archive-probe'` and `time --output /tmp/x solo-sdd archive live-archive-probe` run through the Bash tool → each refused as taken by another agent; the throwaway change folder is removed after.

## Needs

- Step 5: `sync.py push` of the merged change, the delivery's layout step (a prod action of this repository, AGENTS.md Security), then a Claude Code session that loads the deployed hook.

## Fallback

Step 5 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-4), and Not Verified names step 5 if the layout has not happened, with a line in the first table of `docs/waiting.md`.
## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

- analyze: joined `env -S'…'`/`--split-string=…` are refused by the env guard first, so the archive reason never shows (J1) → the joined forms keep the dump reason in their own scenario; the env guard is not changed for them — `env_alone` belongs to Environment dumps refused, and they are refused either way.
- analyze: the hostile rows had no expected answer (J3) → scenario Broken and deep strings: no run and no internal error for the broken and the past-depth strings, the run within a second for the long cluster.
- analyze: the secret-guard delta was built on the dependency's delta before its PR #99 merged (J6) → #99 merged as 5549bc4, this branch was fast-forwarded onto it before any code, and the delta equals the main spec plus the `time --output`/`--format` rows; it is compared again before the archive.
- analyze: the runner rule of task 1.2 was in no scenario (repeat A3) → `uv run env -S '…'` is a refused row, `npx prettier -c '…'` a known false refusal in Out of Scope and the known-limit test.
- analyze: the repeat named per-scenario checks for task 1.1 (A4) → `archive_refused` only for the scenarios refused with the archive reason.
- analyze: Out of Scope named the wrong requirement for the `env -S` bypass (J11) → it names Known bypasses of the Bash guard.
- analyze: `npx -c'…'` joined (judge J12, dropped) → not read as `--call`: npm's option parser does not split it.
