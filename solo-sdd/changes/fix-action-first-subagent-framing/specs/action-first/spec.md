## MODIFIED Requirements

### Requirement: Prescribed forms and failed reads
Section 1 of the global rules SHALL hold that a report form and rules on writing files prescribed by a running skill or by the request win over the opening and the file of an analysis, a subagent's report to its caller is not such a result unless its prompt holds the line `Your final message is passed to the owner as your answer.`, and that a data source that cannot be read is reported as a failure naming the source and its error, never as `No action follows:`.

#### Scenario: A database that cannot be read
- **WHEN** the agent is asked to analyse a catalog whose `catalog.db` is not a SQLite file
- **THEN** a line among the first 5 non-empty lines of its answer names `catalog.db` together with a read failure (such as `error`, `cannot`, `not a database`), and no line starts with `No action follows:`

#### Scenario: A report form the request prescribes
- **WHEN** the agent is asked about the catalog and the request says the first line of the answer is `rows: <n>`, nothing before it
- **THEN** the first non-empty line of its answer starts with `rows:`

#### Scenario: A subagent answering for the owner
- **WHEN** a subagent's prompt holds the line `Your final message is passed to the owner as your answer.` and asks it to analyse the catalog in `catalog.db` and say what to work on
- **THEN** within the first 5 non-empty lines of its final message stand one to three list items, each `<action> — <effect>`, and a link to a new Markdown or CSV file in the catalog's project folder that holds them

#### Scenario: A subagent given steps for the owner
- **WHEN** a subagent's prompt holds the line `Your final message is passed to the owner as your answer.` and asks it to count the rows of `catalog.db` and list the five oldest items, with no reason
- **THEN** the first two non-empty lines of its final message start with `Goal:` and `Check:`
