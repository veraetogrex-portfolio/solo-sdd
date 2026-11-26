# Proposal

## Why

The `guard` hook lets through plain Bash commands whose pipe walk misses the shell grammar of a compound command, a `-c` string, a glued redirection, a subshell source and `case`, and each prints the whole environment, though the requirement Environment dumps refused says a command that runs `env` or `printenv` without arguments, alone or in a pipe, is refused. Two `eval --` forms likewise slip past the archive and merge guards. Found 2026-11-26 by the independent reviewer of `fix-pipe-walk-env` (PR #105) as Pre-existing on its base and branch.

Reproduction (2026-11-26, main 17c3c00, `env_dump(command_text(cmd))`, `archive_runs` and `gh_merges` of `global/work_hooks.py`, run from script files): `echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | case x in x) sh;; esac`, `echo env | sh -c sh`, `echo env | sh>out`, `echo env | (sh)>out`, `echo env | (sh)2>/dev/null`, `echo env | (cat) | sh`, `echo env | (eval cat) | sh` and `case x in x) env;; esac` pass → expected to be refused; in zsh (the shell of Claude Code's Bash tool) each runs the piped text as commands. `eval -- solo-sdd archive foo` gives no archive run and `eval -- gh pr merge 1` no merge → expected the run `foo` and a merge, as `eval solo-sdd archive foo` and `eval gh pr merge 1` give.

Cause:
- `global/work_hooks.py:2147` (`shell_text`) and `2128` (`piped_text`): what reaches a command's stdin is read only from a `|` right before it, so a command inside a compound that a pipe feeds (`(true; sh)`, `if …; then sh; fi`) gets nothing, and a `cat` or `tee` whose stdin is a compound's stops the walk.
- `global/work_hooks.py:2027` (`part_words`): a redirection glued after text (`sh>out`) is kept as one word unless its target is a `.env` file, so the program word is `sh>out`; a `)` is cut only by `subshell_end` (line 2066), one per `(` in the same part, so `sh)` in `(true; sh)` and `cat)` in a pipe source keep it.
- `global/work_hooks.py:2145` (`shell_text`): a shell's `-c` string is returned without what is piped into the shell, though the string's commands read the shell's stdin, as `eval`'s text does (`eval_text`).
- `global/work_hooks.py:2265` (`env_dump`): the program word of a `case` item follows its pattern's `)`, so `case` is read as the program.
- `global/work_hooks.py:1749` and `2640` (`archive_runs`, `gh_merges`): eval's words are taken from right after `eval`, so its `--` is read as the program word.

## What Changes

- A `)` that closes a subshell ends the words of a command, wherever its `(` opened, and only the subshell's redirections follow it (`(cat) < .env`): a quoted or escaped `(` or `)` is text, and only a leading `(` at the head of a command opens a subshell, so the `(` of a glob (`!(x)`, `*(N)`), an array (`A=(1 2)`), zsh's `=(…)` or a substitution's `()` opens a group its `)` closes, also in a later word; `subshell_end` goes; `echo env | (cat) | sh` and `echo env | (eval cat) | sh` are refused with the existing reason "The command prints the whole environment or a secret".
- A redirection glued after text (`sh>out`, `sh&>out`, `(sh)>out`, `(sh)2>/dev/null`) is no part of the word before it, as the shell reads it: each such form after `echo env |` is refused.
- What a pipe into a compound command (a subshell, a `{ }` group, `if`, `while`, `until`, `case`, `for`, `select`) carries reaches every command in it that reads its stdin, and what a compound prints into a pipe is what each of its commands not piped on prints: `echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | (true; cat) | sh`, `echo env | (cat; true) | sh`, `echo env | { cat; } | sh` and `{ echo env; } | sh` are refused. The nesting is read once per command across its parts (`(`, `{`, `if`, `while`, `until`, `for`, `select` open, a subshell's `)`, `}`, `fi` and `done` close, a case's patterns are not read), so `echo env | (true); sh` passes: `sh` reads the outer stdin. A nesting that does not read to its end (a close without its open, an open or a case left) leaves every dump word and every `.env` name of the command counted, as a form the parser cannot read. Each part's printed text is found once per command and joined texts keep each line once, so a chain of compounds costs linear time.
- A shell's `-c` string is read like `eval`'s text, with what is piped into the shell: `echo env | sh -c sh` and `echo env | sh -c 'cat | sh'` are refused, and `echo env | sh -c cat | sh` is refused as a source.
- A `case` at a command position counts every dump word and every `.env` name from it to the last `esac` and in what feeds it, at each depth of `eval`, a `-c` string and a substitution: `case x in x) env;; esac` and `echo env | case x in x) sh;; esac` are refused, and `case x in x) cat .env;; esac` stays a `.env` read; `case x in x) grep env f;; esac` is refused too, a refusal on the safe side, while `case x in x) true;; esac; echo 'API_KEY=' >> .env` passes as on the base.
- `archive_runs` and `gh_merges` read eval's words past one `--` (`eval_words`): `eval -- solo-sdd archive foo` is an archive run of `foo` and `eval -- gh pr merge 1` a merge, refused by the existing CLAIM, review and merge reasons.
- `echo ls | (true; sh)`, `echo ls | sh -c sh`, `echo ls | sh>out`, `echo ls | (cat) | sh`, `case x in x) ls;; esac`, `echo env | (true; sh ')')` (sh runs the script `)`) `echo env | (cat) > out`, `echo env | (true); sh`, `echo ls | (cat; true) | sh` and `A=(1 2) /usr/bin/env gh pr merge 5` (a known merge bypass) still pass.
- `env_read` reads the same `part_words` and `shell_text`, so `echo cat .env | (true; sh)`, `echo cat .env | sh>out`, `(cat <.env)` and `cat *(N) .env` are refused as `.env` reads, and `(cat) < .env`, refused on the base, stays refused; the requirement Secret file reads in Bash already covers them.
- The stand `tests/stands/pipe-walk-compound.py` runs steps 1-3 of the Live Scenario: the real hook by its entry point on the base 17c3c00 and on the branch.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirement Environment dumps refused (scenario compound commands, `-c` strings, glued redirections and `case` in a pipe).
- `work-hooks-subagents`: MODIFIED requirements Direct merge refused in a process tree and Archive run behind runners and options (scenario `eval --`).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/pipe-walk-compound.py`

## Out of Scope

- `tee >(sh)`: a process substitution fed by `tee` (`echo env | tee >(sh)`) passes on the base and the branch; a change of its own.
- The kind of a close: the nesting counts opens and closes, not which opener a `fi` or `done` ends; a misnested text that still balances is read by its count.
- A here-string feeder (`sh <<< env`, `(cat) <<< env | sh`): passes on the base and the branch; a change of its own.
- `case` read item by item: its patterns' `)` and `|` would need their own grammar; the whole command is counted instead.

## Depends On

none

## Source

No owner quote names this bug: it came from the session that closed `fix-pipe-walk-env`. Its task to this session (2026-11-26): "These forms pass the guard on main 17c3c00 and run the piped text as commands (checked in zsh with a harmless payload): a pipe into a compound command or a `-c` string (`echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | case x in x) sh;; esac`, `echo env | sh -c sh`); a redirection glued to the shell word or a subshell `)` (`echo env | sh>out`, `echo env | (sh)>out`, `echo env | (sh)2>/dev/null`); `piped_text` not walking through a `cat`, `tee` or `eval` inside a subshell (`echo env | (cat) | sh`, `echo env | (eval cat) | sh`); `case x in x) env;; esac` (the pattern's `)` hides the program). Also `eval -- solo-sdd archive foo` and `eval -- gh pr merge 1` are missed by `archive_runs` and `gh_merges` (reuse `eval_words`)."
