## MODIFIED Requirements

### Requirement: Models allowed per role and caller
The guard SHALL apply the rules by role and by who launches (`agent_id` in the hook input means a subagent launches, none means the main session); the rules of each role are set by the scenarios, and a role model the project sets adds the refusal of Project models within the machine policy (capability `settings`).

#### Scenario: An orchestrator from the main session
- **WHEN** the main session launches "Orchestrator add-words" with `model: opus`
- **THEN** the launch passes

#### Scenario: An orchestrator from a subagent
- **WHEN** a subagent launches "Orchestrator add-words"
- **THEN** the launch is refused: only the main session launches orchestrators

#### Scenario: An executor without a model from a subagent
- **WHEN** a subagent launches "Implement words command" without `model`, with `model: opus` or with `model: sonnet`
- **THEN** the launch is refused; the refusal text says the orchestrator writes the change code, and from a subagent `Review:` and `Lookup:` are allowed

#### Scenario: Search not through Explore
- **WHEN** a subagent launches "Lookup: where is the limit" with `subagent_type: general-purpose` and `model: haiku`
- **THEN** the launch is refused: search goes only through `Explore`

#### Scenario: Search through Explore
- **WHEN** a subagent launches "Lookup: where is the limit" with `subagent_type: Explore` and `model: haiku`
- **THEN** the launch passes

#### Scenario: A reviewer on a cheap model
- **WHEN** a subagent launches "Review: 248" with `model: haiku` or `model: sonnet`
- **THEN** the launch is refused; the text names the models of the `main` list and the variant without `model`

#### Scenario: The review role rule
- **WHEN** `Agent` with the role `review` is launched
- **THEN** `model` is not set (inherited from the launcher) or is in the `main` list; a model from `cheap` and `sonnet` are refused with the text that review and acceptance run on the main model

#### Scenario: The orchestrator role rule
- **WHEN** `Agent` with the role `orchestrator` is launched
- **THEN** it is allowed only from the main session, any model

#### Scenario: The lookup role rule
- **WHEN** `Agent` with the role `lookup` is launched
- **THEN** `subagent_type` is `Explore`, `model` is set explicitly and is not in the `expensive` list

#### Scenario: The general and implement roles
- **WHEN** `Agent` with the role `general` or `implement` is launched by the main session or a subagent
- **THEN** from the main session without limits; from a subagent refused with the text that the orchestrator writes the change code itself, and the owner bypass does not lift this rule, like the orchestrator rule; from a subagent only `review` and `lookup` are allowed
