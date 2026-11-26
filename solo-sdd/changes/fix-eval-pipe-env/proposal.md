# Proposal

## Why

The `guard` hook lets through a plain Bash command in which `eval` is the source of a pipe into a shell, or a shell run by `eval` reads a pipe, and that command prints the whole environment, though the requirement Environment dumps refused says a command that runs `env` or `printenv` without arguments, alone or in a pipe, is refused. Found 2026-11-26 while closing `fix-env-runs-env` (PR #94).

Reproduction (2026-11-26, commits 9f138c8 and b6844a4, the latter with PR #94 merged; the real hook by its entry point `python3 global/work_hooks.py guard` with a PreToolUse JSON, run from a script file): `eval echo env | sh`, `eval echo printenv | bash`, `eval 'echo env' | sh` and `echo env | eval sh` pass → expected to be refused; so do `eval echo env | tee | sh`, `echo env | eval 'cat | sh'` and `printf env | eval eval sh`. `echo x | eval env` and `eval eval eval eval echo env | sh` are already refused: the text `eval` runs is read, past three levels by any dump word in it.

Cause: `global/work_hooks.py:1999`, `shell_text`: the source of a pipe into a shell that reads stdin is read only when it is `echo` or `printf` (line 2016), passed through `tee` or a bare `cat` (line 2018); an `eval` source returns `None`, so the text it prints is never read. For `eval` itself (line 2005) `shell_text` returns the text eval runs alone, without the pipe that is eval's stdin, so a shell in that text that reads stdin is read as a shell with no input.

## What Changes

- The source of a pipe into a shell may be `eval`: it prints what each segment of its text not piped on prints, read by the same rules as today's sources; `eval echo env | sh`, `eval echo printenv | bash`, `eval 'echo env' | sh`, `eval echo env | tee | sh` and `eval 'echo env; true' | sh` are refused with the existing reason "The command prints the whole environment or a secret".
- The text `eval` runs keeps the pipe into it: the pipe is put before the first segment head of the text that reads input (a shell that reads its commands from stdin, `tee`, a bare `cat`, an `eval` whose own text has such a head, and an `eval` past three levels), so `echo env | eval sh`, `echo env | eval 'true; sh'`, `echo env | eval 'cat | sh'`, `printf env | eval eval sh`, `echo env | eval 'eval true; sh'` and `echo env | eval eval eval eval sh` are refused.
- An `eval` source fed by a pipe is read with what the pipe carries, and past three `eval` levels by the dump words of the pipeline before it: `echo env | eval cat | sh`, `echo env | eval tee | sh`, `eval echo env | eval sh` and `echo env | eval cat | eval cat | eval cat | eval cat | sh` are refused.
- `eval echo hi | sh`, `echo ls | eval sh`, `echo ok | eval cat`, `echo env | eval true` and `eval "echo 'env" | sh` (an open quote: bash's `eval` runs nothing) still pass.
- `env_read` reads the same `shell_text`, so `eval echo cat .env | sh` is refused as a `.env` read, as `echo cat .env | sh` is today; the requirement Secret file reads in Bash already covers it.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirement Environment dumps refused (scenario eval in a pipe into a shell).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/eval-pipe-env.py`

## Out of Scope

- `|&` and a newline after `|` as a pipe into a shell (`echo env |& sh`): the pipe walk of `shell_text` reads neither for any source, `echo` included; a change of its own.
- Brace groups, subshells and compound commands inside an `eval` text or as a pipe source (`eval '{ echo env; }' | sh`, `{ echo env; } | sh`): an `eval` text is read as the same text outside `eval` is read today.
- A program in the `eval` text that runs its input or arguments (`xargs`, an interpreter): already a listed known bypass outside `eval`.
- A trailing backslash in an `eval` text (`echo env | eval 'sh \'`): the command is not plain, and `dump_text` refuses it today; `shell_text` does not read it.
- `.env` words past three `eval` levels of a pipe: `env_read` keeps its own depth rule.
- `archive_runs`, `cmd_start` and `dump_text`: other readers, unchanged.

## Depends On

- fix-env-runs-env

## Source

No owner quote names this bug: it came from the session that closed `fix-env-runs-env`. Its task to this session (2026-11-26): "the Bash guard of `global/work_hooks.py` lets through `eval echo env | sh`, `eval echo printenv | bash`, `eval 'echo env' | sh` and `echo env | eval sh` (all pass on main after PR #94 ...). Cause: `shell_text` reads only `echo`, `printf`, `tee` and a bare `cat` as the source of a pipe into a shell, and a shell run by `eval` that reads stdin is not recognised."
