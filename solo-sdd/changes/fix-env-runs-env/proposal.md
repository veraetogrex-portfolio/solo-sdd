# Proposal

## Why

The `guard` hook lets through a plain Bash command in which `env` runs a second `env`, and that command prints the whole environment, though the requirement Environment dumps refused says a command that runs `env` without arguments is refused. Found 2026-11-26 by the orchestrator and the reviewer of `fix-env-dump-valued-options` (PR #89) as present on both its base and its branch.

Reproduction (2026-11-26, commit 58c1d41, the real hook by its entry point `python3 global/work_hooks.py guard` with a PreToolUse JSON, run from a script file): `env env`, `env -i env`, `env -u X env`, `env FOO=1 env`, `env env -i`, `/usr/bin/env env`, `env /usr/bin/env` and `sudo env env` pass → expected to be refused; `env env ls`, `env -i env HOME=/x true` and `env env printenv HOME` pass, as expected. The non-plain form `echo "$(date)"; env env` is already refused by the fallback of `dump_text`.

Cause: `global/work_hooks.py:2160`, `env_dump`: `cmd_start` skips every wrapper word, so in `env env` both words are skipped and no program word is left; the dump check then takes the first `env` before the program word (`e = next(...)`) and asks `env_alone` whether only options and assignments follow it, which fails on the second `env`. The last `env` before the program word, whose rest holds only options and assignments, is the one that prints the environment. A probe of `env_dump` with the last `env` taken refuses every form above and still passes `env env ls`, `env -i env HOME=/x true` and `env env printenv HOME`.

The same reading also refuses `env -S env`, listed today as a known bypass (the split string of `env -S`): the guard reads the split string as one word, so a split string that is one dump word is now refused, while one that holds a space (`env -S 'A=1 env'`) is no dump word and still passes; that example replaces `env -S env` in the known bypass.

## What Changes

- `env_dump` takes the last `env` before the program word, not the first: `env env`, `env -i env`, `env -u X env`, `env FOO=1 env`, `env env -i`, `/usr/bin/env env`, `env /usr/bin/env`, `sudo env env`, `timeout 5 env env`, `env "env"`, `env -- env`, `env -uX env`, `env --unset=X env`, `printf x | env env` and `env -S env` are refused with the existing reason "The command prints the whole environment or a secret".
- `env env ls`, `env -i env HOME=/x true` and `env env printenv HOME` still pass; in a command that is not plain, `dump_text` reads a nested `env` on as `env`, so `echo "$(date)"; env env ls`, refused today, passes.
- The known bypass of the split string of `env -S` keeps its place in `docs/hooks.md`, with the example `env -S 'A=1 env'` instead of `env -S env`, which is now refused.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirements Environment dumps refused (scenario env runs env) and Known bypasses of the Bash guard (the `env -S` example of the scenario An interpreter prints the environment).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/env-runs-env.py`
- `docs/hooks.md`

## Out of Scope

- `eval` as the source of a pipe into a shell and a shell run by `eval` that reads stdin (`eval echo env | sh`, `eval 'echo env' | sh`, `echo env | eval sh` pass on 58c1d41): `shell_text` reads only `echo`, `printf`, `tee` and a bare `cat` as the source; a change of its own.
- `archive_runs` without the other wrappers' valued options and the glued forms: the archive guard of `work-hooks-subagents`, a change of its own.
- `SUDO_VALUED` holding `-h`: sudo's `-h` alone is its help, so `sudo -h host printenv` prints the help, not the environment; the refusal it gives today is a false refusal of a form nobody runs, not a bypass, and stays as it is.
- The split string of `env -S` (`env -S 'A=1 env'`): stays a listed known bypass.
- A change of `cmd_start` itself: shared with `global/process-guard.py`.
- The open changes `guard-fails-closed` and `history-guard`, which edit the same files: neither modifies a requirement this change modifies.
- The text of the Known bypasses requirement: only its `env -S` item narrows to a split string with a space, the rest is unchanged.

## Depends On

none

## Source

No owner quote names this bug: it came from the orchestrator and the reviewer of `fix-env-dump-valued-options`. The task of the starting session to this session (2026-11-26): "closes a dump bypass in the Bash guard of `global/work_hooks.py` (`guard_secrets_bash`, `DUMP_WORDS`, the env wrapper handling): a second `env` run by `env` (`env env`, `env -i env`, `env -u X env`) passes the guard and prints the whole environment."
