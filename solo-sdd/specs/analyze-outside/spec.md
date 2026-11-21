# analyze-outside Specification

## Purpose
The `spec-analyze` check before code runs outside the session that wrote the change: cheap attackers each try to prove the change is not ready on their own pass group, a judge on the main model keeps or drops their findings, and the author fixes what was kept.

## Requirements

### Requirement: Analyze outside the author
When `spec-plan` step 7a or `spec-next` step 4a runs `spec-analyze` and `process.analyze` is `on`, the passes SHALL run in subagents, never in the session that wrote or implements the change, except in an agent without a subagent tool (Passes in place). Every such subagent SHALL get the artifact paths, the main specs of the affected capabilities and the project rules, and SHALL NOT get the planner's reasoning, reports or chat history.

#### Scenario: One clean analyzer
- **WHEN** `process.analyze-attackers` is `0`, and `spec-plan` created the change `add-csv`
- **THEN** the planner launches one `Analyze: add-csv` subagent, without `model` or with `agents.review-model` when it is set, whose prompt names the artifact paths, the affected main specs and the project rules, and runs no pass itself

#### Scenario: Analyze switched off
- **WHEN** the file has `process.analyze: off`
- **THEN** no `Analyze:`, `Attack:` or `Judge:` subagent starts, and the report has `Analyze: off (solo-sdd/config)`

### Requirement: Passes in place
The passes SHALL run in place, with no subagent launched, inside an `Analyze:`, `Attack:` or `Judge:` subagent, on a direct `/spec-analyze` call by the user, and in an agent without a subagent tool; the last SHALL report `Analyze: in session (no subagent tool)`. Inside those three subagents the passes SHALL edit no file and return the findings table to the author; the author's edit is the `spec-analyze` fix other capabilities name.

#### Scenario: Inside an attacker
- **WHEN** an `Attack: add-csv 4 4a` subagent reads the laid-out `spec-analyze`
- **THEN** it runs passes 4 and 4a itself, launches no subagent, and the change folder is unchanged after it returns its findings

#### Scenario: No subagent tool
- **WHEN** `spec-next` runs in an agent that has no subagent tool
- **THEN** the passes run in the session, and the report has `Analyze: in session (no subagent tool)`

### Requirement: Attackers and a judge
With `process.analyze-attackers` N > 0 the author SHALL launch N `Attack: <id> <passes>` subagents with `model` from `agents.attack-model`, each tasked to prove the change is not ready on its pass group: 1, 2, 3, 3a; 4, 4a; 5, 6, 7, 7a, 7b. Then one `Judge: <id>` on the main model SHALL get every finding and the artifacts, merge duplicates and mark each `keep` with a level or `drop` with a reason.

#### Scenario: The default three attackers
- **WHEN** the file has no `process.analyze-attackers`, and `spec-next` takes `add-csv`
- **THEN** it launches `Attack: add-csv 1 2 3 3a`, `Attack: add-csv 4 4a` and `Attack: add-csv 5 6 7 7a 7b` on `haiku`, then one `Judge: add-csv` with their findings

#### Scenario: Fewer or more attackers than groups
- **WHEN** N is 1, 2, 4 or 7
- **THEN** with 1 the attacker takes all three groups; with 2 the first takes groups one and two and the second group three; with N of 3 or more attacker i takes group ((i - 1) mod 3) + 1

#### Scenario: A duplicate finding
- **WHEN** two attackers report the same requirement without a task
- **THEN** the judge keeps one merged finding naming both attackers

### Requirement: Findings after the judge
The author SHALL fix every kept CRITICAL and HIGH in the artifacts; a kept finding it does not fix SHALL get a `Decisions Without Owner` line with the reason. With N = 0 every finding counts as kept. When the outside run ran, the `spec-plan` and `spec-next` reports SHALL hold `Analyze: <n> findings, kept <k>, dropped <d>; CRITICAL <c> · HIGH <h>, fixed <f>` in place of the old line; otherwise the line stays `Analyze: off (solo-sdd/config)` or `Analyze: in session (no subagent tool)`.

#### Scenario: A kept finding the author refuses
- **WHEN** the judge keeps a HIGH finding that the author judges wrong
- **THEN** `Decisions Without Owner` has a line naming the finding and the reason, and the change is still started

#### Scenario: The report line
- **WHEN** three attackers gave 9 findings, the judge kept 4 (1 CRITICAL, 2 HIGH) and dropped 5, and the author fixed 3
- **THEN** the report has `Analyze: 9 findings, kept 4, dropped 5; CRITICAL 1 · HIGH 2, fixed 3`

#### Scenario: One analyzer
- **WHEN** N is 0, and `Analyze:` gave 6 findings
- **THEN** the report line starts with `Analyze: 6 findings, kept 6, dropped 0`

### Requirement: Repeat after the author's edits
After the author's edits and `solo-sdd validate <id>`, the repeat of passes 1, 2, 7 and 7a SHALL run in one `Analyze: <id> 1 2 7 7a` subagent, except in an agent without a subagent tool (Passes in place); its findings go to the author with no judge.

#### Scenario: A fix opens a hole
- **WHEN** the author's fix of coverage adds a task that waits for a person
- **THEN** the repeat subagent reports it under pass 2, and the author moves it into `Needs`
