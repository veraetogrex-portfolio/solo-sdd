## MODIFIED Requirements

### Requirement: Stop waits for background agents
The `stop` subcommand SHALL skip all readiness checks if the Stop input has at least one `background_tasks` entry with `status: running` whose `type` is neither `shell` nor `monitor`; an entry without `type` counts as an agent. Running `shell` and `monitor` entries alone (a dev server, `tail -f`, a log watch) SHALL NOT skip the checks. If there are no such entries or the field is missing, the checks run as before.

#### Scenario: The dispatcher waits for orchestrators
- **WHEN** Stop comes with `background_tasks` where one `subagent` task is `running`, and the session has an uncommitted edit
- **THEN** `stop` prints nothing and does not return the agent

#### Scenario: All background tasks finished
- **WHEN** Stop comes with `background_tasks` without `running` tasks, and there is an uncommitted edit
- **THEN** `stop` returns the agent with the previous reason about uncommitted edits

#### Scenario: A dev server left running
- **WHEN** Stop comes with only a running `{"type": "shell", "command": "npm run dev"}` entry, or only a running `monitor` entry, and there is an uncommitted edit
- **THEN** `stop` returns the agent with the reason about uncommitted edits

#### Scenario: An agent and a shell together
- **WHEN** Stop comes with a running `shell` entry first and a running `subagent` entry after it, and there is an uncommitted edit
- **THEN** `stop` prints nothing

#### Scenario: Another kind of task
- **WHEN** Stop comes with one running `teammate` entry, or one running entry of an unknown `type` such as `x`, and there is an uncommitted edit
- **THEN** `stop` prints nothing

#### Scenario: An entry without a type
- **WHEN** Stop comes with one running entry that has no `type` field, and there is an uncommitted edit
- **THEN** `stop` prints nothing, as before this change
