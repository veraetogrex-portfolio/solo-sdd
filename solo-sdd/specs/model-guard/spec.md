# model-guard Specification

## Purpose
The model guard of the Claude Code hooks: Codex tests and search run on inexpensive models, review and acceptance on the main model, expensive models in subagents are limited by role and by who launches them, and only the owner can allow an expensive model against the rules.

## Requirements

### Requirement: Subagent role by description prefix
The guard SHALL determine a subagent's role by an explicit tag at the start of the `description` field of an `Agent` call by the role list from `global/model-policy.json`; descriptions without a tag get the role `general`, the role `implement` follows the same rules as `general`.

#### Scenario: An executor writes code with tests
- **WHEN** the main session or a subagent launches `Agent` with the description "Write a.py and test" and `model: sonnet`
- **THEN** the role is `general`; the reviewer rule does not apply to it

#### Scenario: A reviewer on an expensive model
- **WHEN** `Agent` is launched with the description "Review: add-words" and `model: opus` or without `model`
- **THEN** the role is `review`, the launch passes: review runs on the main model

#### Scenario: A domain word in an executor's description
- **WHEN** a subagent launches "Implement: acceptance core module" or "Acceptance core module" with `model: sonnet`
- **THEN** the role is `implement` or `general`, not `review`

#### Scenario: Search
- **WHEN** "Lookup: where the limit is set" is launched
- **THEN** the role is `lookup`

#### Scenario: Role tags
- **WHEN** the `Agent` call description starts (ignoring case and leading spaces) with `Review:`, with `Orchestrator` (with a colon or a space after the word), with `Implement:`, with `Lookup:`
- **THEN** the role is respectively `review`, `orchestrator`, `implement`, `lookup`; other descriptions, including those with the old Russian review, executor and search tags, are `general`

#### Scenario: Words without a tag
- **WHEN** the description holds `Acceptance`, `Test`, `Independent review`, `Re-review` without a tag, or role words further in the description
- **THEN** they do not affect the role

### Requirement: Models allowed per role and caller
The guard SHALL apply the rules by role and by who launches (`agent_id` in the hook input means a subagent launches, none means the main session); the rules of each role are set by the scenarios.

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

### Requirement: Owner-only expensive override
The model rules bypass SHALL work only with `SOLO_SDD_EXPENSIVE_OK=1` in the hook process environment. The word `EXPENSIVE_OK` in a subagent description or in a Bash command text does not turn the bypass on. The bypass lifts the model limits; it does not lift the rule "only the main session launches an orchestrator". Refusal messages do not name the bypass and say that the owner allows an expensive model.

#### Scenario: The agent added EXPENSIVE_OK
- **WHEN** "Review: add-words EXPENSIVE_OK" is launched with `model: sonnet`, and there is no variable in the environment
- **THEN** the launch is refused, the refusal text does not contain `EXPENSIVE_OK`

#### Scenario: The owner allowed an expensive model
- **WHEN** the hook runs with `SOLO_SDD_EXPENSIVE_OK=1` in the environment, and "Review: add-words" is launched with `model: opus`
- **THEN** the launch passes; `codex exec -m gpt-6-astra` in Bash passes too

### Requirement: Agent cannot enable override
The guard SHALL refuse agent actions that carry `SOLO_SDD_EXPENSIVE_OK` into the environment of future Claude Code sessions: a write through Write, Edit or MultiEdit into the files of the requirement Override carrier files if the new text holds this name; a Bash command that holds this name and writes into one of these files (redirection `>`, `>>`, `>|`, `tee`, `sed -i`), and `launchctl setenv` with this name. Reading and searching for the name are not refused.

#### Scenario: An attempt to enable the bypass through settings
- **WHEN** the agent writes into `~/.claude/settings.json` an `env` block with `SOLO_SDD_EXPENSIVE_OK`
- **THEN** the write is refused

#### Scenario: An attempt through the shell profile
- **WHEN** the agent runs `echo 'export SOLO_SDD_EXPENSIVE_OK=1' >> ~/.zshrc`
- **THEN** the command is refused

#### Scenario: A code search and a one-command environment
- **WHEN** the agent runs `grep -rn SOLO_SDD_EXPENSIVE_OK global` or `SOLO_SDD_EXPENSIVE_OK=1 python3 tests/test_work_hooks.py`
- **THEN** the command passes

#### Scenario: A separate command's environment
- **WHEN** the variable is set in the environment of a separate command (`SOLO_SDD_EXPENSIVE_OK=1 python3 …`)
- **THEN** the command is not refused: it does not change the session hooks' environment

### Requirement: Override carrier files
The settings and shell profile files in the requirement Agent cannot enable override SHALL be: `settings.json` and `settings.local.json` in the `.claude` folder, `.zshenv`, `.zshrc`, `.zprofile`, `.bashrc`, `.bash_profile`, `.profile`.

#### Scenario: Local project settings
- **WHEN** the agent writes through Edit into `.claude/settings.local.json` a text with `SOLO_SDD_EXPENSIVE_OK`
- **THEN** the write is refused

#### Scenario: The bash profile
- **WHEN** the agent runs `echo 'export SOLO_SDD_EXPENSIVE_OK=1' | tee -a ~/.bash_profile`
- **THEN** the command is refused

### Requirement: Test model allowlist
`guard` SHALL refuse a Bash test command outside Codex that names a model with `--model <name>` or `--model=<name>` unless the model is under `cheap` in `model-policy.json`; the refusal SHALL name the cheap models. `-m` and `model=` values SHALL keep the current check against `expensive`, since `-m` also means a Python module or a pytest marker. Codex launches keep their rules. Owner-only expensive override SHALL still apply.

#### Scenario: An unknown expensive model
- **WHEN** the agent runs `pytest --model gpt-9-ultra`
- **THEN** the command is refused, the reason names the cheap models

#### Scenario: A cheap model
- **WHEN** the agent runs `pytest --model=<a model under cheap>`
- **THEN** the command passes

#### Scenario: A module and a marker
- **WHEN** the agent runs `python3 -m pytest -m slow tests`
- **THEN** the command passes

#### Scenario: The owner override
- **WHEN** the hook runs with `SOLO_SDD_EXPENSIVE_OK=1` and the agent runs `pytest --model gpt-9-ultra`
- **THEN** the command passes
