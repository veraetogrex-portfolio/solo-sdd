## Live Scenario

The real hook as Claude Code starts it: `python3 global/work_hooks.py guard` with a PreToolUse JSON on stdin (`tool_name: Bash`, the command, `cwd` the repository), the way `entry` in `tests/test_work_hooks.py` runs it, timed with `time.monotonic()` around the run; a driver script in a temporary folder builds the long commands so that no shell command holds them.

The base is main 4ec331e: its hook from a temporary worktree of that commit (`git worktree add --detach "${TMPDIR:-/tmp}/wt-base-4ec331e" 4ec331e`, removed after).

1. On the base, `echo ` + 2,000 `$(` → its verdict (recorded), `echo ` + 8,000 `$(` → the same verdict after more than 0.8 s, and `echo ` + 50,000 `$(` → no answer within 10 s (the run is stopped at 12 s).
2. On the branch, `echo ` + 50,000 `$(` → passes; `$a` x 100,000 + `; cat .env` → `deny` with the `.env` read reason; `git add ` + 50,000 `$(` → passes; each hook run answers within 8 s, and the secret check alone (a driver calling `guard_secrets_bash`) within 2 s.
3. On the branch, `cat .env`, `cp .env /tmp/e`, `test -f .env` and `cat .env.example` → the same answers as on the base (two refused, two passing).
4. In a Claude Code session after `sync.py push` of the merged change: `cat .env` run through the Bash tool is refused with the `.env` reason, and `ls .env.example` passes.

## Needs

none

## Fallback

Step 4 needs the layout after merge (the delivery's step, which agents run without asking): until then steps 1-3 run the hook from the branch by its entry point, and Not Verified names step 4 with a line in the first table of `docs/waiting.md`.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (repeat analyze 1): the 2-second bound is the secret check's, the whole hook's is 8 seconds; rejected: making `split_words` linear here (another function, its own change).
- plan (spec-analyze judge J1, J6): the fix scans for `.env` occurrences and tests each token with today's pattern, keeping `ENV_FILE`; rejected: a word-start lookbehind (drops `x=.env`, `(.env)`, `$.env`) and a possessive or atomic prefix (still quadratic per start, and `?+` does not compile on Python 3.9, the hook's interpreter).
