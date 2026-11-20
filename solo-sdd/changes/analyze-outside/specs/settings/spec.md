## ADDED Requirements

### Requirement: Analyze attackers setting
`process.analyze-attackers` SHALL take an integer of at least 0 (default `3`): the number of `Attack:` subagents of the outside `spec-analyze` run, `0` for one `Analyze:` subagent. `spec-plan` and `spec-next` SHALL read it.

#### Scenario: The default
- **WHEN** the file has no `process.analyze-attackers`
- **THEN** `config list` prints `process.analyze-attackers 3 default`

#### Scenario: A negative value
- **WHEN** `config set process.analyze-attackers -1` runs
- **THEN** exit 1 with `process.analyze-attackers takes a whole number from 0`, the file is unchanged

## MODIFIED Requirements

### Requirement: Process cadence settings
`spec-next` SHALL propose `spec-audit` when the archive count after its archive is a multiple of `process.audit-every` (default 5). With `process.analyze: off` `spec-plan` and `spec-next` SHALL skip the `spec-analyze` pass, and their report SHALL hold `Analyze: off (solo-sdd/config)`. `spec-plan`, `spec-next` and `ALGORITHM.md` SHALL let an agent change the six keys (with `process.analyze-attackers`) only on the owner's words in the chat.

#### Scenario: Analyze switched off
- **WHEN** the file has `process.analyze: off`
- **THEN** the laid-out `spec-next` text skips the analyze gate for this setting and names the report line `Analyze: off (solo-sdd/config)`

#### Scenario: Audit every three archives
- **WHEN** the file has `process.audit-every: 3`
- **THEN** the laid-out `spec-next` text reads `process.audit-every` and names `Time for: /spec-audit on the main specs` at a multiple of it

#### Scenario: The owner-only keys
- **WHEN** the laid-out `spec-plan`, `spec-next` and `ALGORITHM.md` are read
- **THEN** each names `process.analyze-attackers` among the keys an agent changes only on the owner's words in the chat
