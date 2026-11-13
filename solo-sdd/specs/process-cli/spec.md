# process-cli Specification

## Purpose
Lists, creates and archives changes in the `solo-sdd/` tree, so a project runs its whole change cycle with the solo-sdd package alone.

## Requirements

### Requirement: List changes and specs
`solo-sdd list` SHALL print one line per open change: the id, done and total tasks, and `CLAIM` or `WAITING` if the folder has that file. `--specs` SHALL print one line per main spec with its requirement count. `--json` SHALL print the same data as a list of objects. Archived changes SHALL NOT be listed.

#### Scenario: Two open changes
- **WHEN** the tree has `a` with 2 of 5 tasks done and a `CLAIM` file, and `b` with 0 of 3
- **THEN** two lines: `a 2/5 CLAIM` and `b 0/3`

#### Scenario: Specs
- **WHEN** `solo-sdd list --specs` runs on a tree with the spec `cli` of 3 requirements
- **THEN** the line `cli 3`

### Requirement: New change
`solo-sdd new <id>` SHALL create `solo-sdd/changes/<id>/` with `proposal.md`, `verification.md` and `tasks.md` from the package templates and print their paths. It SHALL refuse with exit code 1 and change nothing if the id is not kebab-case or a change or archived change with this id exists.

#### Scenario: A new id
- **WHEN** `solo-sdd new add-export` runs in a tree without that change
- **THEN** the folder holds the three files with the template sections, exit code 0

#### Scenario: An existing id
- **WHEN** `solo-sdd/changes/archive/2026-11-01-add-export/` exists
- **THEN** exit code 1, the message names the archived change, no folder is created

### Requirement: Archive applies deltas
`solo-sdd archive <id>` SHALL apply each delta to its main spec: `ADDED` appends, `MODIFIED` replaces the block with the same name, `REMOVED` deletes it, `RENAMED` changes its name; a new capability gets a main spec from the delta's `## Purpose` and requirements. Then the folder SHALL move to `changes/archive/YYYY-MM-DD-<id>/`.

#### Scenario: Modified requirement
- **WHEN** a delta has `## MODIFIED Requirements` with `### Requirement: Export` and new text
- **THEN** the main spec holds the new block in place of the old one, once

#### Scenario: A change without deltas
- **WHEN** the change's proposal has `Specs: none` and no `specs/` folder
- **THEN** no main spec changes, the folder moves to the archive

#### Scenario: New capability
- **WHEN** the delta's capability has no main spec
- **THEN** `solo-sdd/specs/<capability>/spec.md` is created with the `## Purpose` text and the requirements

### Requirement: Archive is atomic
`solo-sdd archive` SHALL change no file if the change fails `validate`, a `MODIFIED`, `REMOVED` or `RENAMED` name is not in the main spec, an `ADDED` name already is, or the archive folder exists. Without `--yes` on a terminal it SHALL show the spec files to change and ask; without a terminal and without `--yes` it SHALL refuse.

#### Scenario: Unknown modified name
- **WHEN** a delta modifies `### Requirement: Missing`, which the main spec does not have
- **THEN** exit code 1, the message names the file and `Missing`, the main specs and the change folder are byte for byte the same

#### Scenario: No terminal
- **WHEN** `solo-sdd archive demo` runs with stdin closed and without `--yes`
- **THEN** exit code 1 with the hint `--yes`, no file changes

### Requirement: Archive refuses unfinished work
`solo-sdd archive` SHALL change no file and exit 1 when `tasks.md` has an unticked `- [ ]` task above its last task group, or `## Result` of `verification.md` has no text outside comments; the message SHALL name each open task and the empty section. With `--force` it SHALL skip only this check, archive and print `forced: <what was open>`; the other refusals of Archive is atomic stay.

#### Scenario: Open implementation tasks
- **WHEN** `tasks.md` has `- [ ] 1.2 …` in `## 1. Implementation` and `solo-sdd archive demo --yes` runs
- **THEN** exit 1, the message names `1.2`, the main specs and the change folder are byte for byte the same

#### Scenario: The acceptance group
- **WHEN** every task before `## 2. Acceptance` is ticked, `2.2` (the archive itself) is not, and `## Result` has text
- **THEN** the archive goes on

#### Scenario: An empty result
- **WHEN** `## Result` holds only the template comment
- **THEN** exit 1, the message names `Result`

#### Scenario: Forced
- **WHEN** the same change is archived with `--yes --force`
- **THEN** the archive is done and the output has `forced:` with `1.2`

### Requirement: Archive names sibling deltas
After a successful archive, `solo-sdd archive` SHALL print one line `sibling: <change> <section> <requirement>` for each other open change whose delta has a MODIFIED, REMOVED or RENAMED block of a requirement this archive added, modified, removed or renamed in the same capability.

#### Scenario: Two changes on one requirement
- **WHEN** `chars-bytes` modifies "Character count command" and the open `chars-empty` modifies it too
- **THEN** archiving `chars-bytes` prints `sibling: chars-empty MODIFIED Character count command`

#### Scenario: A removed requirement
- **WHEN** `drop-bytes` removes "Byte mode" and the open `bytes-fix` modifies it
- **THEN** archiving `drop-bytes` prints `sibling: bytes-fix MODIFIED Byte mode`

#### Scenario: No sibling
- **WHEN** no open change touches the archived requirements
- **THEN** no `sibling:` line is printed
