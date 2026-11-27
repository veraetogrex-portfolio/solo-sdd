# Proposal

## Why

The `guard` hook lets through plain Bash commands whose pipe walk misses the shell grammar of a compound command, a `-c` string, a glued redirection, a subshell source and `case`, and each prints the whole environment, though the requirement Environment dumps refused says a command that runs `env` or `printenv` without arguments, alone or in a pipe, is refused. Two `eval --` forms likewise slip past the archive and merge guards. Found 2026-11-26 by the independent reviewer of `fix-pipe-walk-env` (PR #105) as Pre-existing on its base and branch.

Reproduction (2026-11-26, main 17c3c00, `env_dump(command_text(cmd))`, `archive_runs` and `gh_merges` of `global/work_hooks.py`, run from script files): `echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | case x in x) sh;; esac`, `echo env | sh -c sh`, `echo env | sh>out`, `echo env | (sh)>out`, `echo env | (sh)2>/dev/null`, `echo env | (cat) | sh`, `echo env | (eval cat) | sh` and `case x in x) env;; esac` pass → expected to be refused; in zsh (the shell of Claude Code's Bash tool) each runs the piped text as commands. `eval -- solo-sdd archive foo` gives no archive run and `eval -- gh pr merge 1` no merge → expected the run `foo` and a merge, as `eval solo-sdd archive foo` and `eval gh pr merge 1` give.

Cause:
- `global/work_hooks.py:2147` (`shell_text`) and `2128` (`piped_text`): what reaches a command's stdin is read only from a `|` right before it, so a command inside a compound that a pipe feeds (`(true; sh)`, `if …; then sh; fi`) gets nothing, and a `cat` or `tee` whose stdin is a compound's stops the walk.
- `global/work_hooks.py:2027` (`part_words`): a redirection glued after text (`sh>out`) is kept as one word unless its target is a `.env` file, so the program word is `sh>out`; a `)` is cut only by `subshell_end` (line 2066), one per `(` in the same part, so `sh)` in `(true; sh)` and `cat)` in a pipe source keep it, and no reader follows a compound's stdin or output across its parts.
- `global/work_hooks.py:2145` (`shell_text`): a shell's `-c` string is returned without what is piped into the shell, though the string's commands read the shell's stdin, as `eval`'s text does (`eval_text`).
- `global/work_hooks.py:2265` (`env_dump`): the program word of a `case` item follows its pattern's `)`, so `case` is read as the program.
- `global/work_hooks.py:1749` and `2640` (`archive_runs`, `gh_merges`): eval's words are taken from right after `eval`, so its `--` is read as the program word.

## What Changes

- A redirection glued after text is no part of the word before it, as the shell reads it (`part_words`): `echo env | sh>out`, `echo env | sh&>out` and `echo env | (sh)>out` are refused with the existing reason "The command prints the whole environment or a secret"; `echo ls | sh>out` passes.
- `archive_runs` and `gh_merges` read eval's words past one `--` (`eval_words`): `eval -- solo-sdd archive foo` is an archive run of `foo` and `eval -- gh pr merge 1` a merge, refused by the existing CLAIM, review and merge reasons; through the shared `gh_merges` the history guard reads `eval -- git push --force` too, as it reads `eval git push --force`.
- The other forms of the report, a pipe into or out of a compound command or into a shell's `-c` string (`echo env | (true; sh)`, `echo env | (cat) | sh`, `echo env | sh -c sh`, `echo env | (sh)2>/dev/null`) and a case item's program (`case x in x) env;; esac`), are named in `docs/hooks.md` as known bypasses of the Bash guard and pinned by its known-bypass test: the guard is an accident guard, an agent does not write these forms by accident, and reading them needs a parser of the shell's compound grammar (two attempts with 11 review rounds each opened new misses in it).
- The stand `tests/stands/pipe-walk-compound.py` runs steps 1-3 of the Live Scenario: the real hook by its entry point on the base 17c3c00 and on the branch.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirement Environment dumps refused (scenario a redirection glued to the shell word) and MODIFIED requirement Known bypasses of the Bash guard (the pipe-walk forms named; its text shortened to the 500-character limit, the list moved into a scenario).
- `work-hooks-subagents`: MODIFIED requirements Direct merge refused in a process tree and Archive run behind runners and options (scenario `eval --`).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/pipe-walk-compound.py`
- `docs/hooks.md`

## Out of Scope

- Reading a compound command, a shell's `-c` string as a pipe sink or source, and a case statement in the pipe walk: known bypasses (What Changes), decided by the owner on 2026-11-27 after two attempts.
- `tee >(sh)`, a here-string feeder (`sh <<< env`), `source /dev/stdin`, text filters other than `tee` and a bare `cat` piped into a shell: passes on the base and the branch.

## Depends On

none

## Source

No owner quote names this bug: it came from the session that closed `fix-pipe-walk-env`. Its task to this session (2026-11-26): "These forms pass the guard on main 17c3c00 and run the piped text as commands (checked in zsh with a harmless payload): a pipe into a compound command or a `-c` string (`echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | case x in x) sh;; esac`, `echo env | sh -c sh`); a redirection glued to the shell word or a subshell `)` (`echo env | sh>out`, `echo env | (sh)>out`, `echo env | (sh)2>/dev/null`); `piped_text` not walking through a `cat`, `tee` or `eval` inside a subshell (`echo env | (cat) | sh`, `echo env | (eval cat) | sh`); `case x in x) env;; esac` (the pattern's `)` hides the program). Also `eval -- solo-sdd archive foo` and `eval -- gh pr merge 1` are missed by `archive_runs` and `gh_merges` (reuse `eval_words`)."
