## MODIFIED Requirements

### Requirement: Lead writes code
Outside the "Under the dispatcher" mode the lead agent SHALL do the change tasks itself, including code. It launches subagents only for independent acceptance (step 7a) and heavy reading (the `lookup` role of the capability `model-guard`). The exception: the owner named `codex-orchestration`, or the project sets `agents.executor: codex`; then Codex executors write the code, and the lead agent accepts the result with its own commands.

#### Scenario: A change in two areas
- **WHEN** a change has six tasks in two modules, and the owner did not name Codex
- **THEN** the lead agent writes the code; only subagents with the tags `Review:` and `Lookup:` are launched

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
