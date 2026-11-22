## Purpose

Tries a failed copy into `backups/` again, up to a limit the person can set.

## ADDED Requirements

### Requirement: Retry a failed copy
When a copy fails, `backup.py` SHALL try it again until it succeeds or the tries reach the retry limit, the setting `process.retry-max` of `backup.json`. A copy that succeeds SHALL print `copied <file>, tries: <n>`; when every try fails it SHALL print `gave up on <file>, tries: <n>` to stderr and exit with code 1.

#### Scenario: The second try works
- **WHEN** the first copy of `notes.txt` fails and the second works
- **THEN** it prints `copied notes.txt, tries: 2` and exits with code 0

#### Scenario: A limit the person set
- **WHEN** `backup.json` holds `{"process.retry-max": 2}` and every copy fails
- **THEN** it prints `gave up on notes.txt, tries: 2` and exits with code 1

### Requirement: Default retry limit
Without `process.retry-max` in `backup.json`, or without `backup.json`, the retry limit SHALL be `3`.

#### Scenario: No settings file
- **WHEN** there is no `backup.json` and every copy fails
- **THEN** it prints `gave up on notes.txt, tries: 3` and exits with code 1
