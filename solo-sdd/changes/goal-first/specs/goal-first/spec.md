## Purpose

A request made of steps without a goal is planned against the goal those steps serve and a check that shows it is reached; every named step is still done as asked, and anything beyond them is only proposed.

## ADDED Requirements

### Requirement: Goal and check for a step-only request
For a request that lists steps without a goal, `spec-plan` SHALL write in Why the goal the steps serve and a check that shows it is reached; outside `spec-plan` the goal and its check SHALL open the report. A goal and check not in the owner's words SHALL be marked inferred, in `spec-plan` with a line in `Decisions Without Owner`. The global rules, section 6, SHALL hold this rule.

#### Scenario: Two tests to remove
- **WHEN** `spec-plan` gets "remove the tests test_a and test_b" with no reason
- **THEN** Why names a goal (for example a shorter test round) and a check with a number, and `Decisions Without Owner` marks both inferred

#### Scenario: Outside spec-plan
- **WHEN** an agent gets "rename x and y in util.py" with no reason, outside `spec-plan`
- **THEN** its report opens with the goal and its check, marked inferred

### Requirement: Named steps kept, extras proposed
Every step the owner named SHALL get a task as asked. A note that a named step does not move the check, and a cheaper way to reach the goal, SHALL go into the `spec-plan` report as a `Proposals:` line, never into a task.

#### Scenario: A step that does not move the check
- **WHEN** the check is the test round time, the owner named a slow test and a fast test, and only the slow one costs time
- **THEN** both removal tasks exist, and the report has a `Proposals:` line naming the fast test as not moving the round time
