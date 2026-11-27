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

- A pipe next to a compound command (a part after `|` with a word starting with `(` or an opening keyword: `{`, `if`, `while`, `until`, `for`, `select`, `case`, `coproc`; or a part before `|` with a word ending in `)` or a closing keyword: `}`, `fi`, `done`, `esac`), in a command with a part that runs a program reading commands from its stdin (a shell without a script or with `-s` whose stdin is not redirected from a file, a heredoc or a here-string, as `redirections`, the parse `part_words` reads, gives the last redirection of fd 0 (a dup such as `<&3`, a process substitution, a `/dev/` or `/proc/` path once normalised, or a target the shell expands, `~`, `$F`, `/[d]ev/stdin`, `/{d..d}ev/stdin`, `/(dev)/stdin`, keeps the pipe), or an `eval` or a shell's `-c` string whose text has such a part; each part read as the walk reads a command, by `part_words`, `wrapper_values_cut`, `cmd_start` and `handed_text`, with its unquoted closing brackets and an fd glued after one cut from its end in one linear scan; and a `-c` or `eval` text with a word `case`), counts every dump word and every `.env` name of the command: the commands of a compound share its stdin and its output, and the walk does not read the nesting. `echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | case x in x) sh;; esac`, `echo env | (sh)>out`, `echo env | (sh)2>/dev/null`, `echo env | (cat) | sh`, `echo env | (eval cat) | sh`, `echo env | (cat; true) | sh`, `{ echo env; } | sh`, `echo env | time (sh)`, `echo env | coproc (sh)`, `echo env | (true; sh&>out)` and `{ echo env; }&>/dev/stdout | sh` are refused with the existing reason "The command prints the whole environment or a secret". The rule reads each part's words once, so its cost is linear. It refuses `echo env | (true); sh` and `echo env | ( true ) | sh` too, refusals on the safe side.
- A redirection glued after text (`sh>out`, `sh&>out`) is no part of the word before it, as the shell reads it: `echo env | sh>out` is refused, and a `)` after a redirection's target (`(cat <.env)`) is no part of the target.
- A shell's `-c` string is read like `eval`'s text, with what is piped into the shell, and when no head of such a text reads its input but the text runs a program reading commands from stdin, the piped text goes into its first head that runs such a program or opens a compound command: `echo env | sh -c sh`, `echo env | sh -c 'cat | sh'`, `echo env | sh -c 'true; (true; sh)'`, `echo env | eval 'true; (true; sh)'`, `echo env | sh -c 'case x in x) sh;; esac'` and `echo env | eval "sh -c 'case x in x) sh;; esac'"` are refused. A subshell's `)` glued to a redirection's target ends the compound too: `(echo env; true 2>/dev/null) | sh` is refused.
- A command with a word `case` counts every dump word and every `.env` name of the command, at each depth of `eval`, a `-c` string and a substitution, as its patterns' `)` and `|` hide the program after them (the rule the main spec already applies to a command that is not plain): `case x in x) env;; esac` is refused and `case x in x) cat .env;; esac` stays a `.env` read; `case x in x) grep env f;; esac` and `case x in x) true;; esac; test -f .env && echo y` are refused too, refusals on the safe side, while `grep "env" f; case x in x) true;; esac` passes (the search pattern is cut first) and `case x in x) ls;; esac` passes.
- `archive_runs` and `gh_merges` read eval's words past one `--` (`eval_words`): `eval -- solo-sdd archive foo` is an archive run of `foo` and `eval -- gh pr merge 1` a merge, refused by the existing CLAIM, review and merge reasons.
- `echo ls | (true; sh)`, `echo ls | sh -c sh`, `echo ls | sh>out`, `echo ls | (cat) | sh`, `case x in x) ls;; esac`, `echo ls | (true; sh ')')`, `echo env | (true; sh ')')` (sh runs the script `)`), `echo env | (cat) > out`, `(cd app && bash build.sh) 2>&1 | tail -5; test -f .env && echo ok` (a shell that runs a script reads no commands from stdin), `echo ls | (cat; true) | sh`, `A=(1 2) /usr/bin/env gh pr merge 5` (a known merge bypass) and `ls >(cat ')' .env)` (a known Bash bypass) still pass.
- `env_read` reads the same rules, so `echo cat .env | (true; sh)`, `echo cat .env | sh>out`, `echo cat .env | (true; sh <//dev/stdin)` and `(cat <.env)` are refused as `.env` reads, and `(make) | tail; sh; test -f .env && echo ok` is refused on the safe side: a new scenario of the requirement Secret file reads in Bash names it. A here-string or a heredoc is never the pipe, so `( bash <<<"make $T" ) | tail -3; grep -c '^KEY=.' .env` passes as on the base.
- Through the shared `gh_merges`, `eval_words` also serves the history guard's match: `eval -- git push --force` is refused as `eval git push --force` already is (requirement Forced push refused). `echo env | time (sh)` was refused on the base already and is no new behaviour.
- The stand `tests/stands/pipe-walk-compound.py` runs steps 1-3 of the Live Scenario: the real hook by its entry point on the base 17c3c00 and on the branch.

## Capabilities

### New Capabilities

### Modified Capabilities
- `secret-guard`: MODIFIED requirement Environment dumps refused (scenario compound commands, `-c` strings, glued redirections and `case` in a pipe) and MODIFIED requirement Secret file reads in Bash (scenario a pipe next to a compound command).
- `work-hooks-subagents`: MODIFIED requirements Direct merge refused in a process tree and Archive run behind runners and options (scenario `eval --`).

## Impact

- `global/work_hooks.py`
- `tests/test_work_hooks.py`
- `tests/stands/pipe-walk-compound.py`

## Out of Scope

- The nesting of a compound command: not read; a pipe next to one counts the whole command (What Changes), and reading it item by item would need the shell's grammar of `(`, `{`, `if`, `case`, `while`, `for` and their closes across parts (a first take that read it, in review round 1, opened new misses and a cubic cost: round 2).
- A shell's `-c` string as a pipe source (`echo env | sh -c cat | sh`): passes on the base and the branch; reading it as `eval`'s source would take the known quadratic rescan of an `eval` chain past three levels.
- `tee >(sh)`: a process substitution fed by `tee` (`echo env | tee >(sh)`) passes on the base and the branch; a change of its own.
- A here-string feeder (`sh <<< env`, `(cat) <<< env | sh`): passes on the base and the branch; a change of its own.

## Depends On

none

## Source

No owner quote names this bug: it came from the session that closed `fix-pipe-walk-env`. Its task to this session (2026-11-26): "These forms pass the guard on main 17c3c00 and run the piped text as commands (checked in zsh with a harmless payload): a pipe into a compound command or a `-c` string (`echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | case x in x) sh;; esac`, `echo env | sh -c sh`); a redirection glued to the shell word or a subshell `)` (`echo env | sh>out`, `echo env | (sh)>out`, `echo env | (sh)2>/dev/null`); `piped_text` not walking through a `cat`, `tee` or `eval` inside a subshell (`echo env | (cat) | sh`, `echo env | (eval cat) | sh`); `case x in x) env;; esac` (the pattern's `)` hides the program). Also `eval -- solo-sdd archive foo` and `eval -- gh pr merge 1` are missed by `archive_runs` and `gh_merges` (reuse `eval_words`)."
