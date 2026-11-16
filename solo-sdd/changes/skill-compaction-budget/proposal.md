# Proposal

## Why

After auto-compaction Claude Code re-attaches the most recent invocation of each skill, but only its first 5,000 tokens, within a combined budget of 25,000 tokens; it does not re-read the skill file later (code.claude.com/docs/en/skills, read 16.11.2026). Measured 16.11.2026 in this repository:
- `skills/spec-dispatch/SKILL.md`: 33,251 bytes, 5,471 words, 239 lines; step 7 "Merge one at a time" and everything after it (the orchestrator prompt, the decisions, the report form) lie past the first 5,000 tokens, so a long dispatcher session loses them after its first compaction;
- `skills/spec-next/SKILL.md` 19,791 bytes and `skills/spec-plan/SKILL.md` 19,376 bytes, 3,289 words each: at the edge of the budget, their last steps (acceptance, archive, the report) are the first to go;
- every other skill is under 13,100 bytes.

Superpowers 7.0.1 (21.10.2026) met the same limit with a test that fails when a `SKILL.md` reaches 20,000 bytes and moved long parts into files read from disk at their step.

## What Changes

- A test fails when a tracked `skills/*/SKILL.md` is larger than 16,000 bytes and names the file and its size. 16,000 bytes is 5,000 tokens at 3.2 bytes per token: denser than plain English, because the skills are full of paths, commands and backquotes.
- `spec-dispatch`, `spec-next` and `spec-plan` keep in `SKILL.md` the order of steps and one line per step with its gate; the long body of a step moves into a step file next to `SKILL.md` (`skills/<name>/<step>.md`), and the step's line says to read that file each time the step starts, also after compaction. The rules move word for word.
- A test fails when a step file named in a `SKILL.md` does not exist, and when a step file in a skill folder is named by no line of its `SKILL.md`.
- `targets.json` deploys each step file next to its skill's `SKILL.md` in every agent root that skill goes to.
- The tests that read a skill's text for a rule read the skill with its step files; the Line length test of `tests/test_readme.py` covers the step files too.

## Capabilities

### New Capabilities

### Modified Capabilities
- `skill-commands`: new requirements Skill size budget and Step files.
- `readme-content`: requirement Line length covers the step files.

## Impact

`skills/spec-dispatch/SKILL.md`, `skills/spec-dispatch/`, `skills/spec-next/SKILL.md`, `skills/spec-next/`, `skills/spec-plan/SKILL.md`, `skills/spec-plan/`, `targets.json`, `tests/test_skill_commands.py`, `tests/test_readme.py`, `tests/test_sdd_dispatch.py`, `tests/test_sdd_dispatch_plan.py`, `tests/stands/skill-compaction-budget.py`, `README.md`, `AGENTS.md`.

## Out of Scope

- Changing any rule of the three skills: the split keeps every rule and quoted output word for word.
- The other skills: all under 13,100 bytes; the size test keeps them there.
- A hook that re-injects the active change after compaction: the SessionStart `context` hook has no matcher and already runs on `source: compact` with the open changes and git state.
- `permissions.denyInsteadOfPrompting` for background orchestrators and the Claude Code 2.1.323 worktree limits in a sandbox: not checked against a failure here; the sandbox is off on this machine.
- A retell step in `spec-analyze` (the Elephant-Goldfish idea): a separate decision, not a compaction defect.

## Depends On

dispatch-run-decisions, review-rounds-five

## Source

The owner, 16.11.2026, pasted the report "OpenSpec, Spec Kit, Kiro, GSD 2 and Superpowers updates since 30.10.2026 (14.11.2026)" (translated from Russian) and wrote "Analyse and create changes if needed"; the report's item 1: "Candidate change: `skill-compaction-budget` - a test that every `skills/*/SKILL.md` is under 20,000 bytes, and the dispatcher steps moved into `references/` and read at their step."
