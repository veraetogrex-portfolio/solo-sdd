## Purpose

`spec-analyze` finds, before code, a change whose tasks name values other than its requirements do, and a change whose tasks and deltas build something other than what its proposal promises.

## ADDED Requirements

### Requirement: Task values match the requirement
Pass 7 of `spec-analyze` SHALL compare every value a task names in backquotes (a number, a setting key, a path, a command, an output line) with the value any requirement or scenario of the deltas names for the same thing, known by what both texts say it is for: a key spelled otherwise names the same setting. A different value SHALL be one HIGH finding under pass 7 naming both, not also a pass 5 term drift. A value for a thing no requirement names gives no finding.

#### Scenario: A different default
- **WHEN** a requirement says the setting `process.retry` defaults to `3`, and the task that registers it says default `5`
- **THEN** pass 7 reports one HIGH finding naming `3` and `5`, pass 5 reports nothing for it, and the author fixes the task

#### Scenario: A drifted key in a task without a requirement name
- **WHEN** a scenario names `process.analyze-attackers` as the number of attackers, and a task that names no requirement registers the number of attackers as `process.analyze-attacker`
- **THEN** pass 7 reports a HIGH finding naming both keys

#### Scenario: The requirement is the wrong one
- **WHEN** the author judges the task's value right and the requirement's wrong
- **THEN** the fix goes into the delta, and `Decisions Without Owner` has a line naming both values

#### Scenario: A value only the task names
- **WHEN** a task names its test file `tests/test_retry.py`, and no requirement names a test file
- **THEN** pass 7 gives no finding for it

### Requirement: Retell against the proposal
Pass 1 of `spec-analyze` SHALL first read only `tasks.md` and the delta specs and write a retell of at most five lines of what the user gets, then read `proposal.md`. A line covers a What Changes item when it names the file, command, setting or behaviour the item names. An item no line covers SHALL be HIGH; a retell line, task or delta requirement no item covers SHALL be MEDIUM. The retell SHALL stand as a `Retell:` block above the findings table of the report.

#### Scenario: A promise without work
- **WHEN** What Changes says `docs/hooks.md` names the new rule, and no task or requirement names `docs/hooks.md`
- **THEN** pass 1 reports a HIGH finding naming that item, and the report has the `Retell:` block without it

#### Scenario: Work without a promise
- **WHEN** a task registers a new setting that no What Changes item names
- **THEN** pass 1 reports a MEDIUM finding naming the setting, whether or not the retell names it

#### Scenario: Retell and proposal agree
- **WHEN** every What Changes item is covered by a retell line, and every line, task and delta requirement by an item
- **THEN** pass 1 gives no retell finding, and the report still has the `Retell:` block

#### Scenario: Under the outside run
- **WHEN** `process.analyze-attackers` is `3`, and the attacker of group one `1 2 3 3a` writes the retell
- **THEN** it returns the `Retell:` block above its findings table, and the judge reads the block to mark the retell findings and gives the author the block above the judged table; when two or more attackers take group one, each block is named by its attacker
