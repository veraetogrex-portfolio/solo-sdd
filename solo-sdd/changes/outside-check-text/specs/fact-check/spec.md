## Purpose

An analysis, a research or a text for other people is checked before it is handed over by a `Check:` subagent that did not write it: every number, date, version and named fact from an outside source is matched against its primary source, wrong values are fixed and facts without a primary source are marked.

## ADDED Requirements

### Requirement: Outside fact check before handover
Before an analysis, research or text for other people that holds a number, date, version or named fact from an outside source is handed over, the global rules and `evidence-research` SHALL require one `Check:` subagent that did not write it. It SHALL get the text and its source list, not the reasoning, and return `| fact | mark | right value | source |` with each mark `confirmed`, `wrong` or `no primary source`.

#### Scenario: Three planted errors
- **WHEN** a text of 11 facts with a wrong release date, a wrong version and a wrong price, local primary sources for 10 of them and none for the 11th, goes to `Check:`
- **THEN** the three are marked `wrong` with the values of their sources, the seven others with sources `confirmed`, the 11th `no primary source`

#### Scenario: Not covered
- **WHEN** the text is a skill report, a change artifact, an agent status line, or a text with no fact from an outside source
- **THEN** no `Check:` subagent runs

### Requirement: Fact check without a subagent tool
An agent without a subagent tool SHALL check each fact against its primary source itself and write `Check: in session (no subagent tool)` in place of the counts.

#### Scenario: An agent without subagents
- **WHEN** `evidence-research` runs in an agent that has no subagent tool
- **THEN** the answer ends with `Check: in session (no subagent tool)`

### Requirement: Fixes and a counter-argument after the check
The author SHALL fix every `wrong` value before handover and move every `no primary source` fact under `Not confirmed:`; a second `Check:` pass SHALL cover only the fixed lines. A recommendation SHALL get one line from `Check:`: the strongest argument against it. `evidence-research` SHALL end its answer with `Check: confirmed <n>, fixed <n>, not confirmed <n>`.

#### Scenario: The handed-over answer
- **WHEN** an `evidence-research` answer on the stand's sources recommends one option
- **THEN** it holds the three corrected values, the 11th fact under `Not confirmed:`, one line with the strongest argument against the recommendation and `Check: confirmed 7, fixed 3, not confirmed 1`
