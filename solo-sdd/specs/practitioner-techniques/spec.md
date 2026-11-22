# practitioner-techniques Specification

## Purpose
Work in a field no spec, lesson or skill of the agent covers starts from the tools, techniques and checks a practitioner of that field uses, each with a source, and prompts to subagents carry no persona.

## Requirements

### Requirement: Practitioner list in a new field
Section 14 of the global rules SHALL require that work in a field where no project spec, `## Lessons` line or laid-out skill names any of that field's checks is preceded by a `Practitioner checks:` list of at least three tools, techniques or checks a practitioner of the field uses, each with a source; the work uses them, and the report holds the list and a `Practitioner checks run:` line naming which ran. A field where one of them names a check is covered: that check is used.

#### Scenario: Money rounding
- **WHEN** an agent is asked to check the rounding of a tip calculator, and no spec, lesson or laid-out skill names a money rounding check
- **THEN** its report holds a `Practitioner checks:` list of at least three items (for example decimal arithmetic instead of binary floats, the rounding mode, the minor units of the currency), each `<check> — <source>` where the source is a link or a named standard (`ISO 4217`, `IEEE 754`), and a `Practitioner checks run: <items>` line naming which of them ran

### Requirement: Practitioner list in a plan
`spec-plan` SHALL put a `Practitioner checks:` line into What Changes of the proposal of a change in such a field, listing the items the change uses with their sources, and SHALL give each item a task or a Live Scenario step that names it.

#### Scenario: A change in a new field
- **WHEN** `spec-plan` plans a change about money rounding, and no spec, lesson or laid-out skill names a money rounding check
- **THEN** What Changes of the proposal has the `Practitioner checks:` line with at least three items with sources, and each item is named by a task or a Live Scenario step

### Requirement: No persona prompts
`skills/`, `global/AGENTS.md`, `ALGORITHM.md` and `templates/` SHALL hold no line that gives the reader a level of skill: `you are` or `act as` followed by a level word (expert, senior, seasoned, experienced, veteran, principal, world-class, top-notch), or `world-class` anywhere; `integrations/` (pinned copies) is out of the check. A role line that names a role and its actions SHALL pass. Section 14 SHALL ban a level of skill in a prompt to a subagent.

#### Scenario: A persona added to a skill
- **WHEN** a skill gets the line "You are an expert reviewer"
- **THEN** the persona test fails naming the file and the line

#### Scenario: A role line
- **WHEN** a skill holds "You are the dispatcher: you launch orchestrators", "You are the Opus orchestrator of change <ID>" or "Act as the orchestrator."
- **THEN** the persona test passes

#### Scenario: The ban in the global rules
- **WHEN** section 14 of `global/AGENTS.md` is read
- **THEN** it says a prompt to a subagent sets no level of skill, and gives the field's checks instead
