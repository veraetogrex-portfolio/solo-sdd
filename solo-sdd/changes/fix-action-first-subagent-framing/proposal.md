# Proposal

## Why

The live runs of 2026-11-26 (`general-purpose` subagents of the main session on the laid-out rules, recorded in the Result of the `action-first-project-repo` archive) failed the analysis opening on both `haiku` and `sonnet`.

Reproduction: `python3 tests/stands/action-first.py prepare`, then a subagent gets the request of `analysis.md` ("analyse the catalog in catalog.db and tell me what to work on") → expected: one to three actions in the first 5 non-empty lines and a linked analysis file (`--grade-analysis` four `yes`) → got on sonnet: a `Goal:`/`Check:` line, a data paragraph, a heading, five numbered actions and no file (four `no`); the step-only request of `steps-prompt.md` got no `Goal:`/`Check:` lines on either model (`goal first: no`).

Cause: `global/AGENTS.md:19` ends section 1's analysis rule with "a subagent's report to its caller is not such a result", and the stand runs the measured agent as a subagent whose prompt never says where its final message goes. Every stand run is a subagent's report to its caller, so the rule exempts exactly what the stand measures; the prompts written by `prepare` in `tests/stands/action-first.py:150` and `:159` give the agent no other reading. The steps miss has the same root: `global/AGENTS.md:17-18` puts the `Goal:` and `Check:` lines at the head of "a report to the owner", and a subagent that reads its final message as a report to its caller does not take it for one; the prompt line names the owner as its reader.

## What Changes

- Section 1 of the global rules keeps the subagent exemption for a report the caller reads for its own step, and when its prompt holds the line `Your final message is passed to the owner as your answer.` makes that final message a report to the owner: the analysis opening of section 1 and the goal lines of sections 1 and 6 hold for it, and the new scenario A subagent given steps for the owner checks the goal lines.
- `tests/stands/action-first.py` (its prepare) writes that line into every prompt file, and its selftest checks the line and the clause, so a stand run is graded as an answer to the owner, not as a report to a lead.

## Capabilities

### New Capabilities

### Modified Capabilities
- `action-first`: requirement Prescribed forms and failed reads gains the case of a subagent whose final message goes to the owner.

## Impact

- `global/AGENTS.md` (section 1, the analysis rule)
- `tests/stands/action-first.py` (prepare, selftest)

## Out of Scope

- The `plan-input` misses of the same runs: `fix-plan-input-misses`.
- Changing the stand model in `global/model-policy.json`: the owner chose `sonnet` for these runs in the chat; the policy default stays.
- `lesson-gate` also edits `global/AGENTS.md` (section 15); a merge conflict there is resolved by the dispatcher's return, not here.

## Depends On

none

## Source

The owner, 2026-11-26 (translated from Russian): "Yes, on sonnet", then "Yes, plan it", answering whether to plan a change that fixes the gaps the runs found, proven by the same stands on sonnet.
