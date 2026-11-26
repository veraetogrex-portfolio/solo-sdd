# Proposal

## Why

The `guard` hook lets through plain Bash commands that pipe text into a shell or hand it to `eval` in forms of the shell grammar its pipe walk does not read, and each prints the whole environment, though the requirement Environment dumps refused says a command that runs `env` or `printenv` without arguments, alone or in a pipe, is refused. Found 2026-11-26 by the independent reviewer of `fix-eval-pipe-env` (PR #99) as Pre-existing on its base and branch.

Reproduction (2026-11-26, main 5549bc4, `env_dump(command_text(cmd))` of `global/work_hooks.py` and the real hook by its entry point, run from script files): `echo env |& sh`, `echo env |` followed by a newline and `sh`, `eval -- env`, `echo env | eval -- sh`, `echo env | (sh)`, `echo env | ( sh )` and `echo env | (eval sh)` pass → expected to be refused. In zsh (the shell of Claude Code's Bash tool) each prints the whole environment (89 lines); in bash and dash all but `|&` (bash 3.2 and dash have no `|&`) and, in dash, the two `eval --` forms do.

Cause:
- `global/work_hooks.py:1360`, `split_cmd`: `|&` is split into the parts `|`, an empty part and `&`, and a newline after `|` into `|`, an empty part and a newline, so the shell part is never preceded by a `|` and `shell_text` (line 2063) never reads the pipe into it.
- `global/work_hooks.py:2021` and `2012`, `eval_text` and `reads_input`: the words after `eval` are its text, so `--`, which ends `eval`'s options in bash and zsh, is read as the program word of the text.
- `global/work_hooks.py:2063` and `2010`, `shell_text` and `reads_input`: the program word is taken with a glued subshell end (`(sh)` gives `sh)`), and a separate `)` after it is read as an argument of the shell, so a shell in a subshell is no shell that reads its commands from stdin.

## What Changes

- `split_cmd` reads `|&` as a pipe (`|`, its `&` kept as a space in the next part so every offset into the text stays) and keeps a newline after `|` or `|&` in the next part: the pipeline goes on, as the shell reads it; `echo env |& sh`, `echo env |& bash -s` and `echo env |` + newline + `sh` are refused with the existing reason "The command prints the whole environment or a secret".
- A `--` right after `eval` ends its options and is not part of its text: `eval -- env` and `echo env | eval -- sh` are refused.
- A subshell end ends the words of the command in it: every `)` glued to the program word is cut from it, and a `)` word ends the shell's words, in `shell_text` and in the reading heads of an `eval` text; `echo env | (sh)`, `echo env | ( sh )`, `echo env | ( (sh))` and `echo env | (eval sh)` are refused.
- `echo ls |& sh`, `echo ls |` + newline + `sh`, `eval -- ls`, `echo ls | eval -- sh` and `echo ls | (sh)` still pass.
- Every other reader of `split_cmd` sees the same pipeline as the shell: `runs_text` (through `strip_heredocs` and `strip_patterns`), `codex_launches`, `archive_runs`, the worktree and `gh` merge guards and the copy of the shell block in `global/process-guard.py` get `|&` as `|` with the next command and no empty part after a pipe; `echo "$(date)"; grep "env" f |& cat` still passes, as `| cat` does.
- The stand `tests/stands/pipe-walk-env.py` runs steps 1-3 of the Live Scenario: the real hook by its entry point on the base 5549bc4 and on the branch.
- `env_read` reads the same `split_cmd` and `shell_text`, so `echo cat .env |& sh` is refused as a `.env` read, as `echo cat .env | sh` is today; the requirement Secret file reads in Bash already covers it.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirement Environment dumps refused (scenario pipe and eval forms of the shell grammar).

## Impact

- `global/work_hooks.py`
- `global/process-guard.py`
- `tests/test_work_hooks.py`
- `tests/stands/pipe-walk-env.py`

## Out of Scope

- A newline after `&&` or `||`: the command after it is read as a command of its own today, so no dump is missed.
- A comment or a backslash continuation between `|` and the next command: the command is not plain, and `dump_text` already counts any dump word in it.
- A `)` glued to a source of the pipe (`(cat) | sh`, `echo env | (cat) | sh`): `piped_text` reads only `echo`, `printf`, `tee`, a bare `cat` and `eval` today; a change of its own if wanted.
- A newline after `|` in a command that is not plain: `dump_text` reads it by its own segments, so `echo "$(date)"; grep "env" f |` + newline + `cat` stays refused (probed 2026-11-26 on the base and the prototype), a false refusal on the safe side; `| cat` and `|& cat` pass.
- The `eval` handling of `codex_launches` and `archive_runs`: other readers, unchanged.

## Depends On

- fix-eval-pipe-env
- fix-archive-runs-command-values

## Source

No owner quote names this bug: it came from the session that closed `fix-eval-pipe-env`. Its task to this session (2026-11-26): "`echo env |& sh`, `echo env |` followed by a newline and `sh`, `eval -- env`, `echo env | eval -- sh` and `echo env | (sh)` all pass the guard on main 5549bc4 and print the whole environment. Cause: `split_cmd` yields `|`, ``, `&` for `|&` and a separate newline part after `|`, so the walk never sees a pipe; `eval`'s `--` is taken as part of its text; a subshell glued to the shell word hides the program word."
