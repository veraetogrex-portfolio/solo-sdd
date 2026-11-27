# Proposal

## Why

Two lines of section 1 of the global rules leave room for the misses the live runs of 2026-11-26 found once the rules were given in the prompt (the Result of the `fix-action-first-subagent-framing` archive, second pass, `sonnet`):

- `steps-prompt.md` ("count the rows of catalog.db and list the five oldest items") → expected: `Goal:` and `Check:` first (`--grade-goal` `goal first: yes`) → got: the reply opened with `No action follows: this is a plain lookup`. Cause: `global/AGENTS.md:19` says the 5-line window is counted "after the `Goal:` and `Check:` lines when they come first", which reads as optional, and names only "the actions right after them", not `No action follows:`.
- `analysis.md` → expected: a linked file that holds the action lines (`--grade-analysis` `file linked: yes`, the main scenario Data only in a database) → got: `catalog-analysis.md` linked, without the action lines. Cause: `global/AGENTS.md:19` says only "The data and the full analysis go into a new Markdown or CSV file", and the requirement Analysis data delivered as a file says the same, while its scenario and the stand's grader expect the file to hold the actions.

## What Changes

- Section 1 of the global rules says that for a request of steps without a goal the `Goal:` and `Check:` lines come first, before the actions or the `No action follows:` line, also for a lookup with nothing to fix, unless a prescribed form puts another line first.
- Section 1 says the analysis file holds the same action lines.
- `tests/stands/action-first.py` checks the two phrases in its rules block and gets a steps prompt on the empty catalog (`steps-empty-prompt.md`).

## Capabilities

### New Capabilities

### Modified Capabilities
- `action-first`: requirements Goal lines before the actions and Analysis data delivered as a file.

## Impact

- `global/AGENTS.md` (section 1, the analysis rule)
- `tests/stands/action-first.py` (selftest)

## Out of Scope

- The one action item without ` — ` in the 2026-11-26 `analysis` run: the rule already says "each a list item `<action> — <expected effect>`"; a model miss, not a text gap; the Live Scenario records it if it repeats.
- The stand prompts of other skills (`plan-input`: the archived `fix-plan-input-misses`).

## Depends On

none

## Source

The owner, 2026-11-27: `/spec-plan`, given right after the dispatcher report that named this open item (translated from Russian): "the effect on every item, the actions inside the analysis file and the `Goal:`/`Check:` lines for a request of steps fail".
