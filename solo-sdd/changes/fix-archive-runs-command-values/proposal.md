# Proposal

## Why

The `guard` hook lets through an archive run whose command sits in an option value the wrapper runs as a command, and one behind GNU `time`'s long valued options, though the requirement Archive run behind runners and options refuses archive runs behind wrappers and their option values. Found 2026-11-26 in the Out of Scope of `fix-archive-runs-wrapper-values` (PR #98).

Reproduction (2026-11-26, commit 0dc1195; the real hook by its entry point `python3 global/work_hooks.py guard` with a PreToolUse JSON, run from a script file, against a change with a foreign CLAIM): `env -S 'solo-sdd archive add-words'`, `env --split-string 'solo-sdd archive add-words'`, `env -iS 'solo-sdd archive add-words'`, `npx -c 'solo-sdd archive add-words'`, `npx --call 'solo-sdd archive add-words'`, `npx --call='solo-sdd archive add-words'`, `time --output /tmp/x solo-sdd archive add-words` and `time --format %e solo-sdd archive add-words` pass → expected to be refused as taken by another agent. `env --split-string='solo-sdd archive add-words'` is refused, but only as an environment dump. The same hole in the env guard: `time --output /tmp/x printenv` and `/usr/bin/time --format %e printenv` pass, though the requirement Environment dumps refused refuses `printenv` without arguments.

Cause: `global/work_hooks.py:1622`, `WRAPPER_VALUED`: `time` names only `-o` and `-f`, so `wrapper_values_cut` leaves the value of `--output`/`--format` in place and `cmd_start` (line 1394) takes `/tmp/x` as the program, in `archive_runs` (line 1673) and `env_dump` alike. `archive_runs` reads a command string only after `eval` and a shell's `-c`; the string of `env -S` and `npx -c` is taken as one program word (`solo-sdd archive add-words`), which `archive_name` never matches.

## What Changes

- GNU `time`'s `--output` and `--format` join `-o` and `-f` in the shared `WRAPPER_VALUED`: `time --output /tmp/x solo-sdd archive add-words` and `time --format %e …` are refused by the CLAIM refusal and Review before archive, and `time --output /tmp/x printenv` and `/usr/bin/time --format %e printenv` by the env guard; `time --output /tmp/x ls` passes.
- `archive_runs` reads the string an option value hands on as a command: `env -S`/`--split-string` (the words after the string are appended to it as its arguments), also joined (`-S'…'`, `--split-string=…`) and at the end of a short cluster (`env -iS '…'`), and `npx -c`/`--call` (also `--call=…`; npm reads no joined `-c…`); the string is split by shell quoting and parsed again, like a shell's `-c` string. The joined `env` forms keep the env guard's dump reason, which that check gives first. `env -S 'solo-sdd validate --all'` passes.
- A broken or deep string reads no run and raises no internal error: an open quote, `env -S`, `npx -c` or `npx --call=` without a value, a string past three `eval` levels; a short cluster of 20,000 letters before `S` is read in under a second.
- The env guard does not read these strings: `env -S 'A=1 env'` stays a listed known bypass of `docs/hooks.md`.

## Capabilities

### New Capabilities

### Modified Capabilities
- `work-hooks-subagents`: MODIFIED requirement Archive run behind runners and options (scenario GNU time's long options); ADDED requirement Archive run in a command string of an option.
- `secret-guard`: MODIFIED requirement Environment dumps refused (scenario A wrapper option with a value gains GNU time's long options).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/archive-run-words.py`

## Out of Scope

- The env guard reading `env -S` and `npx -c` strings: `env -S` with a space stays a listed known bypass (requirement Known bypasses of the Bash guard, `docs/hooks.md`); this change touches Environment dumps refused only for GNU `time`'s long options, and a change that modifies Known bypasses of the Bash guard takes the rest.
- The env guard's refusal of a joined `env -S'…'` or `--split-string=…` string that runs no dump (`env -S'solo-sdd validate --all'`): it reads the joined option as an `env` with no program, a false refusal kept as today.
- `env -S` escape sequences and `${VAR}` expansion inside the split string: the string is split into words as the shell would, not by `env`'s own rules.
- Command strings of other programs' options (`xargs`, `find -exec`, `watch`, `script -c`): already outside the archive guard, as `xargs` is for the merge guard.
- The known false refusal of an argument of a program a runner starts (`npx prettier solo-sdd archive x`, and now `npx prettier -c 'solo-sdd archive x'`, since every word after a runner is read for a string option), kept over a missed run.

## Depends On

- fix-eval-pipe-env

## Source

Session task 2026-11-26: "The `guard` hook (`archive_runs` in `global/work_hooks.py`) does not recognise an archive run whose command sits in an option value that the wrapper runs as a command: `env -S 'solo-sdd archive x'`, `env --split-string 'solo-sdd archive x'`, `npx -c 'solo-sdd archive x'` and `npx --call 'solo-sdd archive x'` all pass a foreign CLAIM and the Review before archive. GNU time's long options (`time --output /tmp/x solo-sdd archive x`, `--format`) pass as well."
