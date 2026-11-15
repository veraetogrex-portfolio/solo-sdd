## ADDED Requirements

### Requirement: Unknown arguments refused
`sync.py status` SHALL accept only `--quiet`; `push` only `--force`, `--quiet`, `--global-rules` and `--replace-foreign`; `pull` and `solo-sdd sync pull` only one name and `--from <place>`. `--help` or `-h`, alone or anywhere after one of these commands, SHALL print the usage, exit 0 and write nothing, also next to an unknown argument. Otherwise any other argument SHALL give `unknown argument <arg>`, the usage and exit 2 before the state is read or a file is written.

#### Scenario: Help on push
- **WHEN** `python3 sync.py push --help` runs on an empty temporary home
- **THEN** the usage is printed, the exit code is 0, and the home has no file

#### Scenario: Help next to an unknown argument
- **WHEN** `python3 sync.py push --bogus --help` runs on an empty temporary home
- **THEN** the usage is printed, the exit code is 0, and the home has no file

#### Scenario: An unknown option on push
- **WHEN** `python3 sync.py push --frobnicate` runs on an empty temporary home
- **THEN** the output starts with `unknown argument --frobnicate` and holds the usage, the exit code is 2, and the home has no file

#### Scenario: An unknown option before a broken state
- **WHEN** `state.json` holds `[]` and `python3 sync.py push --bogus` runs
- **THEN** the output starts with `unknown argument --bogus`, not `fail state:`, the exit code is 2, and the home is byte for byte the same

#### Scenario: An unknown option on pull
- **WHEN** a deployed copy of a skill was edited in place and `solo-sdd sync pull <skill> --bogus` runs
- **THEN** the exit code is 2, the repository source of the skill is byte for byte the same, and so is the home

#### Scenario: A prefix of a known option
- **WHEN** `python3 sync.py push --forc` or `push --force=yes` runs
- **THEN** it is refused as an unknown argument with exit 2 and no file written

## MODIFIED Requirements

### Requirement: Broken state refused
When `state.json` exists and cannot be read, does not parse or is not a JSON object, `status`, `install`, `update`, `uninstall`, `sync pull` and `doctor` SHALL exit 1 with `fail state: <path>: <reason>` and change no file. A missing `state.json` stays a fresh deployment. A run that requirement Unknown arguments refused refuses, or answers with the usage, ends by it before the state is read.

#### Scenario: A truncated state
- **WHEN** `state.json` holds `{"skills/ship/SKILL.md"` and `solo-sdd install` runs
- **THEN** exit 1 with `fail state:`, no copy and no backup is written

#### Scenario: Doctor on a broken state
- **WHEN** `state.json` holds `[]` and `solo-sdd doctor` runs
- **THEN** the output has `fail state:` and the exit code is 1

#### Scenario: Sync pull with an unknown argument on a broken state
- **WHEN** `state.json` holds `[]` and `solo-sdd sync pull ship --bogus` runs
- **THEN** the output starts with `unknown argument --bogus`, the exit code is 2, and no file changes
