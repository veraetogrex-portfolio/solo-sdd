## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository); an empty answer means the command passes, a `deny` answer prints its reason. The commands are the ones of the reproduction, as the sessions ran them.

1. On the base commit 286817e (its hook run as `python3 <worktree>/global/work_hooks.py guard` from a temporary worktree of that commit), `grep -n "secret\|printenv\|env |echo \$" skills/debug-profile/SKILL.md`, `grep -n "foo\|env\[" global/sdd_eval.py`, `[ -n "$(git status --short)" ] && echo yes; (cd /tmp && env -i HOME=$HOME PATH=/usr/bin:/bin python3 report.py < /dev/null | tail -4)` and `echo "$(date)"; env X=1 python3 -V` → each `deny`, "The command prints the whole environment or a secret".
2. On the branch, the same four commands and `echo "$(date)"; env -u HOME python3 -V` → no answer (each passes).
3. On the branch, `export -p` and every command of the scenarios Dumps still refused and Other programs' scripts are not text → each `deny` with the same reason.
Steps 1-3 run in one call of the stand, which makes and removes its temporary home and base worktree: `python3 tests/stands/env-dump-text-words.py`, printing `env-dump-text-words: 52 of 52 checks passed`.

4. In a Claude Code session after `sync.py push` of the merged change (the delivery's layout step): the first `grep` of step 1 run through the Bash tool from the repository prints its matching lines instead of the hook refusal.

## Needs

none

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

2026-11-23: `python3 tests/stands/env-dump-text-words.py` from the worktree root printed `env-dump-text-words: 52 of 52 checks passed`: the base 286817e refused the four commands of step 1 with "The command prints the whole environment or a secret", the branch passed the five commands of step 2 and refused the 43 commands of step 3 with the same reason. `python3 tests/run.py --jobs 5 --tier slow`: `files: 42, failed: 0`. Mutation check of `test_environment_dumps_refused_property`: with the program-word dump check of the `env` span replaced by a substitution check only, the test failed on `echo "$(date)"; env -u X e\nv; grep -n "printenv|env" f;`; restored, it passes.

## Not Verified

- Step 4: the hook laid out by `sync.py push` in a live Claude Code session; the layout is a prod action after merge, done by the delivery. Row in the first table of `docs/waiting.md`.

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge 10): the exemption covers the quoted arguments of `grep` and `rg` only, not `sed` and `awk` as the owner's item D said: GNU sed's `e` and awk's `getline`, `| "cmd"` and `system(` run programs from a quoted script, and every refusal of the week was a `grep`.
- plan (analyze repeat 2, 3): `env` counts only at a command position, so a heredoc text `guard env dumps` stays refused; `grep` after `env` or a wrapper is still `grep`.
- plan (analyze repeat 6): the plain-path holes (`env -u X printenv`, `env -C /tmp printenv`, `awk 'BEGIN{system("env")}'`) are older than this change and go to a change of their own, proposed in the plan report.
- plan (judge 12): only the `env` word, its options with their values, its assignments and its program word are exempt; a dump word after them still counts.
- analyze (judge J2): the no-cut condition is `UNCUT` plus any `#`, the shared definition of command-guards Shell forms the text cut cannot read, not a second list.
- analyze (judge J4, J5): the quote reader reads the raw command, heredoc bodies included; a heredoc anywhere leaves the command uncut, so the accepted false refusal `guard env dumps` stays.
- analyze (judge J8): `egrep`, `git grep`, `ag`, unquoted patterns and sed scripts stay counted in a non-plain command: the week's refusals were all quoted `grep` patterns, and each added program widens what the cut must read; a search piped to a program outside `TEXT_SINKS` keeps its arguments counted, as `strip_patterns` does.
- analyze (judge J10, J11): `env -u HOME env` in a plain command shares the older `cmd_start` hole of Out of Scope; a program that prints the environment itself (`python3 -c 'print(os.environ)'`) passes today with or without `env` and stays outside this change.
- analyze repeat (R1, R2, R7): the tasks' stricter values hold and are written as scenario rows, since the requirement text is at its length limit: a quoted search word holding `${` and an `env` span word holding a substitution or a dump word stay counted; a `#`, an `UNCUT` form, a heredoc or `case` anywhere in the command stops every cut, as `strip_patterns` reads `UNCUT` over the whole text.
- analyze repeat (R3, R4): `rg` with a word naming `--pre` or `--hostname-bin` keeps every argument counted; `grep` after an `env` span is found by the new `env` reader, so `env -u HOME grep "printenv" f` passes.
- review round 1 (Important 1, 2): fixed. `env` takes any word holding `=` as an assignment, as GNU and BSD env do; a pipe into a program that is not a text reader (interpreters included), checked over every segment of the command so a group or subshell before the pipe counts, or a `>(` anywhere keeps every search counted.
- review round 1 (Nit 1) and round 2: an option word before the program or the `env` (`sudo -u`, `exec -a`, `time -o`, `caffeinate -t`) stops the cut of that segment, and the receiver of a pipe must be a bare text reader as its first word.
- review round 1 (Nit 2, 4): a glob in an `env` span word keeps the `env` counted; `docs/hooks.md` names every `env` option the code reads.
- review round 1 (Nit 3): the unit rows that repeat the stand's refused rows stay: `tests/run.py` does not run stands, so they are the suite's only check of those rows.
- review round 2 (Important 1 rest): a redirection's fd and target are no words of `shell_segments`, so `env A.B=1 > /tmp/x` and `env -i 'A B=1' 2>&1` have no program word and stay refused; the `env` span is cut word by word, so a redirection between its words stays counted.
- review round 2 (Nit, output through a file): `grep -o printenv f > x; sh x` passes on the base too as two calls; named as a known bypass in `docs/hooks.md` and `KNOWN_BYPASSES`.
- review round 2 (Pre-existing): a glob forming a dump word in a bare program word (`[e]nv`) and plain `env A-B=1` pass on the base; outside this change.
- suite run 3 (load average 7): the whole hook took over 1 s on a 100 KB input in the parallel suite, spent in the older `command_text` and `env_dump` (0.2-0.7 s each when measured alone), while the new `dump_text` took at most 0.2 s; the 1 s bound of task 1.3 is asserted on `dump_text`, the reader this change adds, and the hook verdict on each input is still asserted.
