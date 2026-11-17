## ADDED Requirements

### Requirement: Change size limits
`solo-sdd validate` SHALL refuse more tasks in `tasks.md` than `process.max-tasks` (default 10) and a requirement longer than `process.requirement-max-chars` (default 500), naming the limit and its source. `spec-plan` and `spec-analyze` SHALL take these and `process.bugfix-max-tasks` (default 5) through `solo-sdd config get`; a bug fix takes the smaller task limit. `config set` SHALL refuse a task limit below 3 and a length below 100. 10, 5 and 500 in other requirements name these defaults.

#### Scenario: A project with larger units
- **WHEN** the file has `process.max-tasks: 14`, and a change has 12 tasks
- **THEN** `solo-sdd validate <id>` passes it

#### Scenario: The default limit
- **WHEN** the file has no `process.max-tasks`, and a change has 11 tasks
- **THEN** `validate` fails with `too many tasks: 11 > 10 (default)`

#### Scenario: A file limit on length
- **WHEN** the file has `process.requirement-max-chars: 300`, and a requirement text has 400 characters
- **THEN** `validate` fails naming `400 > 300 (file)`

#### Scenario: A limit no change can meet
- **WHEN** `config set process.max-tasks 2` runs
- **THEN** exit 1 names `3`: the `Acceptance` group alone holds two tasks; the file is unchanged

### Requirement: Process cadence settings
`spec-next` SHALL propose `spec-audit` when the archive count after its archive is a multiple of `process.audit-every` (default 5). With `process.analyze: off` `spec-plan` and `spec-next` SHALL skip the `spec-analyze` pass, and their report SHALL hold `Analyze: off (solo-sdd/config)`. `spec-plan`, `spec-next` and `ALGORITHM.md` SHALL let an agent change the five keys only on the owner's words in the chat.

#### Scenario: Analyze switched off
- **WHEN** the file has `process.analyze: off`
- **THEN** the laid-out `spec-next` text skips the analyze gate for this setting and names the report line `Analyze: off (solo-sdd/config)`

#### Scenario: Audit every three archives
- **WHEN** the file has `process.audit-every: 3`
- **THEN** the laid-out `spec-next` text reads `process.audit-every` and names `Time for: /spec-audit on the main specs` at a multiple of it
