# Proposal

## Why

The live runs of 2026-11-26 (`general-purpose` subagents of the main session on the laid-out `plan-input` skill, recorded in the Result of the `plan-input-skill` archive) passed 4 of 8 steps on `sonnet`; four misses held on `haiku` too.

Reproductions, each on a fresh `python3 tests/stands/plan-input.py prepare`:

- `bare-prompt.md` (a target folder that is not a git repository) → expected: no input, the git reason (`--grade-refusal` `no input: yes`, `reason named: yes`) → got: an input written into `bare/docs/`, the reply citing "the skill's rule for such projects".
- `inside.md` run twice → expected: a second file with the suffix `-2`, the first unchanged → got: no second file, the reply reporting the first one "already in `inputs/`" and checking its claims.
- `prompt.md` and `inside.md` → expected: the reply opens with the three launch lines (`launch lines: yes`) → got: the input path first and the launch lines after line 10 (`launch lines: no` in `inside.md` run 1).
- `chat-prompt.md` → expected: `home/Documents/plan-input/<date> input for spec-plan - chat.md` → got: the input next to `notes/review.md`, the reply saying "the review text in the message is identical to notes/review.md".

Causes: `skills/plan-input/SKILL.md:13` (step 2) names the stop but no Red flags row holds it against a target that has a `docs/` folder; `:33` (step 9) names `-2` only for a taken name, and nothing says an earlier input of the same material is never the answer to a new request; `:80` (Report) says "the launch lines first" without saying the reply's first line is launch line 1. The chat miss is the stand's: `prepare` (`tests/stands/plan-input.py:176`) puts the pasted review in `notes/review.md` within reach, and section 1 of the global rules tells the agent to read a pasted excerpt at its source, so "next to the material's file" is right there.

## What Changes

- `plan-input` keeps step 2's stop for a target folder outside git wherever the material or a `docs/` folder lies, writes a new `-2` input when an earlier input of the same material exists instead of checking or reusing it, and opens its reply with launch line 1 (the file holds the launch lines under its title).
- The spec records that a review pasted in the chat whose file lies within reach outside the target is saved next to that file (the base chat run did so, rightly), and that the chat case with no such file goes to `~/Documents/plan-input/`.
- `tests/stands/plan-input.py` gets a chat mode of its prepare (a stand with no copy of the review outside the target, for the chat run), a launch-line grade that fails when the reply does not open with launch line 1, and the line `Your final message is passed to the owner as your answer.` in every prompt: the measured subagent's final message is the owner's answer, not a report to a lead, which section 1 of the global rules exempts (`fix-action-first-subagent-framing`).

## Capabilities

### New Capabilities

### Modified Capabilities
- `plan-input`: requirements Input kept outside the target, Launch lines and Target without a process tree gain the scenarios of the misses.

## Impact

- `skills/plan-input/SKILL.md` (steps 2 and 9, Report, Red flags)
- `tests/stands/plan-input.py` (prepare, launch, selftest)

## Out of Scope

- The analysis opening and goal lines of the same runs: `fix-action-first-subagent-framing`.
- The stand's shared `prepare` for steps 4 and 5 (one wrong run's file turns its neighbours' `no input` to `no`): the Live Scenario below runs each of them on its own `prepare`; changing the grader is not needed for that.
- Counts in the reply and the done/planned exclusivity missed on `haiku` only; `sonnet` passed them (step 2: nine `yes`).

## Depends On

none

## Source

The owner, 2026-11-26 (translated from Russian): "Yes, on sonnet", then "Yes, plan it", answering whether to plan a change that fixes the gaps the runs found, proven by the same stands on sonnet.
