# Proposal

## Why

The secret guard can switch itself off. `guard_env_write`, `guard_env_read` and `guard_secrets_bash` run inside `cmd_guard` of `global/work_hooks.py`, and `main()` catches every `Exception` there, writes it to `errors.log` and returns 0, so a check that raises lets a `.env` read or an environment dump through. The settings entry adds a second gap: `solo_sdd/hooks.py` connects `guard` by `_cmd("guard", timeout=10)` without `onFailure`, so a crash before `main()` (an import error, a broken copy) or the 10-second timeout also passes, while `process-guard.py` is connected with `"onFailure": "block"`. The `DENY` list (`Read(**/.env)` in `permissions.deny`) covers the `Read` tool only, not a read through Bash or an environment dump.

Both gaps follow a project rule, `AGENTS.md`: "Hooks are fail-open: an internal error lets the action through". The owner chose the other side for the guard on 2026-11-26 (Source): a secret leak costs more than a blocked call. This change narrows the rule and does not drop it: only the secret checks and the guard entry as a whole fail closed; the model, merge, worktree, archive, handback and question checks keep failing open as the requirements Status check on handback and Checks without the policy say.

## What Changes

- An exception inside `guard_env_write`, `guard_env_read` or `guard_secrets_bash` gives a `deny` answer that names the failed check and `errors.log`, and is still written to `errors.log`; an exception in any other check keeps passing.
- `install --hooks` connects the `guard` entry with `onFailure: "block"` next to its 10-second timeout, so a crash before `main()` and a timeout refuse the call; a settings file with the earlier entry gets the new one on the next `install --hooks`.
- A missing `work_hooks.py` or a missing `/usr/bin/python3` still passes (`G` in `solo_sdd/hooks.py` checks both before `exec`): that is the state after `uninstall` or on a machine without the interpreter, not a failure of the guard.
- The rule line of `AGENTS.md`, the docstring of `global/work_hooks.py`, the `DENY` comment of `solo_sdd/hooks.py` and `docs/hooks.md` name the exception.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: ADDED requirement Secret checks fail closed.
- `cli`: ADDED requirement Guard entry fails closed.

## Impact

- `global/work_hooks.py`
- `solo_sdd/hooks.py`
- `tests/test_work_hooks.py`
- `tests/test_cli.py`
- `docs/hooks.md`
- `AGENTS.md`

## Out of Scope

- The other checks of `guard` and the other `work_hooks.py` subcommands: they keep failing open.
- The 5-second timeout of `sh()`, which returns empty output: a check that reads empty git output decides as it does today.
- An agent deleting `work_hooks.py` or editing the settings entry: the guard does not guard itself.
- Codex hooks (`codex_need()`): whether Codex has a failure field is not checked here.
- Neighbouring changes of this plan: `codex-user-only-skills`, `history-guard`, `lesson-gate`.

## Depends On

none

## Source

The owner, 2026-11-26, on the comparison of solo-sdd with mattpocock/skills, skyremote/chief-of-staff-kit and davidondrej/skills (translated from Russian): "well, since you singled them out, make the changes". The item of that comparison the owner answered (translated): "`guard` in work_hooks does not block on a failure: `process-guard` has `onFailure: "block"`, while `guard` is called as `_cmd("guard", timeout=10)` without the field; if `work_hooks.py` crashes or times out, the secret guard lets the command through. I would block: secrets matter more than downtime."
