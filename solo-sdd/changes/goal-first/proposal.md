# Proposal

## Why

An owner often hands over steps ("remove tests X and Y") rather than the goal they serve ("the test round takes at most 5 minutes"). A plan built from the steps alone cannot tell whether a step moves the goal, whether a cheaper way reaches it, or when the work is done. The `proposal.md` template asks Why for "the problem or the gap this change closes" and Source for the owner's words verbatim, but no rule covers a request made of steps without a goal. Section 6 of the global rules ("change only the named places") forbids widening the work silently, and that stays.

## What Changes

- `spec-plan` (the creation rules): a request that lists steps without a goal gets, at the end of Why, a `Goal:` line with the goal they serve and a `Check:` line with a number that shows it is reached, from the owner's words or marked `(inferred)` with a `goal inferred:` line in `Decisions Without Owner`.
- Every named step is still done as asked. A note that a named step does not move the check, and a cheaper way to reach the goal, go into the plan report as a `Proposals:` line; the plan does not widen by itself.
- Outside `spec-plan` the `Goal:` and `Check:` lines open the report, before the plain lines section 1 of the global rules asks for, and the `Proposals:` line goes into it.
- Section 6 of the global rules gets both rules (the goal and check lines, the `Proposals:` line) for work outside `spec-plan`; section 1 names that the goal lines come first.
- `spec-plan` step 2a moves into a step file to keep `SKILL.md` within the size budget.
- A stand grades the `spec-plan` text run on a step-only request against a copy of the demo project, and the section 6 text run outside `spec-plan`.

## Capabilities

### New Capabilities
- `goal-first`: a step-only request is planned against the goal it serves, without widening the work.

### Modified Capabilities

## Impact

- `skills/spec-plan/creation.md`
- `skills/spec-plan/SKILL.md`
- `global/AGENTS.md`
- `skills/spec-plan/codebase-map.md`
- `tests/stands/plan-map-stand.py`
- `targets.json`
- `tests/targets-before.json`
- `templates/solo-sdd/change/proposal.md`
- `tests/stands/goal-first/`
- `tests/test_skill_commands.py`
- `tests/stands/goal-first.py`

## Out of Scope

- A check at acceptance that the `Check:` line is reached: the line steers the plan and its proposals; acceptance stays the Live Scenario of each change.
- A step-only request on the light path (`spec-plan` step 1a): it makes no change and gets no Why; the stand turns the light path off.
- A question to the owner about the goal: the rules keep "no clarifying questions"; an inferred goal is marked instead.
- Neighbouring changes of this plan: `subagent-check-roles`, `analyze-outside`, `outside-check-text`, `source-over-paste`, `practitioner-techniques`, `eval-process-signals`, `skill-ablation`, `work-pull`, `review-principles`.

## Depends On

- source-over-paste
- analyze-outside

## Source

The owner, 2026-11-20 (translated from Russian): "Also turn into changes the five rules of working together: a goal instead of steps, techniques instead of roles, no self-assessment in the same session, the source instead of a paste, fact checking against primary sources." Unit E: "Goal: when the owner gives steps, the plan writes down the goal they serve and checks the steps against it."
