## Purpose

A pasted excerpt of a file, log, report or chat is read at its source when the agent can reach it, because an excerpt may be cut or stale; a source out of reach is named with the access that would give it.

## ADDED Requirements

### Requirement: Read the source of a pasted excerpt
The global rules SHALL require that a pasted excerpt of a file, log, report or chat is read at its source before it is used when the agent can reach it. The source SHALL be what the excerpt or the message names, or the project file that holds its lines verbatim (one search of the project folder). A source out of reach SHALL give the line `Based on an excerpt: <the access that would give the source>`.

#### Scenario: A cut excerpt
- **WHEN** the owner pastes lines 1-5 of a project file without naming it and asks a question whose answer line 6 of that file changes
- **THEN** the agent finds the file by one search, and its answer quotes line 6

#### Scenario: A source out of reach
- **WHEN** the pasted excerpt names a log under a path outside the agent's folders
- **THEN** the answer has `Based on an excerpt: read access to <that path>`

#### Scenario: A missing source
- **WHEN** the excerpt names a project file that does not exist
- **THEN** the answer has `Based on an excerpt: <the named path> does not exist`

### Requirement: Relay reads the report's source
`relay` step 1 SHALL look for the source of the pasted report (the other agent's session log, the change folder, the PR) and read it before parsing the report; a source out of reach SHALL be named with the access that would give it.

#### Scenario: A report with a change folder
- **WHEN** a pasted report names the change `add-csv` and claims its Live Scenario passed, and the `Result` of `solo-sdd/changes/add-csv/verification.md` says it failed
- **THEN** `relay` reads that file before step 2, and its report has `Refuted: <the claim> — solo-sdd/changes/add-csv/verification.md`
