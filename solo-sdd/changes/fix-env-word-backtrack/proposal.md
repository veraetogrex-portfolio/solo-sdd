# Proposal

## Why

The secret check of the `guard` hook takes quadratic time on a long token without a space or a `/`, so such a command is now decided by the hook's 10-second timeout (refused since `guard-fails-closed`, PR #103) instead of by the check, and before PR #103 it passed.

Reproduction (2026-11-27, `/usr/bin/python3`, the module loaded from `global/work_hooks.py`): `guard_secrets_bash("echo " + "$(" * n, ".", same)` → expected: an answer in well under a second → got: 0.33 s at n = 4,000 and 1.06 s at n = 8,000 (four times the time for twice the input); the orchestrators of `guard-fails-closed` and `history-guard` measured about 75 s and 103 s at 50,000 `$(`.

Cause: `ENV_FILE` (`global/work_hooks.py:35`) opens with the optional folder prefix `(?:[^\s;&|'"<>]*/)?`; `ENV_WORD` (`:1966`) puts only `(?<![\w/.-])` before it, so every `$` and `(` is a start position, and from each one the class run scans to the token's end and backtracks looking for a `/`. `guard_secrets_bash` searches it over the whole command twice (`ENV_WORD.search(raw) or ENV_WORD.search(flat(raw))`, `:2486`); a profile at n = 8,000 puts 1.06 s of the 1.06 s in those `search` calls.

## What Changes

- Every `.env` name search over Bash text (each `ENV_WORD.search` call and the `git add` search) runs in time linear in the text's length: candidates are taken only around each occurrence of `.env` (found by `re.finditer` of the literal, case-insensitive, on the original text), and each is tested by that caller's own pattern and flags on its token, so the set of names each caller matches stays the same by construction. `ENV_FILE` and its fullmatch callers (Read, Grep, Write, the folder scan) do not change.
- The secret check decides a 50,000-repeat token within 2 seconds; the whole hook, whose `shlex` word splitting stays quadratic, answers such a command within 8 seconds, before its 10-second timeout.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: requirement Secret file reads in Bash gains the scenarios A long token answered in time and Names kept by the faster search; the command-guards scenario A plain expansion is not plain for the secret guard keeps its verdict (a kept row).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`

## Out of Scope

- The 1-second timing assertion of `test_environment_dumps_refused_hostile_input` that failed under parallel load twice on 2026-11-26: its assertion stays; if this fix makes it pass under load, the report says so.
- The quadratic `shlex` word splitting of `split_words` (`global/work_hooks.py:1477`), measured by the repeat analysis at about 4.3-4.9 s of the hook's run on `echo ` + 50,000 `$(` with both `.env` searches made linear: a change of its own; this change bounds the whole hook at 8 seconds only.
- Other quadratic patterns (`REDIRECT` matched per word, `CHANGE_FILE`).
- `fix-guard-spaced-assignment` and `fix-pipe-walk-compound` (another session) also edit `global/work_hooks.py`; the dispatcher runs them one at a time.

## Depends On

- fix-pipe-walk-compound

## Source

The owner, 2026-11-27: `/spec-plan`, given right after the dispatcher report that named this open item (translated from Russian): "the secret guard's regular expression slows down quadratically on long `$(` nesting, and such commands now run into the 10-second timeout".
