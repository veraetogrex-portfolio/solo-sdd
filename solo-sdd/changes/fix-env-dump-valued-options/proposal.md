# Proposal

## Why

The `guard` hook lets through plain Bash commands that print the whole environment, though the requirement Environment dumps refused says a command that runs `printenv` or `env` without arguments is refused. Found 2026-11-23 by the analysis judge of `fix-env-dump-text-words`, recorded there as a separate change.

Reproduction (2026-11-23, commit dfc9500, the real hook by its entry point `python3 global/work_hooks.py guard` with a PreToolUse JSON, run from a script file): `env -u X printenv`, `env -C /tmp printenv`, `env -u X -u Y printenv`, `/usr/bin/env -u X printenv`, `timeout 5 env -u X printenv`, `sudo -u root printenv`, `sudo -u root env`, `sudo -g wheel printenv`, `env -u X sh -c env`, `sudo -u root sh -c printenv`, `caffeinate -t 5 printenv`, `exec -a NAME printenv` and `npx -p x printenv` pass → expected to be refused; `sudo -u root printenv GITHUB_TOKEN` passes → expected to be refused as a secret. `env -uX printenv`, `env --unset=X printenv` and `env -u X` are refused, as expected.

Cause: `global/work_hooks.py:2138`, `env_dump`: `cmd_start` (line 1394) skips a wrapper's option such as `-u` or `-C` but not its value, so `X`, `/tmp` or `root` is taken for the program and `printenv` after it is never read. `archive_runs` (line 1667) already reads the same words through `wrapper_values_cut` (line 1622), which turns the values of `sudo`'s and `env`'s valued options into `-`; `env_dump` does not, neither for the program word nor for the words it hands to `shell_text` (line 2130), and `wrapper_values_cut` knows no valued option of the other wrappers (`caffeinate -t`, `exec -a`, `npx -p`). A probe of `env_dump` with both calls and those options added refuses every form above and still passes `env -u HOME python3 -V`, `env -C /tmp ls`, `env -u X sh -c ls`, `sudo -u root ls`, `caffeinate -t 5 ls`, `npx -p x eslint .` and `env -u X printenv HOME`.

`awk 'BEGIN{system("env")}' /dev/null` passes too, and so do `python3 -c 'import os; print(os.environ)'` and `perl -e 'system("env")'`: a script of an interpreter that runs or reads the environment. The guard does not read interpreters' scripts in a plain command, and any interpreter (awk, python, perl, node, ruby) can print the environment in its own syntax, so the form becomes a listed known bypass, not a refusal. So do a dump word another program runs from its arguments: `xargs printenv`, sed's `e` command (`sed 's/.*/env/e' f`) and the split string of `env -S` (`env -S env`), whose value is a command line, not a value to skip.

## What Changes

- `env_dump` reads the words of each command through `wrapper_values_cut` before `cmd_start` and before `shell_text`, as `archive_runs` does: after a wrapper, the value of a valued option (`env -u X`, `-C /tmp`, `-P /usr/bin`, `sudo -u root`, `-g wheel`, `caffeinate -t 5`, `-w 1`, `exec -a NAME`, `npx -p x`, `--package x`, `time -o /tmp/x`, `-f %e`) is not the program, so `printenv`, `env`, a secret `printenv NAME` and a shell's `-c` dump after it are refused.
- A text that `eval` or a shell's `-c` string hands on past three levels, where `env_dump` reads no further, counts by any dump word in it, as `env_read` counts any `.env` name there: `eval eval eval eval env` is refused, `eval eval eval env X=1 python3 -V` still passes.
- `env_dump` hands `wrapper_values_cut` a map of each wrapper's valued options; `archive_runs`, its other reader, keeps reading only `sudo`'s and `env`'s values, so the archive guard does not change.
- The delta's Environment dumps refused block is the one `fix-env-dump-text-words` leaves in the main spec after its archive, with two scenarios added.
- `env -u HOME python3 -V`, `env -C /tmp ls`, `env -u X sh -c ls`, `sudo -u root ls`, `caffeinate -t 5 ls`, `npx -p x eslint .` and `env -u X printenv HOME` still pass.
- `docs/hooks.md` lists among the known bypasses of the Bash checks an interpreter's script that runs or reads the environment (`awk 'BEGIN{system("env")}'`, `python3 -c 'import os; print(os.environ)'`) and a dump word another program runs from its arguments (`xargs printenv`, sed's `e` command, `env -S env`).

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirements Environment dumps refused (scenarios of a wrapper's valued option and of a dump nested past the parsed depth) and Known bypasses of the Bash guard (an interpreter's script).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `docs/hooks.md`

## Out of Scope

- The other readers of `cmd_start` without `wrapper_values_cut` (the merge guard lists `sudo -u` and `env -u` as its known bypasses in `docs/hooks.md`): their own guards, not the environment dump.
- A change of `cmd_start` itself: it is in the shell block shared with `global/process-guard.py` and called at twelve places of `global/work_hooks.py`.
- npm's own valued options before the program of `npx` (`--loglevel`, `--registry`, `--cache`, `-w`, `--prefix`): `npx --loglevel silent printenv` still passes; the map takes only `npx`'s own `-p`/`--package`.
- Reading interpreters' scripts (awk `system(`, `getline`, python `os.environ`, perl, node), `xargs`, sed's `e` command and the `env -S` split string: listed as known bypasses instead.
- The archive guard's reading of `caffeinate -t`, `exec -a` and `npx -p` (`archive_runs`, requirement Archive run behind runners and options of `work-hooks-subagents`): a change of its own.
- The non-plain fallback of the same requirement: `fix-env-dump-text-words`.
- Neighbouring changes of the same plan: `action-first-project-repo`, `worktree-add-quiet`, `plan-input-skill`.

## Depends On

- fix-env-dump-text-words

## Source

No owner quote names this bug: it came from the analysis judge of `fix-env-dump-text-words` (its Out of Scope), in the plan the owner approved on 2026-11-23 with "do it" (translated from Russian, see the Source of `fix-env-dump-text-words`). The planning session's task to this session: "the `guard` hook (`global/work_hooks.py`, `env_dump` and `cmd_start`) lets through plain Bash commands that print the environment. Reproduced on commit 286817e by running `python3 global/work_hooks.py guard` with a PreToolUse JSON, from a script file (the hook refuses a Bash line that holds `env` next to `$(`): `env -u X printenv` and `env -C /tmp printenv` pass, because `cmd_start` skips `-u` or `-C` but not its value, so `env_dump` reads `X` or `/tmp` as the program; `awk 'BEGIN{system("env")}' /dev/null` passes too. The main spec `solo-sdd/specs/secret-guard/spec.md`, requirement Environment dumps refused, says such commands are refused. Decide in the change whether the awk form is fixed or listed as a known bypass in `docs/hooks.md`."
