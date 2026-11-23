# Proposal

## Why

The `guard` hook refuses commands that print no environment with "The command prints the whole environment or a secret". Seen in the week 16-22.11.2026: 16.11 (…2c6d96) `grep -n "secret\|printenv\|env |echo \$" skills/debug-profile/SKILL.md`; 17.11 (…e54b02, in `~/Code/_sandbox/advance-report`) a line holding `"$(git -C $M status --short)"` and then `(cd /tmp && env -i HOME=$HOME PATH=/usr/bin:/bin python3 $M/src/report.py … < /dev/null | tail -4)`; 21.11 (…009887) `grep -n "…\|env\[" global/sdd_eval.py`. Each time the agent dropped or rewrote the command.

Reproduction (2026-11-23, base commit 286817e, the real hook by its entry point): `grep -n "secret\|printenv\|env |echo \$" skills/debug-profile/SKILL.md`, `grep -n "foo\|env\[" global/sdd_eval.py` and `echo "$(date)"; env X=1 python3 -V` are refused → expected to pass. The `env -i` line alone passes; it is refused only next to the `$(…)`.

Cause: `global/work_hooks.py:2163`, `guard_secrets_bash`: a command holding any of `NOT_PLAIN` (`#`, `$'`, `${`, `$(`, a backquote, a backslash) is not read by the parser, and `DUMP_WORDS` (line 2053) is searched over the whole raw text, so `env` or `printenv` inside a grep pattern, and `env` that runs a program, count as a dump.

## What Changes

- In a command that is not plain, a dump word inside a single- or double-quoted argument of `grep` or `rg` is text and does not count, unless that argument holds `$(` or a backquote.
- In such a command, the `env` word, its options with their values (`-i`, `-u <name>`, `-C <dir>`), its assignments and its program word do not count when that program is not itself a dump word; a dump word after them still counts.
- `env`, `env | grep TOKEN`, `printenv`, `export -p`, `grep x "$(env)"`, `env -i printenv`, `env -u X printenv`, `env X=1 xargs printenv` and the scripts of `sed` and `awk` stay refused next to a substitution.
- The exemption applies only where the hook reads the quoting as the shell does: no cut when `#` or `$'` stands outside the quoted argument, an open quote or a trailing backslash refused, an escaped quote read as one argument; a 100 KB pattern is answered within 1 s.
- `docs/hooks.md` names the exemption in place of its sentence that a non-plain command holding `env` is refused anywhere, quoted text included.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirement Environment dumps refused.

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `docs/hooks.md`

## Out of Scope

- `awk 'BEGIN{system("env")}'`, `env -u X printenv` and `env -C /tmp printenv` in a plain command already pass (found 2026-11-23 while reproducing and by the analysis judge: `cmd_start` skips `-u` but not its value): a separate change, not this one.
- The scripts of `sed` and `awk`, which the owner's item also named: their `e` command, `getline` and `system(` run programs, so they stay refused next to a substitution.
- Reading non-plain commands with the full parser: a larger change of the guard.
- Neighbouring changes of this plan: `action-first-project-repo`, `worktree-add-quiet`, `plan-input-skill`.

## Depends On

none

## Source

The owner, 2026-11-23, on the decisions of the weekly review of 16-22.11 (translated from Russian): "all except the proxy, yes", then "do it". Item D of the owner's input file "2026-11-23 input for spec-plan" (name translated): "In the non-plain fallback, a dump word inside a quoted argument of `grep`, `rg`, `sed`, `awk` is text; `env -i …` and `env NAME=value … <program>` run a program and print nothing."
