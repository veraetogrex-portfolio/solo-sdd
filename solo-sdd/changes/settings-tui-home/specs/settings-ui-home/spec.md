## Purpose

The machine part of solo-sdd configuration on the settings screen: which agents get the skills, the hooks and the global rules, with the deployment state and the doctor warnings, changed through the same commands a person runs.

## ADDED Requirements

### Requirement: Machine section
The settings screen SHALL have a Machine section, also when opened outside a project, showing the chosen agents among the registered providers with the detected ones marked, whether the hooks and the global rules are on, the deployment source and version, the number of copies in each `status` state and every `warn` and `fail` line of `doctor`.

#### Scenario: A fresh home
- **WHEN** the home has a deployment for `claude` and `other` without hooks
- **THEN** the section shows `claude` and `other` ticked, hooks off, global rules off, and the `doctor` warning about the depth

#### Scenario: Outside a project
- **WHEN** the screen opens in a folder without `solo-sdd/`
- **THEN** only the Machine section is shown

### Requirement: Apply machine edits
Applying machine edits SHALL list the commands it will run and the folders they change, run them only after confirmation through the functions of `install` and `uninstall`, and show their output and exit codes. A refused command SHALL change no file. Cancelling SHALL run nothing.

#### Scenario: Narrow the agents
- **WHEN** `claude` and `codex` are chosen and the person unticks `codex` and confirms
- **THEN** the screen ran `solo-sdd install --agents claude,other`, the unchanged copies under `~/.codex` are gone, its output is shown

#### Scenario: Hooks off
- **WHEN** the hooks are on and the person turns them off and confirms
- **THEN** the screen ran `solo-sdd uninstall --hooks` and shows hooks off

#### Scenario: Hooks without Claude
- **WHEN** the person unticks `claude` while the hooks are on and confirms
- **THEN** the refusal naming that hooks need `claude` is shown and no file changes

#### Scenario: Cancelled
- **WHEN** the person sees the command list and cancels
- **THEN** no command runs
