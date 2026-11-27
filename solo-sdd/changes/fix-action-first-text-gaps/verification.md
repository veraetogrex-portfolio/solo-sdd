## Live Scenario

`python3 tests/stands/action-first.py prepare` makes the stand; its prompt files carry the rules block built from `global/AGENTS.md` of the checkout it runs from. Each answer comes from a `general-purpose` subagent of the main session on `sonnet` (the owner's choice of 2026-11-26), never `claude -p`, whose prompt is the whole prompt file text, rules block included: a subagent sees its session's start-time `~/.claude/CLAUDE.md`, not the laid-out one (the lesson stand-runs-what-it-tests). The lead saves each final message to the scratchpad and discards a run whose transcript reads a path under `tests/stands/action-first` or this change's folder. One run per prompt; a miss is recorded as it came in Result and Not Verified and becomes a new change through `/spec-plan`; it does not reopen this change once archived.

The base is main 4ec331e: its rules gave, on 2026-11-26 with an abridged rules block in the prompt (sections 0, 1, 2, 3, 6, 9, 13), `steps` `goal first: no` and `analysis` `file linked: no`; section 1 is unchanged up to 4ec331e, so the comparison with the whole block here is indicative.

1. After the merge and the delivery's `sync.py push`: `python3 sync.py status` shows no `outdated`, `missing` or `drift` line for the three copies of `global/AGENTS.md`, `grep -cF 'before the actions or the `No action follows:` line' ~/.claude/CLAUDE.md` → `1`, and `prepare` from the merged main gives `grep -cF 'holds the same action lines' <stand>/analysis.md` → `1`.
2. A subagent gets `steps-prompt.md` (30 rows, so the data gives actions) → `--grade-goal` prints `goal first: yes` and the line after `Check:` is a list item holding ` — `; `--grade-analysis <answer> <stand>/catalog` on the same answer records `file linked` (a data pull, so the file rule applies). A subagent gets `steps-empty-prompt.md` → `--grade-goal` prints `goal first: yes` and the line after `Check:` starts with `No action follows:`.
3. A subagent gets `analysis.md` → `--grade-analysis <answer> <stand>/catalog` prints `actions first: yes` and `file linked: yes`; the other two lines are recorded as they come.
4. A subagent gets `empty-prompt.md` → `actions first: yes`; one gets `form-prompt.md` → `form kept: yes` (no regression of the forms that passed).
5. `python3 tests/stands/action-first.py clean <stand>` → the folder is removed.

## Needs

- Steps 2-4 run from the main session: from a subagent (under `spec-dispatch` the orchestrator is one) the hook refuses an untagged `general-purpose` subagent.
- 5 `sonnet` subagent runs on the subscription (the owner's choice of 2026-11-26), no paid API call.

## Fallback

In any session, steps 1-5 run from the main session after the merge and the delivery's `sync.py push` (agents run it without asking); until then Result holds the `selftest` of task 1.2 and the suite, Not Verified names steps 1-5, and the first table of `docs/waiting.md` gets a line for them.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge J3): the step-only scenarios are model behaviour, proven by Live step 2 only; task 1.1 is the failing test of their cause (the missing rule words).
- plan (judge J4): a form the request or a running skill prescribes wins over the goal lines too, as it wins over the analysis opening; rejected: goal lines always first.
- plan (judge J5): the file holds the same action lines (what the grader checks), not "opens with" them.
- plan (repeat analyze 3): the clause "unless a prescribed form puts another line first" is model behaviour no stand prompt reaches (a steps request with a prescribed first line); it is named under Not Verified.
- plan (judge J8): the one action item without ` — ` (2026-11-26) stays out of scope as a model miss; `effect named: no` in step 3 becomes a new change through `/spec-plan`.
