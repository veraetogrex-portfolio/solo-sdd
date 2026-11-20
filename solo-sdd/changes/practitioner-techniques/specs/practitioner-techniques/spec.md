## Purpose

Work in a field no spec, lesson or skill of the agent covers starts from the tools, techniques and checks a practitioner of that field uses, each with a source, and prompts to subagents carry no persona.

## ADDED Requirements

### Requirement: Practitioner list in a new field
The global rules SHALL require that work in a field no project spec, lesson or skill laid out for the agent covers starts with a short list of the tools, techniques and checks a practitioner of that field uses, each with a source; the work then uses them, and the report names which ones ran.

#### Scenario: Money rounding
- **WHEN** an agent is asked to check the rounding of a tip calculator, and no spec, lesson or laid-out skill covers money rounding
- **THEN** its answer first lists the practitioner's checks (for example decimal arithmetic instead of binary floats, the rounding mode, the minor units of the currency) each with a source, and the report names which of them ran

### Requirement: Practitioner list in a plan
`spec-plan` SHALL put that list into the proposal of a change in such a field, with a task or Live Scenario step for each item the change uses.

#### Scenario: A change in a new field
- **WHEN** `spec-plan` plans a change about money rounding, and no spec, lesson or laid-out skill covers it
- **THEN** the proposal has the list with sources, and each item it uses has a task or a Live Scenario step

### Requirement: No persona prompts
`skills/`, `global/AGENTS.md`, `ALGORITHM.md` and `templates/` SHALL hold no persona prompt that sets a level of skill ("you are an expert", "you are a senior", "world-class"); `integrations/` (pinned copies) is out of the check. A role line that sets actions and bans ("You are the dispatcher") SHALL stay allowed.

#### Scenario: A persona added to a skill
- **WHEN** a skill gets the line "You are an expert reviewer"
- **THEN** the persona test fails naming the file and the line

#### Scenario: A role line
- **WHEN** a skill holds "You are the dispatcher: you launch orchestrators"
- **THEN** the persona test passes
