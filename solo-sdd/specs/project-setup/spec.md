# project-setup Specification

## Purpose
Makes `solo-sdd init` adapt to the project: it detects how the project is run, proposes settings from that, lets the user choose and records the choice with its reasons.

## Requirements

### Requirement: Project detection
`solo-sdd init` SHALL detect the installed agents known to the provider registry, the git remote, protection of the default branch through `gh` (`unknown` without `gh` or access), the distinct commit authors of the last 90 days and a `CODEOWNERS` file (at the root, in `.github/` or `docs/`). Authors SHALL be counted by distinct author email. Detection SHALL only read, SHALL call no external program besides `git` and `gh`, each with a timeout, and SHALL NOT fail `init`.

#### Scenario: No gh
- **WHEN** the project has a remote and `gh` is not installed
- **THEN** branch protection is `unknown`, `init` goes on

#### Scenario: Authors
- **WHEN** the last 90 days have commits by 3 distinct authors
- **THEN** the detection reports 3 authors

### Requirement: Proposed settings
`init` SHALL propose `mode: team` when there are 2 or more authors, a `CODEOWNERS` file or a protected default branch, otherwise `solo`; the detected agents as `agents`; `delivery.mode: pr` when there is a remote and CI, otherwise `local`. Each proposal SHALL be written to `solo-sdd/config` with a comment naming the fact behind it.

#### Scenario: A team repository
- **WHEN** the project has 3 authors and a protected default branch
- **THEN** the config has `mode: team` with a comment naming 3 authors and the protection

#### Scenario: A solo folder
- **WHEN** one author and no remote
- **THEN** `mode: solo` and `delivery.mode: local`

#### Scenario: A remote with CI
- **WHEN** the project has a remote and `.github/workflows/test.yml`
- **THEN** `delivery.mode: pr` with a comment naming the remote and the workflow

#### Scenario: A remote without CI
- **WHEN** the project has a remote and no workflow file
- **THEN** `delivery.mode: local` with a comment naming the remote without CI, and `init` prints that `pr` needs a CI workflow

#### Scenario: pr chosen without CI
- **WHEN** the project has a remote, no workflow file, and `init --delivery pr` runs
- **THEN** the config has `delivery.mode: pr`, and `init` prints that `pr` needs a CI workflow

### Requirement: Questions and flags
On a terminal `init` SHALL ask for mode, agents and delivery with the proposal preselected, Enter accepting it. Without a terminal or with `--yes` it SHALL take the proposals without questions. `--solo`, `--team`, `--agents`, `--delivery` and repeatable `--set key=value` SHALL override proposals; a wrong value SHALL be refused before any file is written.

#### Scenario: Non-interactive
- **WHEN** `solo-sdd init --team --agents claude --set dispatch.limit=3` runs with stdin closed
- **THEN** no question is printed, the config has the three values

#### Scenario: A project on openspec
- **WHEN** the folder has `openspec/` and no `solo-sdd/`
- **THEN** no question is asked, only the import hint is printed

#### Scenario: A wrong set
- **WHEN** `--set delivery.mode=cloud` is given
- **THEN** exit 1 with the allowed values, no file is created

### Requirement: Repeat and reconfigure
A repeated `init` SHALL keep an existing `solo-sdd/config` byte for byte. With flags and no `--reconfigure` it SHALL print that the file is kept and the flags are not applied. `init --reconfigure` SHALL ask the same questions and then every other registered key, each with the value in effect preselected, and change only the lines of keys whose answer differs from it.

#### Scenario: Repeat
- **WHEN** `init` runs in a project whose config has `mode: solo`
- **THEN** the config is unchanged

#### Scenario: Reconfigure
- **WHEN** `init --reconfigure` runs and the user changes only the mode to `team`
- **THEN** only the `mode` line changes

### Requirement: CI detection
`solo-sdd init` SHALL detect whether `.github/workflows/` holds a `*.yml` or `*.yaml` file directly in it, by reading the folder only; a missing or unreadable folder means no CI and SHALL NOT fail `init`.

#### Scenario: A workflow
- **WHEN** the project has `.github/workflows/test.yml`
- **THEN** the detection reports CI

#### Scenario: An empty folder
- **WHEN** `.github/workflows/` exists and holds only `README.md`
- **THEN** the detection reports no CI
