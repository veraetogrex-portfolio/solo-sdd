# Proposal

## Why

`spec-analyze` checks that every requirement has a task (pass 1) and that the delta agrees with the main specs (pass 7), but two kinds of drift inside one change pass unnoticed:

- A task names a value (a default, a limit, a setting key, a path, a command, an output text) that differs from the value the requirement it implements names. The implementer follows the task, so the code ships the task's value and the scenario's test fails late or, worse, is written to the task's value. GitHub Spec Kit 1.4.2 (2026-11-17, "tasks: cite canonical field constraints and analyze drift", #5458) added exactly this check to its `analyze`.
- The tasks and deltas together do not deliver what `proposal.md` promises in What Changes, or deliver something it does not name. Pass 1 compares requirements with tasks, never the proposal's promise with what the plan builds. The Elephant-Goldfish Model extension of the Spec Kit catalog (1.4.1, 2026-11-16) catches this by a retell from the plan alone, without the author's context; the open change `analyze-outside` has attackers and a judge, but no retell (searched for retell, restate and summar on 2026-11-21).

## What Changes

- Pass 1 of `spec-analyze` starts with a retell: from `tasks.md` and the delta specs only, at most five lines of what the user gets; then each What Changes item of `proposal.md` is matched with the retell. An item no retell line covers is HIGH, a retell line no item covers is MEDIUM; the retell goes into the report.
- Pass 7 of `spec-analyze` compares every value a task names in backquotes with the value its requirement or scenario names for the same thing; a different value is HIGH.
- The pass table of `ALGORITHM.md` names both checks in rows 1 and 7.
- A stand with a fixture change that plants both kinds of drift grades a `spec-analyze` run on it.

## Capabilities

### New Capabilities
- `analyze-drift`: `spec-analyze` finds a change whose tasks drift from its requirements or from its proposal.

### Modified Capabilities

## Impact

- `skills/spec-analyze/SKILL.md`
- `ALGORITHM.md`
- `tests/test_skill_commands.py`
- `tests/stands/analyze-drift.py`
- `tests/stands/analyze-drift/`

## Out of Scope

- Running the passes outside the author, attackers and the judge: the open change `analyze-outside`. This change depends on it: the retell is part of pass 1, so its attacker group 1, 2, 3, 3a writes it with no change of the group split, and the reader has not seen the author's reasoning.
- The Stop hook and background tasks: the open change `fix-stop-background-shell` from the same review.
- A drifted value written in plain text, not in backquotes ("default 5"): only backquoted values are compared.
- The missing rows 4a and 7b of the `ALGORITHM.md` pass table: a separate change.
- Checking values in code against the spec: `spec-audit` does that after code.
- A separate subagent or role tag for the retell (a `Retell:` agent): the hook allows only the listed tags, and a clean context is what `analyze-outside` gives every pass.

## Depends On

- analyze-outside

## Source

The owner, in the weekly competitor review task (translated from Russian): "Whatever is better than what we have now, add that into changes, or what you consider better from the point of view of functionality". In this session (translated from Russian): "You only need to make the changes".
