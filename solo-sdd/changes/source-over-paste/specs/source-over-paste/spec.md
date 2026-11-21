## Purpose

A pasted excerpt of a file, log, report or chat is read at its source when the agent can reach it, because an excerpt may be cut or stale; a source out of reach is named with the access that would give it.

## ADDED Requirements

### Requirement: Read the source of a pasted excerpt
The global rules SHALL require a pasted excerpt of a file, log, report or chat to be read at its source before use when within reach: the project folder, the session's added working folders, this project's agent session logs and its PRs. The source SHALL be what the excerpt or message names, else the file within reach holding its lines verbatim, outside archives first. The source SHALL win over a differing excerpt, said to differ, and the answer SHALL quote the source line it rests on.

#### Scenario: A cut excerpt
- **WHEN** the owner pastes lines 1-5 of a project file without naming it and asks a question whose answer line 6 of that file changes
- **THEN** the agent finds the file by a search of the project folder, and its answer quotes line 6

#### Scenario: A stale excerpt
- **WHEN** the named file's line differs from the pasted one
- **THEN** the answer quotes the file's line and says the excerpt differs from it

#### Scenario: Lines in two files
- **WHEN** an unnamed excerpt's lines stand verbatim in a project file and in its older copy under an archive folder (`notes/archive/`, `solo-sdd/changes/archive/`)
- **THEN** the source is the file outside the archive

### Requirement: Mark an answer built on an excerpt
When the source of a pasted excerpt cannot be read, the global rules SHALL require one line in the answer, in English in any reply language, and the work SHALL go on from the excerpt: `Based on an excerpt: <path> does not exist` for an absent path within reach, `Based on an excerpt: read access to <path>` for a path outside reach or unreadable, `Based on an excerpt: no source found in <folders>` for an unnamed excerpt no file holds. A path outside reach SHALL NOT be opened, listed or searched.

#### Scenario: A source out of reach
- **WHEN** the pasted excerpt names a log under a path outside the agent's folders
- **THEN** the answer has `Based on an excerpt: read access to <that path>` and the agent does not read the path

#### Scenario: A missing source
- **WHEN** the excerpt names a project file that does not exist
- **THEN** the answer has `Based on an excerpt: <the named path> does not exist`

#### Scenario: No file holds the excerpt
- **WHEN** an unnamed excerpt's lines stand in no file within reach
- **THEN** the answer has `Based on an excerpt: no source found in <the searched folders>`

### Requirement: Relay reads the report's source
`relay` step 1 SHALL find the source of the pasted report and read it before step 2 parses the report: the change folder the report names (`solo-sdd/changes/<id>/` or its archive copy), its PR by `gh pr view`, the other agent's session log where `context-resume` reads it. A source out of reach or absent SHALL give the `Based on an excerpt:` line of the global rules in the relay report, and a path outside reach SHALL NOT be opened, listed or searched.

#### Scenario: A report with a change folder
- **WHEN** a pasted report names the change `add-csv` and claims its Live Scenario passed, and the `Result` of `solo-sdd/changes/add-csv/verification.md` says it failed
- **THEN** `relay` reads that file before step 2, and its report has `Refuted: <the claim> — solo-sdd/changes/add-csv/verification.md`

#### Scenario: A report naming a path out of reach
- **WHEN** a pasted report cites a log under a path outside the agent's folders as its proof
- **THEN** the relay report has `Based on an excerpt: read access to <that path>` and the path is not read
