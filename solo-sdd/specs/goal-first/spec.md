# goal-first Specification

## Purpose
A request made of steps without a goal is planned against the goal those steps serve and a check that shows it is reached; every named step is still done as asked, and anything beyond them is only proposed.

## Requirements

### Requirement: Goal and check for a step-only request
For a request that lists steps without a goal, `spec-plan` SHALL end the Why of each change it creates with a `Goal:` line (what the steps serve) and a `Check:` line with a number that shows it is reached; outside `spec-plan` the two lines SHALL open the report, before the plain lines of section 1. A line not in the owner's words SHALL end with `(inferred)`, in `spec-plan` with a `goal inferred:` line in `Decisions Without Owner`. Section 6 of the global rules SHALL hold this.

#### Scenario: Two tests to remove
- **WHEN** `spec-plan` gets "remove the tests test_a and test_b" with no reason
- **THEN** the last two lines of Why are `Goal:` (for example a shorter test round) and `Check:` with a number, both marked `(inferred)`, and `Decisions Without Owner` has a `goal inferred:` line

#### Scenario: Outside spec-plan
- **WHEN** an agent gets "rename x and y in util.py" with no reason, outside `spec-plan`
- **THEN** the first two lines of its report are `Goal:` and `Check:`, each marked `(inferred)`

### Requirement: Named steps kept, extras proposed
Every step the owner named SHALL get a task as asked. A note that a named step does not move the check, and a cheaper way to reach the goal, SHALL go into the report as a `Proposals:` line (in `spec-plan`, the plan report), never into a task or an edit. Section 6 of the global rules SHALL hold this rule.

#### Scenario: A step that does not move the check
- **WHEN** the check is the test round time, the owner named a slow test and a fast test, and only the slow one costs time
- **THEN** both removal tasks exist, and the item of the fast test in the report's `Proposals:` line says `moves the check: no`
