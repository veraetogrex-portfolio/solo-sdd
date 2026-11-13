# orchestrator-status Specification

## Purpose
One format in which an orchestrator subagent hands a change back to the dispatcher, and a check of this status against git and files before the dispatcher gets it.

## Requirements

### Requirement: Status block format
An orchestrator status SHALL be a block of lines `FIELD: value` with the fields `STATUS`, `CHANGE`, `BRANCH`, `WORKTREE`, `COMMIT`, `ARCHIVE`, `VALIDATE`, `TESTS`, `LIVE`, `REVIEW`, `AGENTS`, `HOOKS`, `NOT_VERIFIED`, `NOTES`. `STATUS` takes one of the values `archived`, `not_ready`, `blocked`. A status block is a message with a line starting with `STATUS:` (spaces before the word and a code block around it are allowed). If a field line repeats, the first occurrence counts.

#### Scenario: A message without a status
- **WHEN** a subagent hands back a message without a `STATUS:` line (an executor report, a review)
- **THEN** the message does not count as a status and is not checked

#### Scenario: An unknown STATUS value
- **WHEN** the block has `STATUS: done`
- **THEN** the check refuses and names the allowed values

### Requirement: Archived status evidence
For `STATUS: archived` the check SHALL confirm by git and files, without running tests and validation, that all format fields are present and not empty, and the other fields are right by the requirements Archived status worktree evidence, Archived status archive evidence and Archived status exit codes. On any mismatch the check SHALL refuse and list all found mismatches in one message, adding that if they cannot be removed, `STATUS: not_ready` with the reason must be handed back.

#### Scenario: A complete and right status
- **WHEN** an orchestrator hands back `STATUS: archived`, and the commit, the archive and the removed CLAIM match the fields
- **THEN** the handback passes without a refusal

#### Scenario: The commit is not the last one
- **WHEN** `COMMIT` points to a commit after which the branch has more commits, or to a missing one
- **THEN** the check refuses and names the actual `HEAD` of the `WORKTREE` folder

#### Scenario: The change is not archived and CLAIM is not removed
- **WHEN** `solo-sdd/changes/<CHANGE>` remained in `WORKTREE`, and the main folder holds its `CLAIM`
- **THEN** one refusal lists both mismatches

#### Scenario: An exit code with a note
- **WHEN** `TESTS: npm test -> exit 0 (250 files, 5455 tests)`
- **THEN** the field is accepted

#### Scenario: A note does not hide a failure
- **WHEN** `TESTS: npm test -> exit 1 (then exit 0 on retry)`
- **THEN** the check refuses: the exit code after ` -> ` is not 0

#### Scenario: Several commands in a field
- **WHEN** `TESTS: npm test -> exit 0 (245 files; npm run typecheck -> exit 0)`
- **THEN** the field is accepted; with `npm test -> exit 0; npm run typecheck -> exit 2` the check refuses

### Requirement: Not-ready status
For `STATUS: not_ready` and `STATUS: blocked` the check SHALL require only non-empty `CHANGE` and `NOTES` (what is in the way) and not check the commit, the archive and CLAIM.

#### Scenario: An honest "not ready"
- **WHEN** an orchestrator hands back `STATUS: not_ready` with `CHANGE` and a reason in `NOTES`
- **THEN** the handback passes without a refusal

### Requirement: Repeatable LIVE command
For `STATUS: archived` the check SHALL refuse if the `LIVE` command (the text before the first arrow `->`, as in the `exit` code check) holds, outside quotes and without `\` escaping, a separator `&&`, `||`, `;` or a pipe `|`, or starts with `cd `. The refusal names the `LIVE` field and the sign and adds that a multi-step scenario becomes a stand whose call goes into `LIVE`; the dispatcher shortens the output. Environment variables before the command and signs inside quotes are allowed.

#### Scenario: A command chain
- **WHEN** an orchestrator hands back `LIVE: npm run build && node scenarios/docs/check.ts -> 48 checks passed`
- **THEN** the handback is refused, the mismatch names `LIVE` and `&&`

#### Scenario: A pipe
- **WHEN** `LIVE: node packages/core/scenarios/ocr/check.ts | tail -1 -> 25 of 25`
- **THEN** the handback is refused, the mismatch names `LIVE` and `|`: a pipe is a second command, the dispatcher shortens the stand output

#### Scenario: A stand call
- **WHEN** `LIVE: COUNCIL_DEV=1 node packages/core/scenarios/ocr/check.ts -> 25 of 25`
- **THEN** the `LIVE` field gives no mismatches

#### Scenario: A sign in quotes
- **WHEN** `LIVE: node check.ts --title "a; b | c" -> ok`
- **THEN** the `LIVE` field gives no mismatches

### Requirement: Archived status worktree evidence
For `STATUS: archived` the check SHALL require: `WORKTREE` is the root of a git working copy (the folder exists and has `.git`), and if the field is empty, the other checks run at the git repository root of the hook's `cwd`; `COMMIT` is the last commit (`HEAD`) of this folder, at least 7 hex characters, and matches the start of the full `HEAD` hash.

#### Scenario: An empty WORKTREE
- **WHEN** the `WORKTREE` field is empty
- **THEN** the refusal names the empty field, and the other checks run at the git repository root of the hook's `cwd`

#### Scenario: A short hash
- **WHEN** `COMMIT` is shorter than 7 hex characters
- **THEN** the check refuses

### Requirement: Archived status exit codes
In the `VALIDATE` and `TESTS` values of an `archived` status, after the first ` -> ` (without ` -> `, at the start of the value) there SHALL be `exit 0`, followed by the line end, a space, `;`, `,` or `)`, and after the first ` -> ` there SHALL NOT be `exit` with another code (`-> exit 2`, `-> exit: 1`, `build -> failed (exit 1)`); notes and other commands after the code are allowed (`-> exit 0 (250 files); npm run typecheck -> exit 0`); `exit 01`, `exit 0x`, `exit 0(x)` SHALL NOT be accepted.

#### Scenario: A code without an arrow
- **WHEN** `VALIDATE: exit 0`
- **THEN** the field is accepted: without ` -> ` the code is looked for at the start of the value

#### Scenario: Codes that look like zero
- **WHEN** after ` -> ` there is `exit 01`, `exit 0x` or `exit 0(x)`
- **THEN** the field is not accepted

#### Scenario: Another code in another entry
- **WHEN** `TESTS: build -> failed (exit 1)` or `VALIDATE: solo-sdd validate -> exit: 1`
- **THEN** the check refuses

### Requirement: Archived status archive evidence
For `STATUS: archived` the check SHALL require: the `ARCHIVE` folder (a path relative to `WORKTREE` or absolute) exists inside `solo-sdd/changes/archive/` of this folder, and `solo-sdd/changes/<CHANGE>` is absent there; the main project folder (the shared `.git` of `WORKTREE`) has no file `solo-sdd/changes/<CHANGE>/CLAIM`.

#### Scenario: The archive path
- **WHEN** `ARCHIVE` is given as a path relative to `WORKTREE` or as an absolute path
- **THEN** both kinds are accepted

#### Scenario: An archive outside the archive folder
- **WHEN** the `ARCHIVE` folder lies outside `solo-sdd/changes/archive/` of the `WORKTREE` folder
- **THEN** the check refuses
