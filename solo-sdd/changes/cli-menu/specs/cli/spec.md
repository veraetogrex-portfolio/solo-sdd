## MODIFIED Requirements

### Requirement: Entry point
The `solo_sdd` package SHALL run as `solo-sdd` (the `pyproject.toml` entry point) and as `python3 -m solo_sdd` on Python 3.9+ without third-party dependencies. The data (`skills/`, `global/`, `schema/`, `templates/`, `targets.json`, `ALGORITHM.md`) SHALL be found both from an installed wheel and from a repository clone. With an unknown command, or without a command when stdin or stdout is not a terminal, the command list is printed and code 2 returned.

#### Scenario: Version
- **WHEN** `solo-sdd --version` runs
- **THEN** it prints the version from `solo_sdd.__version__`

#### Scenario: From a wheel
- **WHEN** the package is installed with `pip install .` into a temporary environment, and the clone is deleted after that
- **THEN** `solo-sdd status` prints the state of all copies from `targets.json`

#### Scenario: From a clone
- **WHEN** `python3 -m solo_sdd status` is run in a clone
- **THEN** the output after the first line `source: …` matches the output of `python3 sync.py status`

#### Scenario: Bare without a terminal
- **WHEN** `solo-sdd < /dev/null` runs
- **THEN** the command list is printed and the exit code is 2

## ADDED Requirements

### Requirement: Home menu
Bare `solo-sdd` with a terminal on stdin and stdout SHALL open a full-screen menu whose header names the folder, the version, the project mode and the count of open changes, with entries for project settings, integrations and checklists, machine, changes (read-only), doctor, the command list and quit. A folder without `solo-sdd/` SHALL get an entry that runs the questions of `solo-sdd init` and returns to the menu; a folder with only `openspec/` SHALL show the import hint and write nothing.

#### Scenario: In a project
- **WHEN** `solo-sdd` runs on a terminal in a project with two open changes
- **THEN** the header shows the mode and `2 open changes`, and Project settings opens the settings screen

#### Scenario: Prepare a folder
- **WHEN** `solo-sdd` runs on a terminal in a git repository without `solo-sdd/` and the person picks Prepare this folder and accepts every proposal
- **THEN** `solo-sdd/config` exists as `solo-sdd init` writes it, and the menu shows the project entries

#### Scenario: Not a git repository
- **WHEN** the person picks Prepare this folder in a folder that is not a git repository
- **THEN** the menu shows the `solo-sdd init` refusal `not a git repository: git init`, no file is written, the menu stays

#### Scenario: An openspec project
- **WHEN** the folder has `openspec/` and no `solo-sdd/`
- **THEN** the menu shows `solo-sdd import openspec` as the next step and no file is written
