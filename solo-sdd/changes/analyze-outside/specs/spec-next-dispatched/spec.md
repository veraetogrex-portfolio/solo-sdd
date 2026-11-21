## MODIFIED Requirements

### Requirement: Orchestrator writes code
In the "Under the dispatcher" mode the orchestrator SHALL do all tasks of the change itself, whatever their number and the number of code areas. It launches subagents only for independent acceptance (step 7a, tag `Review:`), the outside `spec-analyze` run of step 4a (tags `Analyze:`, `Attack:`, `Judge:`) and heavy reading (tag `Lookup:`). The other steps of the mode and the status block do not change.

#### Scenario: A large change
- **WHEN** a change has seven tasks in two code areas
- **THEN** the orchestrator does them itself, its subagents carry only the tags `Review:`, `Lookup:`, `Analyze:`, `Attack:` and `Judge:`, the change is handed back as a status block

#### Scenario: A small change
- **WHEN** a change has two tasks in one module
- **THEN** the orchestrator does them itself and launches only the reviewer and the `Analyze:`, `Attack:` and `Judge:` subagents of step 4a
