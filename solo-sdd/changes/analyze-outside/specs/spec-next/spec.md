## MODIFIED Requirements

### Requirement: Lead writes code
Outside the "Under the dispatcher" mode the lead agent SHALL do the change tasks itself, including code. It launches subagents only for independent acceptance (step 7a), the outside `spec-analyze` run of step 4a (`Analyze:`, `Attack:`, `Judge:`) and heavy reading (role `lookup` of `model-guard`). The exception: the owner named `codex-orchestration`, or the project sets `agents.executor: codex`; then Codex executors write the code, and the lead agent accepts the result with its own commands.

#### Scenario: A change in two areas
- **WHEN** a change has six tasks in two modules, and the owner did not name Codex
- **THEN** the lead agent writes the code; only subagents with the tags `Review:`, `Lookup:`, `Analyze:`, `Attack:` and `Judge:` are launched

#### Scenario: The owner named Codex
- **WHEN** the owner's request names `codex-orchestration`
- **THEN** Codex executors write the code by this skill, the lead agent accepts the result with its own commands
