## MODIFIED Requirements

### Requirement: Record reuse
A call whose tree, point, `--changed` flag, changed files and enabled descriptions (by digest) match a record SHALL print the recorded lines with `reused <hash>`, exit with the recorded code and start no command. A record holding a SKIP or a stopped run (a timeout or output over 1 MB) SHALL NOT be reused, and a record that is not readable JSON of the expected shape, or holds a line with a character integration output cannot hold, SHALL be ignored and the run repeated.

#### Scenario: Same tree reused
- **WHEN** `check --point checks` failed on a gate and nothing changed since
- **THEN** a second call prints the same lines and `reused <hash>`, exits 1, and the integration command is not started

#### Scenario: An edit makes a new record
- **WHEN** a file changes after a recorded run
- **THEN** the next call runs the integrations and writes a record under a new hash

#### Scenario: An owner description edited
- **WHEN** the tree is the same but the `command` of an enabled owner integration changed
- **THEN** the next call runs the integrations again

#### Scenario: A skipped tool installed later
- **WHEN** the record holds `SKIP marker-check: no-such-tool not found` and the tree is the same
- **THEN** the next call runs `marker-check` again

#### Scenario: An edit in the second of the index write
- **WHEN** a committed file is rewritten with the same size and a stat that matches its index entry, in the second the index was written (`core.checkStat minimal`, `core.trustctime false`)
- **THEN** the tree hash changes, and the next call runs the integrations and writes a record under a new hash
