## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` a folder with a `solo-sdd/` tree), run from a script file; an empty answer means the command passes, a `deny` answer prints its reason.

1. On the base commit 17c3c00, its hook run from a temporary worktree of that commit: `echo env | (true; sh)`, `echo env | (cd /tmp && sh)`, `echo env | if true; then sh; fi`, `echo env | case x in x) sh;; esac`, `echo env | sh -c sh`, `echo env | sh>out`, `echo env | (sh)>out`, `echo env | (sh)2>/dev/null`, `echo env | (cat) | sh`, `echo env | (eval cat) | sh`, `case x in x) env;; esac` with `cwd` the repository, `eval -- gh pr merge 1` with `cwd` the repository and `eval -- solo-sdd archive add-words` with `cwd` a temporary repository whose change `add-words` holds a foreign `CLAIM` → no answer (each passes).
2. On the branch, the same thirteen commands → the eleven dump forms `deny` with "The command prints the whole environment or a secret", the merge `deny` naming `sdd-pr.py merge`, the archive `deny` as taken by another agent.
3. On the branch, `echo ls | (true; sh)`, `echo ls | sh -c sh`, `echo ls | sh>out`, `echo ls | (cat) | sh`, `case x in x) ls;; esac`, `echo env | (true; sh ')')` and `echo env | (cat) > out` → no answer.
Steps 1-3 run in one call of the stand, which makes and removes its temporary home, repository and base worktree: `python3 tests/stands/pipe-walk-compound.py`, printing `pipe-walk-compound: 33 of 33 checks passed`.

4. In a Claude Code session after `sync.py push` of the merged change: `echo env | (true; sh) | wc -l`, `echo env | sh -c sh | wc -l` and `echo env | (cat) | sh | wc -l` run through the Bash tool are refused with the same reason instead of printing a line count of the environment, and `echo ls | (true; sh) > /dev/null && echo passed` prints `passed`.

## Needs

- Step 4: `sync.py push` of the merged change, the delivery's layout step (a prod action of this repository, AGENTS.md Security), then a Claude Code session that loads the deployed hook.

## Fallback

Step 4 needs the layout, a prod action after merge: before it the hook from the branch is run by its entry point (steps 1-3), and Not Verified names step 4 if the layout has not happened, with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan: one rule for `)` in `part_words` (an unquoted `)` ends the words, quotes and `\)` keep it) replaces `subshell_end`'s one `)` per `(` in the same part → a compound's `)` closes a `(` of an earlier part, which a per-part count cannot see; a quoted `')'` stays text, so the round-1 forms of `fix-pipe-walk-env` (`eval '(' true ')' ';' printenv`) keep their verdict (probed 2026-11-26 on the prototype: a replay of the 13,475 string literals of `tests/` and `tests/stands/` gave no verdict change against 17c3c00).
- plan: the end of a compound command is not read → reading it needs the nesting of `(`, `{`, `if`, `case`, `while` and `for` across parts, and a misread nesting would hide a fed command; over-reading only refuses a stdin shell after a compound fed by a dump text (`echo env | (true); sh`).
- plan: `case` counts the whole command (`in_case`) instead of reading its items → a pattern's `|` is split as a pipe by `split_cmd` and its `)` ends the words; `case x in x) grep env f;; esac` is refused, a refusal on the safe side, and `case x in x) cat .env;; esac`, a `.env` read on the base, stays one.
- plan: `feeds` keeps its scan of a parts list once (`FED`) → without it `sh; ` × 10,000 took 1.7 s against 0.13 s on the base (probed 2026-11-26).
- analyze (2026-11-26, judge J2, attacker G1 A2): the compound invariant had no property test → `test_environment_dumps_refused_compound_property` in task 1.1 (the bug fix has its five tasks); extending `test_environment_dumps_refused_property` was rejected, as a harmless segment piped into a non-reader is refused by the search rule (the decision of `fix-pipe-walk-env`).
- analyze (2026-11-26, judge J3, attackers G1 A9, G3 F-04): the replay proof of task 1.2 would flip on its own new rows → it replays the literals of the base 17c3c00's test files.
- analyze (2026-11-26, judges J4, J6, J7): `case x in x) grep env f;; esac`, the unclosed subshell, the redirection without a target and `echo env | (cat) > out` had no scenario → named in the THEN of the new scenario.
- analyze (2026-11-26, judges J5, J8, J9): deep nesting, `set`, `declare -p`, `/bin/sh`, `"sh"`, `exec sh` and `command sh` had no row → rows in task 1.1 (probed on the prototype: 3,000 nested subshells refused in 0.01 s, 20,000 `)` passing in 0.03 s).
- analyze (2026-11-26, judge J10, LOW): the 1 s bound of the hostile rows has no requirement → kept, the pattern of `test_environment_dumps_refused_hostile_input`; the requirement Hostile command text bounds the whole call at 5 s.
- analyze (2026-11-26, judge J11, LOW): the requirement texts of the merge and archive guards name no `eval` → unchanged; their scenarios carry `eval --` and the texts stay under the length limit.
- analyze repeat (2026-11-26, R1): a `case` inside `$(…)` was said to pass → probed 2026-11-26 with the whole guard verdict: `echo "$(case x in x) env;; esac)"`, its unquoted form and `y=$(…); echo "$y"` are refused on the base and the prototype (a command with `$(` is not plain and `case` leaves its whole text counted), and `echo "$(case x in x) cat .env;; esac)"` is a `.env` read on both; the repeat read only `env_dump` and `env_read` → the three dump forms are regression rows in task 1.1.
- analyze repeat (2026-11-26, R2): a pipe into `-c` strings past three levels had no rule → the THEN says any one past three levels of `-c` or `eval` counts as a reader, as for `eval`; five nested `sh -c` and `sh -c "eval 'sh -c sh'"` are refused rows (the prototype refuses both; the base refuses the first by its past-depth rule).
- analyze repeat (2026-11-26, R3): `(true; cat) | sh`, `sh -c cat | sh`, `sh&>out`, `until` and `select` had no row → rows and loop forms in task 1.1 (each passes on the base and is refused on the prototype).
- analyze (2026-11-26): dropped by the judge as misreads or already answered: `eval` as a known merge bypass (only after `A=(…)`), the quoted `')'` known bypass, nested `eval --`, `(true) | sh`, the Source, the Review step, the stand's runner, `cat -`, `tee >(sh)`, `(cat; true) | sh`, docs/hooks.md, the reader list.
