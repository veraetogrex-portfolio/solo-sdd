## Live Scenario

`python3 tests/stands/action-first.py prepare` makes the stand (its `analysis.md`, `empty-prompt.md`, `broken-prompt.md`, `steps-prompt.md`, `form-prompt.md`, `repo.md`, `repo-exp.md` and folders, as in the `action-first-project-repo` archive). Each answer comes from a `general-purpose` subagent of the main session on `sonnet` (the owner's choice of 2026-11-26), never `claude -p`; its prompt is the prompt file's text after the rules block (the text task 1.1 checks), since the laid-out rules reach the subagent through the host as `~/.claude/CLAUDE.md`; the lead saves each final message to the scratchpad and discards a run whose transcript reads a path under `tests/stands/action-first` or this change's folder.

The base is main 58c1d41 laid out: its runs of 2026-11-26 on `sonnet` (the archive's Result, "Rerun on sonnet") gave `analysis` four `no` and `steps` `goal first: no`, with prompts that did not say where the final message goes.

1. `python3 sync.py status` after `sync.py push` of the merged change → no `outdated`, `missing` or `drift` line for the three copies of `global/AGENTS.md`; `grep -cF 'unless its prompt holds the line' ~/.claude/CLAUDE.md` → `1`.
2. `grep -cxF 'Your final message is passed to the owner as your answer.' <stand>/*.md` (the whole prompt line; the rules block quotes the same sentence inside its clause) → `1` for each of the seven prompt files.
3. A subagent gets the tail of `analysis.md` → `--grade-analysis <answer> <stand>/catalog` prints `actions first: yes`, `effect named: yes`, `file linked: yes`, `only analysis file: yes`.
4. A subagent gets the tail of `steps-prompt.md` → `--grade-goal` prints `goal first: yes`.
5. The five runs that passed on the base keep passing: `empty-prompt.md` → `actions first: yes`; `broken-prompt.md` → `failure named: yes`; `form-prompt.md` → `form kept: yes`; `repo.md` → `--grade-repo` eight `yes`; `repo-exp.md` → `--grade-experiment` nine `yes` with a `git worktree add` in its Bash commands.
6. `python3 tests/stands/action-first.py clean <stand>` → the folder is removed.

Each prompt runs once: a step's result is one run of a stochastic model, and a miss is recorded as it came, not rerun until it passes. A miss in step 3 or 4 is recorded in Result and Not Verified and becomes a new change through `/spec-plan`; under the Fallback the change is already archived when these steps run, so a miss does not reopen it.

## Needs

- Steps 1-6 run from the main session: from a subagent (under `spec-dispatch` the orchestrator is one) the hook refuses an untagged `general-purpose` subagent, as `action-first-project-repo` met on 2026-11-23.
- 7 `sonnet` subagent runs on the subscription (the owner's choice of 2026-11-26), no paid API call.

## Fallback

Under the dispatcher, steps 1-6 run from the main session after the merge and the delivery's `sync.py push` (agents run it without asking); until then Result holds the `selftest` of task 1.2 and the suite, Not Verified names steps 1-6, and the first table of `docs/waiting.md` gets a line for them.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge J3): the bug scenarios A subagent answering for the owner and A subagent given steps for the owner are model behaviour, proven by Live steps 3 and 4 only; task 1.1 is the failing test of their cause (the missing line and clause).
- analyze J3 (kept MEDIUM): the line is for a caller that hands the subagent's final message to the owner as it is; today only the stand writes it, no skill does, and teaching the skills that relay a subagent's answer to write it is out of scope here (a later change if the runs show the need).
- analyze J1 (kept CRITICAL, fixed): task 1.1 checks the line as a whole line anywhere in the prompt text after the rules block and the clause words as substrings of the rules block, never by position.
- analyze J2 (kept HIGH, fixed): the clause says the line makes the final message a report to the owner, so the goal lines of sections 1 and 6 hold for it as well as the analysis opening; the delta requirement says the same.
- analyze repeat R1 (HIGH, fixed): the subagent's prompt is the whole text after the rules block, the same text task 1.1 checks, so the line cannot sit outside what the subagent gets.
