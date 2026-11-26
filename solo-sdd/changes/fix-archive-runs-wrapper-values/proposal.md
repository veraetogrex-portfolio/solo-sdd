# Proposal

## Why

The `guard` hook lets through an archive run behind a wrapper option with a value other than `sudo`'s and `env`'s, behind a short option cluster and inside a subshell, though the requirement Archive run behind runners and options says such a run is recognised for the CLAIM refusal and the Review before archive. Kept out of `fix-env-dump-valued-options` (its Out of Scope) and of `fix-env-runs-env`.

Reproduction (2026-11-26, commit 9f138c8, the real hook by its entry point `python3 global/work_hooks.py guard` with a PreToolUse JSON, run from a script file, in a project whose change `add-words` has a foreign CLAIM): `caffeinate -t 5 solo-sdd archive add-words`, `caffeinate -w 1 …`, `exec -a NAME …`, `time -o /tmp/x …`, `/usr/bin/time -f %e …`, `(sudo -u root solo-sdd archive add-words)`, `(env -u X …)`, `sudo -Hu root …` and `env -iu X …` pass → expected to be refused as a foreign archive; `sudo -u root …`, `sudo -uroot …`, `npx -p x …` and `npx --package x …` are refused, as expected (`npx` is a runner, so every later word is already tried as the program). `archive_runs` and `wrapper_values_cut` are the same on b6844a4.

Cause: `global/work_hooks.py:1681`, `archive_runs` calls `wrapper_values_cut(w)` with its default map of `sudo` and `env` only and without the `glued` reading, which `env_dump` already uses (`DUMP_VALUED`, `glued=True`): the value of `-t`, `-w`, `-a`, `-o` or `-f` is left as a word, `cmd_start` takes it for the program, and `archive_name` finds no archive run; without `glued` the name lookup of `wrapper_values_cut` (line 1631) does not read `(sudo` as `sudo`, and `-Hu` takes no value.

## What Changes

- `wrapper_values_cut` has one reading for both callers: the valued options of `sudo`, `env`, `caffeinate`, `exec`, `npx` and `time` (the map `env_dump` uses today), a wrapper word in a subshell (`(sudo`), and a short cluster whose first valued letter is its last (`sudo -Hu root`; `-uroot` holds its value); the parameters `valued` and `glued` go.
- The forms of the reproduction are refused with the existing reasons (a foreign CLAIM, the Review before archive).
- The value of a valued option of these wrappers is never the program: `npx -p solo-sdd archive add-words` and `npx --package solo-sdd archive add-words` now pass, read as npx itself runs them (the package `solo-sdd`, the command `archive`, which that package does not have); they were refused before only because the runner path tried the value `solo-sdd` as the program. `npx -p solo-sdd solo-sdd archive add-words` stays refused.
- `env_dump` keeps its verdicts: its map and its reading are the ones it has today.
- The stand `tests/stands/archive-run-words.py` takes the hook it drives from `SOLO_SDD_HOOK` when set, so the live check runs the deployed copy.

## Capabilities

### New Capabilities

### Modified Capabilities
- `work-hooks-subagents`: MODIFIED requirement Archive run behind runners and options (scenarios Valued options of other wrappers, An option value is not the program).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/archive-run-words.py`

## Out of Scope

- A command string as an option value: `env -S 'solo-sdd archive x'`, `env --split-string …`, `npx -c 'solo-sdd archive x'`, `npx --call …` pass today and after this change; reading such a value as a command again (as the shell `-c` string is) is a reading of its own, and `env -S` is also a listed known bypass of the env guard: a change of its own.
- GNU time's long options `--output` and `--format` (`time --output /tmp/x solo-sdd archive x` passes today and after this change): adding them to the shared map also changes the verdicts of `env_dump` (`time --output /tmp/x printenv`), a requirement of `secret-guard`; macOS `/usr/bin/time` and the shell's `time` have no such options. With the command strings above: a change of its own.
- A runner's own valued option whose value is `solo-sdd` followed by `archive` (`uvx --from solo-sdd archive x`, `pipx run --spec solo-sdd archive x`, `uv run --with solo-sdd archive x`): the runner path still tries every later word as the program, so these stay refused, a false refusal kept over a missed run like the known limit below; only `npx`, which is also a wrapper of the map, has its option values cut.
- The valued options of `nohup`, `timeout`, `nice` and `command`: `cmd_start` already skips the values of `timeout` and `nice`, `nohup` and `command` take none.
- A change of `cmd_start` itself: shared with `global/process-guard.py`.
- The known false refusal of an argument of a runner-started program (`npx prettier solo-sdd archive x`): stays pinned as it is.
- Fail-closed archive checks: hooks are fail-open by the repository invariant; the open change `guard-fails-closed` keeps the archive checks fail-open.

## Depends On

none

## Source

The task of the starting session to this session (2026-11-26): "`archive_runs` in `global/work_hooks.py` reads only `sudo`'s and `env`'s valued options through `wrapper_values_cut` and without its `glued=True` reading, so an archive run behind `caffeinate -t 5`, `exec -a NAME`, `npx -p x`, `time -o /tmp/x`, a subshell `(sudo -u root solo-sdd archive x)` or a short cluster `sudo -Hu root solo-sdd archive x` is not recognised". It started from the Out of Scope of the archived change `fix-env-dump-valued-options`: "The archive guard's reading of `caffeinate -t`, `exec -a` and `npx -p` (`archive_runs`, requirement Archive run behind runners and options of `work-hooks-subagents`): a change of its own." No owner quote names it.
