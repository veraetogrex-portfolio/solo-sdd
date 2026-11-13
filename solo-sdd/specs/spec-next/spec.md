# spec-next Specification

## Purpose
How the `spec-next` skill runs a change outside the "Under the dispatcher" mode.

## Requirements

### Requirement: Lead writes code
Outside the "Under the dispatcher" mode the lead agent SHALL do the change tasks itself, including code. It launches subagents only for independent acceptance (step 7a) and heavy reading (the `lookup` role of the capability `model-guard`). The exception: the owner named `codex-orchestration`; then Codex executors write the code, and the lead agent accepts the result with its own commands.

#### Scenario: A change in two areas
- **WHEN** a change has six tasks in two modules, and the owner did not name Codex
- **THEN** the lead agent writes the code; only subagents with the tags `Review:` and `Lookup:` are launched

#### Scenario: The owner named Codex
- **WHEN** the owner's request names `codex-orchestration`
- **THEN** Codex executors write the code by this skill, the lead agent accepts the result with its own commands

### Requirement: Reviewer on the main model
`spec-next` SHALL run the independent acceptance (step 7a) on the main model: in Claude, an `Agent` subagent with the tag `Review:` without the `model` parameter. Cheap models stay for search, logs, test output and paid product calls in tests and the live scenario.

#### Scenario: Acceptance in Claude
- **WHEN** an orchestrator on Opus launches the independent acceptance of a change
- **THEN** the `Agent` call with the description `Review: <id>` goes without `model`, the reviewer runs on Opus

#### Scenario: A live scenario with a paid call
- **WHEN** the Live Scenario calls the product model
- **THEN** the call goes to the cheapest product model and with the owner's consent, as before

### Requirement: Review findings
Every finding of the independent acceptance (step 7a) SHALL carry the label `Important`, `Nit` or `Pre-existing` and name the error class with all its places in the diff. `Important`: a requirement, behaviour or data is violated; blocks the archive. `Nit`: style, names, small cleanup; at most five listed, the rest counted. `Pre-existing`: the error predates the change; no archive block, a report line. Every finding SHALL be closed: fixed or dropped with a reason in `Decisions Without Owner`.

#### Scenario: An error the change did not introduce
- **WHEN** the reviewer sees in a neighbouring function an error that is also on the base branch
- **THEN** the finding is labelled `Pre-existing`, the change is archived, a line about it is in the report

#### Scenario: Many trifles
- **WHEN** the reviewer found eight remarks about names
- **THEN** five are listed with the label `Nit`, the rest are named as a count and closed with one line in `Decisions Without Owner`; they do not block the archive, there is no new round

#### Scenario: An error class
- **WHEN** in three places of the diff an empty answer is equally unchecked
- **THEN** one finding names the class and all three places

### Requirement: Review rounds
The first acceptance round SHALL read the whole change diff; the second and third only the diff since the last round and the open findings' places, with the list of given findings, which the reviewer does not repeat. There SHALL be at most three rounds. An `Important` left after the third means no archive: the findings and "reconsider the approach" go into `Not Verified`, status "not done". The reviewer gets the project's `REVIEW.md` if any. The report names the number of rounds.

#### Scenario: The second round
- **WHEN** after the first round the author fixed one `Important` finding
- **THEN** the second-round reviewer gets the diff since the first round and the list of given findings; it does not repeat a finding it already gave

#### Scenario: The review did not converge
- **WHEN** after the third round an `Important` remains
- **THEN** there is no fourth round, the change is not archived, `Not Verified` has the finding and "reconsider the approach"

#### Scenario: The project's review rules
- **WHEN** the project root has `REVIEW.md`
- **THEN** the reviewer gets it together with the delta specs

### Requirement: Reviewer failure
If the reviewer ended with an error, returned an empty answer or gave no verdict on every requirement of the change, acceptance SHALL count as not passed, not passed successfully. In each round the agent SHALL once rerun the reviewer with the same task; such a run does not count as a round. A second failure in the same round sends the requirements without a verdict into `Not Verified`, the change is not archived, the report names the reviewer failure.

#### Scenario: The reviewer crashed
- **WHEN** the subagent `Review: <id>` returned a tool error without a verdict
- **THEN** the reviewer is rerun with the same task, the round counter did not grow

#### Scenario: A verdict not on all requirements
- **WHEN** the reviewer gave a verdict on two requirements of three
- **THEN** acceptance is not passed; after the second such answer the third requirement goes into `Not Verified`, no archive

#### Scenario: Failures in different rounds
- **WHEN** in the first round the reviewer crashed and the rerun gave a verdict, and in the second round the reviewer crashed again
- **THEN** the second round has its own rerun, this is not a second failure; if the rerun gave a verdict without open `Important` findings, the change is archived
