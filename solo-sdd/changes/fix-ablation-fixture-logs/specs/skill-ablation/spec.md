## ADDED Requirements

### Requirement: Fixture files tracked by git
The task set test SHALL report `task set <skill>/<task>: fixture file not tracked by git: <path>` for every file under a task's `fixture/` that `git ls-files -z` (the index) does not list, the path relative to `fixture/`, names compared in Unicode NFC. A root outside git, or a failed git call, SHALL add one line naming the root and the reason, never an empty answer. `.gitignore` SHALL re-include only `*.log` under a stand's `fixture/`, every other ignore rule applying there.

#### Scenario: A fixture file git does not track
- **GIVEN** a task's `fixture/logs/transform.log` that `.gitignore` ignores, so `git ls-files` does not list it
- **WHEN** the task set test runs
- **THEN** it fails with `task set <skill>/<task>: fixture file not tracked by git: logs/transform.log`

#### Scenario: Quoted and decomposed names
- **GIVEN** tracked fixture files `logs/a b.log` and `notes/ä.txt` written with a decomposed `ä`, and an untracked `notes/ö.txt`
- **WHEN** the task set test runs
- **THEN** it reports only `notes/ö.txt`

#### Scenario: A root outside git
- **WHEN** `task_errors` runs on a folder that is not a git work tree
- **THEN** its lines hold `task sets: <root>: not a git work tree`, no `fixture file not tracked` line, and the other task set errors as before

#### Scenario: A secret under a fixture stays ignored
- **GIVEN** the repository's `.gitignore`
- **WHEN** `git check-ignore` asks about `tests/stands/x/fixture/.env`, `tests/stands/x/fixture/logs/.env.prod.log`, `tests/stands/x/fixture/.DS_Store` and `tests/stands/x/fixture/logs/a.log`
- **THEN** the first three are ignored and `logs/a.log` is not
