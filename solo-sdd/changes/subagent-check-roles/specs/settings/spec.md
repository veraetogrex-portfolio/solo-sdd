## ADDED Requirements

### Requirement: Attack model setting
`agents.attack-model` (default `haiku`) SHALL take one model name; the guard hook SHALL read it as the key of the `attack` role (Project models within the machine policy).

#### Scenario: The default attack model
- **WHEN** the file has no `agents.attack-model`
- **THEN** `config list` prints `agents.attack-model haiku default`

## MODIFIED Requirements

### Requirement: Project models within the machine policy
When the event folder's `solo-sdd/config` sets `agents.orchestrator-model`, `agents.review-model`, `agents.lookup-model` or `agents.attack-model`, the guard hook SHALL refuse a launch of that key's roles on that model outside their machine list, naming the key and the list. `SOLO_SDD_EXPENSIVE_OK=1` lifts it; a broken config SHALL keep the role rules alone and write `errors.log`. `agents.test-model` SHALL stay bound by Test model allowlist.

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

#### Scenario: The roles and lists of each key
- **WHEN** a role model key is set in the file
- **THEN** `agents.orchestrator-model` bounds the orchestrator by `main`; `agents.review-model` bounds review, analyze, judge and check by `main`; `agents.lookup-model` bounds lookup and `agents.attack-model` bounds attack by `cheap`

#### Scenario: A project widens the attack model
- **WHEN** the file has `agents.attack-model: sonnet`, and a subagent launches `Attack: a 4 4a` on `sonnet`
- **THEN** the hook denies it, and the reason names `agents.attack-model` and the `cheap` list

#### Scenario: A judge on a project review model
- **WHEN** the file has `agents.review-model: fable`, `fable` is in `main`, and a subagent launches `Judge: a` on `fable`
- **THEN** the hook allows it
