## Live Scenario

Each answer comes from a `general-purpose` subagent of the main session on `sonnet` (the owner's choice of 2026-11-26), never `claude -p`; its prompt is the prompt file's text after the skill block (from the target line on, "the skill is above" read as "use the installed plan-input skill"), since the laid-out skill reaches the subagent through the host; the lead saves each final message and keeps each transcript in the scratchpad. Every run below has its own fresh `python3 tests/stands/plan-input.py prepare` (the chat run `prepare --chat`), so no run's file counts against another, except the two runs of step 3, which share one. In any session steps 2-6 run after the merge and the delivery's `sync.py push`, so the subagents read the laid-out skill; 2.1's Result is filled then.

The base is main 58c1d41 laid out: its runs of 2026-11-26 on `sonnet` (the archive's Result, "Rerun on sonnet") gave `bare` `no input: no`, `inside` run 1 `launch lines: no`, `inside` run 2 no `-2` file and `chat` `chat input: no`. The base prompts lacked the owner line, and the base grader took the launch lines anywhere in the first 10 lines.

1. `python3 sync.py status` after `sync.py push` of the merged change → no `outdated`, `missing`, `first` or `drift` line for `plan-input` in `~/.claude/skills`, `~/.codex/skills` and `~/.agents/skills`.
2. A subagent gets `prompt.md` → `--grade <stand> <reply> <notes>` prints nine `yes`.
3. A subagent gets `inside.md` → `--grade <stand> <reply> <inputs>` prints `outside target: yes` and `launch lines: yes`; the same prompt again → a second file in `<inputs>` with the first one's name and `-2`, the first unchanged (`cmp` of its saved copy), and the reply names the `-2` file (`grep -F` of the `-2` file name in the saved reply); and the second run's transcript has no tool call whose input names the first file; these four checks of the second run are read by the lead by hand, as `--grade` takes one new file only.
4. A subagent gets `plain-prompt.md` → `--grade-refusal` prints `no input: yes`, `reason named: yes`; another, on its own stand, gets `bare-prompt.md` → the same two `yes`.
5. A subagent gets `allout-prompt.md` → `--grade-nothing` two `yes`; another gets `locked-prompt.md` → `--grade-unchecked` two `yes`; another gets the chat prompt of `prepare --chat` → `--grade-chat` prints `chat input: yes`; another gets the `chat-prompt.md` of plain `prepare` (the review also in `notes/review.md`) → `--grade <stand> <reply> <notes>` prints `outside target: yes` and the one new file in `notes/` ends in `- review.md`.
6. `--grade-confined` of every transcript → `grading out of reach: yes`; `python3 tests/stands/plan-input.py clean <stand>` removes each stand.

## Needs

- Steps 2-6 run from the main session: from a subagent (under `spec-dispatch` the orchestrator is one) the hook refuses an untagged `general-purpose` subagent, as `plan-input-skill` met on 2026-11-26.
- 9 `sonnet` subagent runs on the subscription (the owner's choice of 2026-11-26), no paid API call.

## Fallback

Under the dispatcher, steps 1-6 run from the main session after the merge and the delivery's `sync.py push` (agents run it without asking); until then Result holds the `selftest` of task 1.2 and the suite, Not Verified names steps 1-6, and the first table of `docs/waiting.md` gets a line for them.

## Result

<!-- Filled during apply: date, what was run, what was observed. -->

## Not Verified

<!-- Filled during apply: what stayed unproven and why. Write: nothing - if all proven. -->

## Decisions Without Owner

<!-- Filled during apply: choices made without asking, and new changes created for out-of-scope work. -->

- plan (spec-analyze judge 5, 6): the bug scenarios are model behaviour proven by Live steps 3-5 only; task 1.1 is the failing test of the stand and grader parts.
- plan (repeat analyze 1, 4): the chat stand of `prepare --chat` holds the review nowhere, `target/` included, so its run tests Material with no file alone; `bare/` keeps no `docs/` folder and the scenario names that staged case, while the refusal grade fails on any created folder.
- plan (judge 13): the owner line and the skill's Report edit both act on the reply order; the runs cannot tell which one fixed it, and both stay.
