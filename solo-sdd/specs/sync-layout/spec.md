# sync-layout Specification

## Purpose
Deploying solo-sdd into the agent folders loses no version of a file it overwrites.

## Requirements

### Requirement: Backup never overwritten
Every `sync.py push` run that overwrites at least one existing copy SHALL save the previous texts into its own new folder `~/.local/share/solo-sdd/backup/<YYYYMMDD-HHMMSS>-<pid>-<n>/`. A backup SHALL match the previous file byte for byte. Writing a backup SHALL NOT replace an existing file. For any sequence of `push` runs and copy edits between them, every text replaced by one of the last 20 runs that wrote a backup SHALL lie in at least one kept backup.

#### Scenario: Two deployments in one second
- **WHEN** `push` replaced a foreign `~/.claude/CLAUDE.md` with the text `ORIGINAL`, the file was edited again to `EDIT2`, and `push --force` ran in the same second
- **THEN** `backup/` has two folders, one with `ORIGINAL`, the other with `EDIT2`

#### Scenario: The backup path is taken
- **WHEN** two copies from `targets.json` give the same path inside the backup folder, and `push` overwrites both
- **THEN** the first is saved and replaced, the second is untouched, an output line names it with the reason `backup already exists`, the backup file stayed the same, exit code 1

#### Scenario: A deployment without overwriting
- **WHEN** `push` only creates missing copies
- **THEN** no new folder is created in `backup/`

#### Scenario: A new backup folder
- **WHEN** `push` creates a backup folder
- **THEN** the folder is created atomically and matches no existing one

#### Scenario: The path is taken
- **WHEN** a backup path is taken
- **THEN** the destination copy is not overwritten, an output line names it with the reason `backup already exists`, the run ends with code 1

#### Scenario: A rules file turned into a block
- **WHEN** `push` turns a rules file into a managed block with the same text
- **THEN** no backup is needed: the text stayed in the file

### Requirement: State written atomically
`state.json` SHALL be written to a new file in the same folder and moved into place with an atomic replace; a run stopped at any point SHALL leave either the old or the new file whole.

#### Scenario: A stopped write
- **WHEN** the write is interrupted after the temporary file is written and before the replace
- **THEN** `state.json` holds the old text and parses

### Requirement: Broken state refused
When `state.json` exists and cannot be read, does not parse or is not a JSON object, `status`, `install`, `update`, `uninstall`, `sync pull` and `doctor` SHALL exit 1 with `fail state: <path>: <reason>` and change no file. A missing `state.json` stays a fresh deployment.

#### Scenario: A truncated state
- **WHEN** `state.json` holds `{"skills/ship/SKILL.md"` and `solo-sdd install` runs
- **THEN** exit 1 with `fail state:`, no copy and no backup is written

#### Scenario: Doctor on a broken state
- **WHEN** `state.json` holds `[]` and `solo-sdd doctor` runs
- **THEN** the output has `fail state:` and the exit code is 1

### Requirement: Foreign copy kept
`install`, `update` and `push` SHALL NOT overwrite a whole-file target that has no state entry and differs from its source: they SHALL print `foreign <path>: kept (install --replace-foreign replaces it)`, lay out the rest and exit 1. With `--replace-foreign` such a file SHALL be backed up and replaced. A target equal to its source SHALL be adopted as `ok`. A rules file laid out as a block keeps its text and gets the block as before.

#### Scenario: A foreign skill
- **WHEN** `~/.claude/skills/ship/SKILL.md` was written by another tool and `solo-sdd install` runs
- **THEN** the file is byte for byte the same, the output has `foreign`, the exit code is 1, the other copies are laid out

#### Scenario: Replaced on request
- **WHEN** the same with `install --replace-foreign`
- **THEN** the file is replaced and its previous text is in a backup folder

#### Scenario: A foreign rules file
- **WHEN** `~/.claude/CLAUDE.md` holds the owner's text, has no state entry, and `solo-sdd install` runs with the global rules chosen
- **THEN** the owner's text stays in the file with the block added, no `foreign` line for it

### Requirement: Backup retention
After writing its backup folder, a run SHALL keep the 20 newest run folders in `~/.local/share/solo-sdd/backup/` by the time in their names, then by modification time, delete the older ones and print `pruned backups: <n>` when it deleted any. A run folder name is `<YYYYMMDD-HHMMSS>-<pid>-<n>` or the `<YYYYMMDD-HHMMSS>` an earlier version wrote. The current run's folder SHALL never be deleted. An entry whose name is not a run folder name SHALL be neither counted nor deleted.

#### Scenario: Many backups
- **WHEN** the backup folder holds 25 folders and a push writes one more
- **THEN** 20 folders are left, the current run's among them, the output has `pruned backups: 6`

#### Scenario: A foreign entry
- **WHEN** the backup folder holds 21 run folders and a folder `mine`, and a push writes one more
- **THEN** `mine` stays, 20 run folders are left, the output has `pruned backups: 2`

#### Scenario: Folders of an earlier version
- **WHEN** the backup folder holds 21 folders named `<YYYYMMDD-HHMMSS>` and a push writes one more
- **THEN** the two oldest of them are deleted and the output has `pruned backups: 2`

#### Scenario: A run without a backup
- **WHEN** the backup folder holds 25 run folders and a push overwrites nothing
- **THEN** all 25 stay and there is no `pruned backups` line
