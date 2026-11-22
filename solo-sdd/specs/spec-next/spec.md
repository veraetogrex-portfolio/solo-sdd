# spec-next Specification

## Purpose
How the `spec-next` skill runs a change outside the "Under the dispatcher" mode.

## Requirements

### Requirement: Lead writes code
Outside the "Under the dispatcher" mode the lead agent SHALL do the change tasks itself, including code. It launches subagents only for independent acceptance (step 7a), the outside `spec-analyze` run of step 4a (`Analyze:`, `Attack:`, `Judge:`) and heavy reading (role `lookup` of `model-guard`). The exception: the owner named `codex-orchestration`, or the project sets `agents.executor: codex`; then Codex executors write the code, and the lead agent accepts the result with its own commands.

#### Scenario: A change in two areas
- **WHEN** a change has six tasks in two modules, and the owner did not name Codex
- **THEN** the lead agent writes the code; only subagents with the tags `Review:`, `Lookup:`, `Analyze:`, `Attack:` and `Judge:` are launched

#### Scenario: The owner named Codex
- **WHEN** the owner's request names `codex-orchestration`
- **THEN** Codex executors write the code by this skill, the lead agent accepts the result with its own commands

### Requirement: Reviewer on the main model
`spec-next` SHALL run the independent acceptance (step 7a) on the main model: in Claude, an `Agent` subagent with the tag `Review:` without the `model` parameter, or with `model` set to `agents.review-model` when the project sets it. Cheap models stay for search, logs, test output and paid product calls in tests and the live scenario.

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
The first acceptance round SHALL read the whole change diff; every later one only the diff since the last round and the open findings' places, with the list of given findings, which the reviewer does not repeat. At most `process.review-rounds` rounds (default 5) SHALL run, plus Extra round for fix findings. An `Important` left then means no archive: the findings and "reconsider the approach" go into `Not Verified`. The reviewer gets `REVIEW.md` if any; the report names the rounds.

#### Scenario: The second round
- **WHEN** after the first round the author fixed one `Important` finding
- **THEN** the second-round reviewer gets the diff since the first round and the list of given findings; it does not repeat a finding it already gave

#### Scenario: The review did not converge
- **WHEN** `process.review-rounds` is not set, and after the fifth round an `Important` remains on a line the last rework did not change
- **THEN** there is no sixth round, the change is not archived, `Not Verified` has the finding and "reconsider the approach"

#### Scenario: The project's review rules
- **WHEN** the project root has `REVIEW.md`
- **THEN** the reviewer gets it together with the delta specs

#### Scenario: A project limit
- **WHEN** the project's `solo-sdd/config` has `process.review-rounds: 2`, and after the second round an `Important` remains outside the last rework
- **THEN** there is no third round and the change is not archived

### Requirement: Reviewer failure
If the reviewer ended with an error, returned an empty answer, an answer without the line `Important: <n>` or gave no verdict on every requirement, acceptance SHALL count as not passed. In each round the agent SHALL once rerun the reviewer with the same task; such a run does not count as a round. A second failure in the same round sends the requirements without a verdict, or the round's verdict, into `Not Verified`, the change is not archived, the report names the reviewer failure.

#### Scenario: The reviewer crashed
- **WHEN** the subagent `Review: <id>` returned a tool error without a verdict
- **THEN** the reviewer is rerun with the same task, the round counter did not grow

#### Scenario: A verdict not on all requirements
- **WHEN** the reviewer gave a verdict on two requirements of three
- **THEN** acceptance is not passed; after the second such answer the third requirement goes into `Not Verified`, no archive

#### Scenario: Failures in different rounds
- **WHEN** in the first round the reviewer crashed and the rerun gave a verdict, and in the second round the reviewer crashed again
- **THEN** the second round has its own rerun, this is not a second failure; if the rerun gave a verdict without open `Important` findings, the change is archived

#### Scenario: No verdict line
- **WHEN** a reviewer's answer has no line `Important: <n>`, and so has the rerun's
- **THEN** the reviewer was rerun once, the change is not archived, and `Not Verified` names the round's missing verdict

### Requirement: Extra round for fix findings
When the last round is the second or later and every `Important` open after it has all its places in lines the rework before that round changed, one more round SHALL run without asking the owner. An `Important` left after it SHALL mean no archive as in Review rounds; there SHALL be no second extra round. The report SHALL say whether the extra round ran.

#### Scenario: A finding on the fix
- **WHEN** after the fifth round the only open `Important` is on a line the fourth-round rework added
- **THEN** a sixth round runs without a question to the owner, and the report says the extra round ran

#### Scenario: The extra round did not close it
- **WHEN** after the extra round an `Important` remains
- **THEN** there is no further round, the change is not archived, `Not Verified` has the finding and "reconsider the approach"

#### Scenario: A limit of one round
- **WHEN** `process.review-rounds` is 1 and an `Important` remains after the first round
- **THEN** no extra round runs, and the change is not archived

#### Scenario: A finding outside the fix
- **WHEN** after the last round one open `Important` is on a line the last rework did not change
- **THEN** no extra round runs, and the change is not archived

### Requirement: Review verdict line
The answer of every `Review:` agent of step 7a SHALL end with the line `Important: <n>`: the `Important` findings open after this round, new ones and given ones not closed (closed: fixed in the diff, or dropped with the reason the author gives in the list of given findings), `0` when none. The author SHALL gate rework, rounds and the archive on that line.

#### Scenario: A round with one open finding
- **WHEN** a reviewer closes both findings of the last round and gives one new `Important` finding
- **THEN** its answer ends with the line `Important: 1`

#### Scenario: A clean round
- **WHEN** a reviewer gives only `Nit` findings
- **THEN** its answer ends with the line `Important: 0`

#### Scenario: A given finding still open
- **WHEN** in round 2 a reviewer finds the round-1 `Important` finding not fixed and gives no new one
- **THEN** its answer ends with the line `Important: 1`
