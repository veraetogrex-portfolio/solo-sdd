# Proposal

## Why

An owner often pastes a piece of a file, a log, a report or a chat into the conversation instead of pointing the agent at it. The excerpt may be cut before the line that changes the conclusion, or older than the file. The global rules say to reread the chat and the project folder before asking (section 1) and to name the missing access (section 2), but nothing says to read the source of a pasted excerpt the agent can reach. `relay` takes a pasted report as data and checks its claims by commands, but does not look for the session or file the report came from.

## What Changes

- The global rules, section 1: a pasted excerpt of a file, log, report or chat the agent can reach (a project file, a session log, a PR, a connected folder) is read at its source; the excerpt may be cut or stale. A source out of reach gets one line naming the access that would give it, and the work goes on with the excerpt marked as an excerpt.
- `relay` step 1: before parsing, find the source of the pasted report (the other agent's session log, the change folder, the PR) and read it; out of reach, say which access would give it.
- A stand with a pasted five-line excerpt of a project file whose sixth line changes the conclusion grades the answer of an agent on the laid-out rules.

## Capabilities

### New Capabilities
- `source-over-paste`: a pasted excerpt is read at its source when the agent can reach it.

### Modified Capabilities

## Impact

- `global/AGENTS.md`
- `skills/relay/SKILL.md`
- `tests/test_skill_commands.py`
- `tests/stands/source-over-paste.py`
- `tests/stands/source-over-paste/`

## Out of Scope

- Connecting folders or sources to the owner's scheduled sessions outside the repository: the owner's settings.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `goal-first`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

- outside-check-text

## Source

The owner, 2026-11-20 (translated from Russian): "Also turn into changes the five rules of working together: a goal instead of steps, techniques instead of roles, no self-assessment in the same session, the source instead of a paste, fact checking against primary sources." Unit H: "Goal: if a pasted excerpt is taken from something the agent can reach, the agent reads the source, not only the excerpt."
