## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` a temporary repository), run from a script file; an empty answer means the command passes, a `deny` answer prints its reason.

1. A transcript where the session edits `src/app.py` and runs no `Review:` agent: `env -S 'solo-sdd archive add-words'`, `env --split-string 'solo-sdd archive add-words'`, `env -iS 'solo-sdd archive add-words'`, `env -S 'solo-sdd archive' add-words`, `npx -c 'solo-sdd archive add-words'`, `npx --call 'solo-sdd archive add-words'`, `npx --call='solo-sdd archive add-words'`, `sudo -u root npx -c 'bash -c "solo-sdd archive add-words"'`, `time --output /tmp/x solo-sdd archive add-words`, `/usr/bin/time --format %e solo-sdd archive add-words` and `time --output=/tmp/x solo-sdd archive add-words`, `env -S '' solo-sdd archive add-words`, `npx -yc 'solo-sdd archive add-words'`, `npm exec -c 'solo-sdd archive add-words'` and `npm x --call 'solo-sdd archive add-words'` → each `deny` naming `src/app.py`, with every form the stand already holds.
2. The same forms against a change with a foreign CLAIM and no edits → each `deny`, "taken by another agent"; `env -S'solo-sdd archive add-words'`, `env --split-string='solo-sdd archive add-words'` and `env -S '-i solo-sdd archive add-words'` → `deny`, "The command prints the whole environment or a secret".
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
- analyze: the runner rule of task 1.2 was in no scenario (repeat A3) → `uv run env -S '…'` is a refused row. In implementation the string option is read only among a wrapper's own options (`npx prettier -c '…'`: `-c` belongs to prettier), so it is a passing row of A string that runs no archive, not the known false refusal the plan expected.
- analyze: the repeat named per-scenario checks for task 1.1 (A4) → `archive_refused` only for the scenarios refused with the archive reason.
- analyze: Out of Scope named the wrong requirement for the `env -S` bypass (J11) → it names Known bypasses of the Bash guard.
- implementation: the past-depth row `eval eval eval env -S '…'` already gives the run on the base code (eval joins its words without quotes, so `solo-sdd` follows `-S` as a separate word) → the row is four levels deep, `eval eval eval eval env -S '…'`, past the parsed depth as `eval eval eval eval solo-sdd archive …` is.
- review round 1, Important 1-4 (the env -S string is env's own arguments, an empty `-S ''` before words, `npx -yc`, `npm exec`/`npm x`; each confirmed by the reviewer on the real `/usr/bin/env` and npm) → fixed: the env string is parsed as `env <string> <words after it>`, an empty string counts for env, npx reads a short cluster ending in `c`, `npm exec` and `npm x` read as npx; the ADDED requirement and its scenarios name them; `env -S '-i …'` is refused by the env guard first, so it is a row of A joined env string.
- review round 1, Important 5 (quadratic time on repeated `-S` values) → fixed: only the first string option is read per command, the rest is in the string parsed again; a row of 3,000 pairs within a second.
- review round 1, Important 6 (tests of env splits the string, npx runs the string and A string that runs no archive repeat stand rows) → dropped: they are the bug-scenario tests of this bug fix change, which the repeat rule exempts.
- review round 1, Nits: `names =[` spacing fixed; the docstring now names getopt for env and npm for npx; the `\_` escape of BSD env is outside the chosen shell-quote reading (Out of Scope); `env - -S '…'` over-refusal, duplicate names, and the stand's TEXT rows against the claimed tree kept as harmless.
- review round 2, Important N1 (the words after the env string lost their quoting: `env -S 'bash -c' '…'` was missed) → fixed: the words after the string are quoted (`shlex.join`); this also ends the over-refusal of `env -S -i '…'` (round 2 Nit a).
- review round 2, Important N2 (npm's last `-c` wins; reading only the first let `npx -c 'echo hi' -c '…'` through) and N3 (npm's valued options, before or after `exec`, ended the reading) → fixed: every `-c`/`--call` value of npx, and of npm with `exec` or `x`, counts up to `--`, npm's options anywhere; npm's option table is not copied, so `npx prettier -c '…'` is a known false refusal again (known-limit test, Out of Scope), as the plan had first expected. Each value is parsed on its own, so the scan stays linear (a row of 3,000 values within a second).
- review round 3, Important I1 (`npm exec -a -c '…'` missed: the shell builtin exec's `-a` value cut applied to npm's exec) → fixed: the npx and npm branch reads its option words uncut; `npx -p -c '…'` is refused though npm takes `-c` as the package there, an over-refusal kept on the safe side.
- review round 3, Nits kept: four empty `-S ''` strings spend the three parse levels; `npm install x -c '…'` and `npx -c '--call=…'` are over-refusals; a duplicate name for `env -S 'A=1' …`; GNU long-option abbreviations (`--split`) are not read, as for every wrapper today.
- review round 4, Important R4-1 (the uncut option word lost the cut at a glued redirection: `npx -c>/dev/null '…'` missed) → fixed: the npx and npm option word is cut at a glued redirection as `archive_runs` cuts every word, but not value-cut; rows `npx -c>/dev/null '…'`, `npm exec -a --call>log '…'`.
- review round 4, Nit kept: a separate redirection between the option and its string (`npx -c 2>/dev/null '…'`) is taken as the string, as before this change.
- analyze: `npx -c'…'` joined (judge J12, dropped) → not read as `--call`: npm's option parser does not split it.
