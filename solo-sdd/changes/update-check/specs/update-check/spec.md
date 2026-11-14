## Purpose

Tells a person that a newer solo-sdd exists and updates it, with its layout and the current project's rules, from the home menu on their confirmation, without the network in ordinary commands and hooks.

## ADDED Requirements

### Requirement: Version check
The home menu, without delaying its drawing, and `doctor` SHALL ask the registry of the install method (npm for an npm install, PyPI otherwise) for the latest version at most once in 24 hours with a 2 second timeout, caching the answer and its time. A clone SHALL not be checked. Only a newer stable version SHALL be a notice; a failure SHALL show none in the menu and keep the cached answer.

#### Scenario: Newer on PyPI
- **WHEN** the package was installed by `uv tool install`, `0.2.0` runs and PyPI answers `0.3.0`
- **THEN** the menu header shows `0.3.0 available` and `doctor` prints `warn version:` with `uv tool upgrade solo-sdd`

#### Scenario: Fresh cache
- **WHEN** the cache holds an answer from 3 hours ago
- **THEN** no request is made and the cached answer is used

#### Scenario: Installed is newer
- **WHEN** `0.3.0` runs and the registry answers `0.2.0`
- **THEN** no notice, `doctor` prints `ok version:`

#### Scenario: Offline
- **WHEN** the request times out
- **THEN** the menu shows no notice and no error, `doctor` prints `ok version:` with the reason the latest is unknown

### Requirement: No network elsewhere
No command other than the home menu and `doctor`, and no hook, SHALL make the version request.

#### Scenario: Agent commands
- **WHEN** `solo-sdd list`, `validate`, `config get` or a hook runs with a stale cache
- **THEN** no request is made and the cache is unchanged

### Requirement: Registry answer checked
An answer over 1 MB, not JSON, of another shape or with a version not of the form `N.N.N` in ASCII digits SHALL count as no answer. No text from the answer except a checked version SHALL be shown or stored, and none SHALL enter a command.

#### Scenario: A hostile version
- **WHEN** the registry answers the version `0.3.0\u001b[2J; rm -rf ~`
- **THEN** no notice, nothing of it is shown or cached, no command is built from it

### Requirement: Update from the menu
The entry Update to `<version>` SHALL show the fixed upgrade command of the install method and the release notes link, and run nothing without confirmation. After confirmation it SHALL run the upgrade, then `solo-sdd install` of the upgraded program, then offer `solo-sdd init` in a project whose rules block `doctor` names as older, and ask to restart; a failed step SHALL stop the steps after it.

#### Scenario: Confirmed
- **WHEN** the person confirms the update to `0.3.0` of a uv install in a project with an older unedited rules block
- **THEN** `uv tool upgrade solo-sdd` runs, then `solo-sdd install` of `0.3.0`, then `solo-sdd init` after a second confirmation, and the menu asks to restart

#### Scenario: Upgrade fails
- **WHEN** the upgrade command exits non-zero
- **THEN** its output is shown and `solo-sdd install` does not run

#### Scenario: Cancelled
- **WHEN** the person cancels at the confirmation
- **THEN** no command runs

### Requirement: Skip and switch off
Skip this version SHALL hide the notice until a newer version is answered. `SOLO_SDD_NO_UPDATE_CHECK=1` or the update check switch of the Machine section SHALL stop every version request, the menu and `doctor` included.

#### Scenario: Skipped
- **WHEN** the person skips `0.3.0` and the registry still answers `0.3.0`
- **THEN** no notice; when it answers `0.3.1`, the notice shows `0.3.1`

#### Scenario: Switched off
- **WHEN** `SOLO_SDD_NO_UPDATE_CHECK=1` is set and the cache is stale
- **THEN** the menu and `doctor` make no request, and `doctor` prints `ok version:` naming the check as off
