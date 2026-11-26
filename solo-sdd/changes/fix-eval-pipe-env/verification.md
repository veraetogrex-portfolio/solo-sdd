## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository), run from a script file; an empty answer means the command passes, a `deny` answer prints its reason.

1. On the base commit b6844a4, its hook run from a temporary worktree of that commit: `eval echo env | sh`, `eval echo printenv | bash`, `eval 'echo env' | sh`, `eval echo env | tee | sh`, `eval 'echo env; true' | sh`, `echo env | eval sh`, `echo env | eval 'true; sh'`, `echo env | eval 'cat | sh'`, `printf env | eval eval sh`, `echo env | eval 'eval true; sh'`, `echo env | eval eval eval eval sh`, `echo env | eval cat | sh`, `echo env | eval tee | sh`, `eval echo env | eval sh` and `echo env | eval cat | eval cat | eval cat | eval cat | sh` → no answer (each passes); `eval eval eval eval echo env | sh` → `deny`.
2. On the branch, the same sixteen commands → each `deny`, "The command prints the whole environment or a secret".
3. On the branch, `eval echo hi | sh`, `echo ls | eval sh`, `echo ok | eval cat`, `echo env | eval true` and `eval "echo 'env" | sh` → no answer.
Steps 1-3 run in one call of the stand, which makes and removes its temporary home and base worktree: `python3 tests/stands/eval-pipe-env.py`, printing `eval-pipe-env: 37 of 37 checks passed`.

4. In a Claude Code session after `sync.py push` of the merged change: `eval echo env | sh` run through the Bash tool is refused with the same reason instead of printing the environment.

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

- plan: a pipe into `eval` goes to the first reading head of its text only → a shell, `tee` and a bare `cat` read their input to its end, and one prefix keeps the rebuilt text linear in the command's length.
- plan: `Depends On` names `fix-env-runs-env` → it modified the same requirement; the delta copies the block as PR #94 left the main spec (b6844a4).
- plan: `|&` and a newline after `|` are left out → the pipe walk misses them for every source, `echo` included, so the fix is in that walk for all sources.
- analyze (2026-11-26, judge J1): `eval eval eval eval echo env | sh` was written as passing → it is refused today by the past-depth rule; the Out of Scope line is gone and the form is a refused row.
- analyze (2026-11-26, judge J2): the hostile rows named no verdict and 100,000 evals take 1.36 s on the current code → each row names its verdict, sizes are 20,000 evals and 10,000 segments, `env_dump` is timed.
- analyze (2026-11-26, judge J3, J6): a pipe into `eval eval eval eval sh` and into `eval 'eval true; sh'` was undecided or let through → an `eval` head reads only when its text has a reading head, and counts as reading past three levels; both are refused rows.
- analyze (2026-11-26, judge J4, J5): the reading heads and the segment separators were only in the proposal → both are named in the scenario; grouped and compound forms inside `eval` are in Out of Scope.
- analyze (2026-11-26, judge J7, J8): the `.env` read through an `eval` source and broken `eval` texts had no row → a `.env` row and broken-form rows in task 1.1, each with the verdict bash gives (probed 2026-11-26 with `cat` in place of the shell): bash drops a trailing backslash of an `eval` text, so `echo env | eval 'sh \'` runs `sh` on the pipe and is refused; an open quote makes `eval` run nothing, so `eval "echo 'env" | sh` passes.
- analyze repeat (2026-11-26, A1): a pipe into an `eval` source (`echo env | eval cat | sh`, `eval echo env | eval sh`) was undecided → an `eval` source is read fed with what the pipe into it carries; three refused rows. A prefix of the whole pipeline text was rejected: in a chain of pipes through `eval` it grows the text quadratically (17.8 s for 1,000 hops in a prototype, 2026-11-26); what the pipe carries is echoed instead, and past three `eval` levels the pipeline's dump words count, as the past-depth rule counts them.
- analyze repeat (2026-11-26, A2, A3): one rule for broken texts, and the trailing-backslash row is refused today by `dump_text` (the command is not plain) → `shell_text` gets no backslash rule, the row stays as a regression row outside the failing list, and the open-quote form is a passing row of the scenario.
- analyze repeat (2026-11-26, A4, A6, A7): the `.env` refusal moves to What Changes; a 500-hop chain through `eval` is a hostile row; `eval eval eval eval echo env | sh` is named as refused today in task 1.1.
- analyze repeat (2026-11-26, A5): the `|&` change does not exist yet → proposed to the owner as a session of its own at the end of this change, not created here (one change per session).
- analyze (2026-11-26, judge J9, J10): the cause line and the stand base → line 2018 for `tee`/`cat`, base b6844a4.
