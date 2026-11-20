# Proposal

## Why

An owner often hands over steps ("remove tests X and Y") rather than the goal they serve ("the test round takes at most 5 minutes"). A plan built from the steps alone cannot tell whether a step moves the goal, whether a cheaper way reaches it, or when the work is done. The `proposal.md` template asks Why for "the problem or the gap this change closes" and Source for the owner's words verbatim, but no rule covers a request made of steps without a goal. Section 6 of the global rules ("change only the named places") forbids widening the work silently, and that stays.

## What Changes

- `spec-plan` (the creation rules): a request that lists steps without a goal gets, in Why, the goal they serve and a check that shows it is reached, from the owner's words or marked as inferred in `Decisions Without Owner`.
- Every named step is still done as asked. A note that a named step does not move the check, and a cheaper way to reach the goal, go into the plan report as a `Proposals:` line; the plan does not widen by itself.
- Outside `spec-plan` the goal and its check open the report.
- The global rules, section 6, get the same two lines for work outside `spec-plan`.
- A stand runs the laid-out `spec-plan` on a step-only request against a copy of the demo project.

## Capabilities

### New Capabilities
- `goal-first`: a step-only request is planned against the goal it serves, without widening the work.

### Modified Capabilities

## Impact

- `skills/spec-plan/creation.md`
- `skills/spec-plan/SKILL.md`
- `global/AGENTS.md`
- `skills/spec-plan/report.md`
- `targets.json`
- `tests/affected.json`
- `tests/test_skill_commands.py`
- `tests/stands/goal-first.py`

## Out of Scope

- A question to the owner about the goal: the rules keep "no clarifying questions"; an inferred goal is marked instead.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

- source-over-paste
- analyze-outside

## Source

The owner, 2026-11-20 (translated from Russian): "Also turn into changes the five rules of working together: a goal instead of steps, techniques instead of roles, no self-assessment in the same session, the source instead of a paste, fact checking against primary sources." Unit E: "Goal: when the owner gives steps, the plan writes down the goal they serve and checks the steps against it."
