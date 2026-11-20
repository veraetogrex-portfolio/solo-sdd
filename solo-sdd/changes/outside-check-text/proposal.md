# Proposal

## Why

Code gets an outside check before it is done (an independent review by an agent that did not write it, `spec-next` step 7a); an analysis, a research or a text for other people does not. The global rules define "done" for them as "sources with dates" and "facts checked" without saying who checks, and `evidence-research` searches primary sources (step 2) but has no step that checks the finished table before the answer form. The session that wrote a text is the one least likely to see its own wrong date or version, while one pass of another agent that opens the primary source of every number catches them.

## What Changes

- The global rules (section 3, the analysis and text kinds of done): before an analysis, a research or a text for other people is handed over, a `Check:` subagent that did not write it gets the text and its source list, not the reasoning, opens the primary source of every number, date, version and named fact and marks it confirmed, wrong (with the right value) or no primary source. Wrong values are fixed, a fact without a primary source moves to "Not confirmed". One pass; a second only for the fixed lines.
- A recommendation in such a text also gets one line from `Check:`: the strongest argument against it.
- `evidence-research` gets this check as a step before the answer form, and the answer form a line `Check: confirmed <n>, fixed <n>, not confirmed <n>`.
- The check covers only a text that holds a fact from an outside source; skill reports, change artifacts and status lines are out. An agent without a subagent tool checks in place and says so.
- Section 10 of the global rules names `Check:` among the subagents allowed.
- A stand with a text of 11 facts, 3 of them planted wrong and one without a source, grades a `Check:` run and the handed-over answer.

## Capabilities

### New Capabilities
- `fact-check`: an outside fact check of analyses, research and texts before they are handed over.

### Modified Capabilities

## Impact

- `global/AGENTS.md`
- `skills/evidence-research/SKILL.md`
- `tests/test_skill_commands.py`
- `tests/stands/outside-check-text.py`
- `tests/stands/outside-check-text/`

## Out of Scope

- The `Check:` role in the guard hook and its model rule: `subagent-check-roles`.
- The prompts of the owner's scheduled tasks outside the repository: the owner edits them separately.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `source-over-paste`, `goal-first`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

- subagent-check-roles
- analyze-outside

## Source

The owner, 2026-11-20 (translated from Russian): "Also turn into changes the five rules of working together: a goal instead of steps, techniques instead of roles, no self-assessment in the same session, the source instead of a paste, fact checking against primary sources." Unit G: "Goal: an analysis, a research and a text for other people are checked by a clean subagent before they are handed over. Every number, date and version is checked against the primary source."
