## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository), run from a script file; an empty answer means the command passes, a `deny` answer prints its reason.

1. On the base commit 5549bc4, its hook run from a temporary worktree of that commit: `echo env |& sh`, `echo env |& bash -s`, `echo env |` + newline + `sh`, `eval -- env`, `echo env | eval -- sh`, `echo env | (sh)`, `echo env | ( sh )`, `echo env | ( (sh))` and `echo env | (eval sh)` → no answer (each passes).
2. On the branch, the same nine commands → each `deny`, "The command prints the whole environment or a secret".
3. On the branch, `echo ls |& sh`, `echo ls |` + newline + `sh`, `eval -- ls`, `echo ls | eval -- sh` and `echo ls | (sh)` → no answer.
Steps 1-3 run in one call of the stand, which makes and removes its temporary home and base worktree: `python3 tests/stands/pipe-walk-env.py`, printing `pipe-walk-env: 23 of 23 checks passed`.

4. In a Claude Code session after `sync.py push` of the merged change: `echo env |& sh | wc -l` and `echo env | (sh) | wc -l` run through the Bash tool are refused with the same reason instead of printing a line count of the environment, and `echo ls | (sh) > /dev/null && echo passed` prints `passed`.

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

- plan: the subshell is read only where it hides a shell or an `eval` head (`shell_text`, `reads_input`) → a `)` glued to any later word stays, since a quoted `-c` string may end in `)` and shlex has removed its quotes; a lone `)` word ends the words, and a script path `')'` is refused by it, a refusal on the safe side.
- plan: `|&` keeps its `&` as a space in the next part → `strip_heredocs` maps parts to offsets in the line, and an extra or missing character would shift them.
- analyze (2026-11-26, judge J1, attackers G1 A4, G2 A1 A2, G3 A4): the other readers of `split_cmd` were named nowhere and Out of Scope read as if they were unchanged → a What Changes line names them and what they now see, Out of Scope keeps only their own `eval` handling, and `echo "$(date)"; grep "env" f |& cat` is a passing row; probed 2026-11-26 it passes on the base and on the prototype alike, so it is a regression row, not a failing one.
- analyze (2026-11-26, judge J4, attacker G1 A3): the pipe forms were outside the property test → adding pipe separators to `test_environment_dumps_refused_property` was rejected, as a harmless segment piped into a non-reader (`env X=1 python3 -V`) is refused by the search rule and breaks its passing half; instead the shell dump test loops over the whole finite product of pipe forms × shell forms × words (now 4 × 10 × 4 = 160 commands, analyze repeat R2), stronger than a sample of it; the prototype gave no mismatch (2026-11-26).
- analyze (2026-11-26, judge J9, attacker G3 A3): no broken form among the hostile rows → `echo env | (sh` refused, `echo env |` + newline at the end and `echo env | eval --` passing added to task 1.1, each with the verdict probed on the prototype.
- analyze (2026-11-26, judge J10, attacker G3 A6, LOW): "a `)` word" → the scenario says "the `)` that closes a subshell, glued to the program word or standing alone".
- analyze repeat (2026-11-26, R1): the `.env` read through `|&` had no delta scenario → the requirement Secret file reads in Bash is unchanged: its text already refuses a command that gives a `.env` file to a program, a shell fed by a pipe included; `echo cat .env |& sh` is its refused row in task 1.1, and a MODIFIED copy of that requirement for one form was rejected as churn.
- analyze repeat (2026-11-26, R2): `echo env | ( (sh))` printed the environment and the wording named one `)` → every `)` glued to the program word is cut; `( (sh))` is a shell form of the loop (4 × 10 × 4 = 160 commands) and 1,000 nested subshells are a hostile row; both refused on the prototype, the nesting in 2 ms (2026-11-26). Forms starting with `((` are arithmetic in bash and zsh, so no such row.
- analyze repeat (2026-11-26, R3): the stand had no What Changes line → added.
- analyze repeat (2026-11-26, R4): `echo env | (sh` is refused on the base → task 1.1 names it as a regression row outside the failing list.
- analyze repeat (2026-11-26, R5): a newline after `|` in a command that is not plain stays refused by `dump_text` → Out of Scope names it as a false refusal on the safe side.
- plan commit (2026-11-26, pass 7b): `fix-archive-runs-command-values` (plan merged as #100 while this change was analyzed) modifies the same requirement Environment dumps refused (`time --output` in the scenario A wrapper option with a value) → it is named in `Depends On`; this delta's copy of the block is brought to that change's archived text before `/spec-next` starts, so neither archive drops the other's scenario.
- owner (2026-11-26, "Start now"): the code starts before `fix-archive-runs-command-values` is archived, as its session stopped at 3 of 5 tasks → it leaves `Depends On`; the code of both touches different functions, and whichever change archives second brings its delta's copy of Environment dumps refused to the first one's archived block (`solo-sdd archive` prints a `sibling:` line for it).
- analyze (2026-11-26): dropped by the judge as misreads or already answered: the subshell cause (`cmd_start` strips the `(` in place), a quoted `--` (`part_words` removes the quotes), the `env_read` scenario, the timing bound (the existing hostile test's pattern), the forms after a `)` and nested `eval --` (decided by the scenario's rule), `scripts/sync_blocks.py` in Impact (run, not edited).
