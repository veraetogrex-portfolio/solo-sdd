# Proposal

## Why

In a field the project has never touched, an agent tends to start from what it already does, and a prompt such as "you are an expert in X" changes the tone, not the method. What helps is naming first the tools, techniques and checks a practitioner of that field uses, with a source for each, and then working with them. A field counts as new when no project spec, lesson or skill laid out for the agent covers it. Neither section 14 of the global rules nor `spec-plan` says anything about work in a field the project has no spec, lesson or skill for. The repository has no persona prompts today (its role lines, such as "You are the dispatcher", set actions and bans, not a level of skill), and nothing keeps it that way.

## What Changes

- The global rules, section 14: work in a field the project has no spec, lesson or skill for starts with a short list of the tools, techniques and checks a practitioner of that field uses, each with a source; the work then uses them, and the report names which ones ran. No line in a prompt to a subagent sets a level of skill; the rule itself is worded without quoting such a line, so the persona test does not catch it.
- `spec-plan` (the creation rules): a change in such a field gets that list in its proposal and a task or Live Scenario step for each item it uses.
- A test keeps `skills/`, `global/AGENTS.md`, `ALGORITHM.md` and `templates/` free of persona prompts; `integrations/` holds pinned copies and is out of the check.

## Capabilities

### New Capabilities
- `practitioner-techniques`: work in a new field starts from a practitioner's tools and checks; no persona prompts.

### Modified Capabilities

## Impact

- `global/AGENTS.md`
- `skills/spec-plan/creation.md`
- `tests/test_skill_commands.py`
- `tests/affected.json`
- `tests/stands/practitioner-techniques.py`

## Out of Scope

- Rewriting the role lines of `spec-dispatch`, its orchestrator prompt and `codex-orchestration`: they set actions and bans, not a level of skill.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `goal-first`, `eval-process-signals`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

- goal-first

## Source

The owner, 2026-11-20 (translated from Russian): "Also turn into changes the five rules of working together: a goal instead of steps, techniques instead of roles, no self-assessment in the same session, the source instead of a paste, fact checking against primary sources." Unit F: "Goal: in a field new to the project the agent first names the tools, techniques and checks of a practitioner, then works with them."
