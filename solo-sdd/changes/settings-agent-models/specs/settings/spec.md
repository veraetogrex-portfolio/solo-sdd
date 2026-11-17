## ADDED Requirements

### Requirement: Subagent model settings
`agents.orchestrator-model` (default `opus`), `agents.review-model` (empty: the session's main model), `agents.lookup-model` and `agents.test-model` (`haiku`, the latter for paid product calls in tests) SHALL take one model name, `agents.dispatcher-effort` one of `low`, `medium`, `high` (default `low`). `spec-dispatch`, `spec-next`, `spec-audit` and the global rules SHALL read them; `opus`, `Opus` and `/effort low` in other requirements name these defaults.

#### Scenario: Another orchestrator model
- **WHEN** the file has `agents.orchestrator-model: fable`
- **THEN** the laid-out `spec-dispatch` text tells the dispatcher to read `agents.orchestrator-model` and launch each orchestrator with that model, `opus` when it is not set

#### Scenario: A model name with a space
- **WHEN** `config set agents.lookup-model "haiku 4"` runs
- **THEN** exit 1 names one model name of ASCII letters, digits, `.`, `-`, `_`, `[` and `]`, the file is unchanged

#### Scenario: The defaults
- **WHEN** the file has none of the six keys
- **THEN** `config list` prints `agents.orchestrator-model opus default` and `agents.dispatcher-effort low default`

### Requirement: Executor setting from the owner
`agents.executor` (`self`, `codex`; default `self`): `codex` SHALL count as the owner naming `codex-orchestration`. The global rules SHALL let an agent set or unset `agents.executor` only on the owner's words in the chat.

#### Scenario: Codex as the executor
- **WHEN** the file has `agents.executor: codex`, and the owner asks `spec-next` to take a change without naming Codex
- **THEN** Codex executors write the code by `codex-orchestration`, the lead agent accepts the result with its own commands

### Requirement: Project models within the machine policy
When the event folder's `solo-sdd/config` sets `agents.orchestrator-model`, `agents.review-model` or `agents.lookup-model`, the guard hook SHALL refuse a launch of that role on that model while the model is outside the role's machine list (`main` for orchestrator and review, `cheap` for lookup), naming the key and the list. `SOLO_SDD_EXPENSIVE_OK=1` lifts it; a broken config SHALL keep the role rules alone and write `errors.log`. `agents.test-model` SHALL stay bound by Test model allowlist.

#### Scenario: A project widens the lookup model
- **WHEN** the file has `agents.lookup-model: sonnet`, and a `Lookup:` subagent of type `Explore` starts on `sonnet`
- **THEN** the hook denies it, and the reason names `agents.lookup-model` and the `cheap` list

#### Scenario: A cheaper orchestrator
- **WHEN** the file has `agents.orchestrator-model: sonnet`, and the main session launches `Orchestrator a` on `sonnet`
- **THEN** the hook denies it, and the reason names `agents.orchestrator-model` and the `main` list

#### Scenario: A project narrows the review model
- **WHEN** the file has `agents.review-model: fable`, `fable` is in `main`, and a `Review:` subagent starts on `fable`
- **THEN** the hook allows it

#### Scenario: A broken config
- **WHEN** the file has a broken line, and the main session launches `Orchestrator a` on `sonnet`
- **THEN** the hook allows it by the role rules, and the temporary home's `errors.log` names the line
