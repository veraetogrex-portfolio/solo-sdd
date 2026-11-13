# foreign-import Specification

## Purpose
Converts an existing `openspec/` process tree into `solo-sdd/`, so a project moves to solo-sdd without losing its specs, open changes and archive.

## Requirements

### Requirement: Import plan and write
`solo-sdd import openspec [folder]` SHALL print the conversion plan (the counts of specs, open and archived changes, and the files it would create) and change nothing; with `--write` it SHALL create `solo-sdd/` by that plan, `specs/` and `changes/` copied byte for byte without the `.openspec.yaml` files, and print the created paths. It SHALL NOT delete or change `openspec/`.

#### Scenario: Plan only
- **WHEN** `import openspec` runs in a project with 3 specs, 2 open and 5 archived changes
- **THEN** the plan names 3, 2 and 5, no file is created

#### Scenario: Write
- **WHEN** the same command runs with `--write`
- **THEN** `solo-sdd/` holds the 3 specs, 2 changes and 5 archived ones byte for byte, `openspec/` is unchanged, the last line names deleting `openspec/` as the next step after a check

### Requirement: Import project files
The import SHALL write `solo-sdd/project.md` from the `context` text of `openspec/config.yaml` with the lines `Language:` and `Mode:` taken from it when present, copy `openspec/analyze.md` to `solo-sdd/analyze.md`, add `Specs: none` under `## Capabilities` for a change whose `.openspec.yaml` has `skip_specs: true`, and keep `CLAIM` and `WAITING` files.

#### Scenario: Context and language
- **WHEN** `config.yaml` has a `context` block with `Language: en.` and `Mode: prod`
- **THEN** `project.md` holds the context text and the lines `Language: en` and `Mode: prod`

#### Scenario: A change without specs
- **WHEN** a change's `.openspec.yaml` has `skip_specs: true`
- **THEN** its imported `proposal.md` has `Specs: none` under `## Capabilities`

### Requirement: Import is idempotent and safe
A repeat of `import openspec --write` after a successful one SHALL change nothing and say so. If a non-empty `solo-sdd/` differs from the plan (a file changed, missing or extra), the import SHALL refuse with exit code 1 and name the first differing path. A folder without `openspec/` SHALL give `no openspec/ tree` and exit 1.

#### Scenario: Repeat
- **WHEN** `import openspec --write` runs twice
- **THEN** the second run prints `nothing to import`, no file changes

#### Scenario: Foreign content
- **WHEN** `solo-sdd/specs/cli/spec.md` exists and differs from `openspec/specs/cli/spec.md`
- **THEN** exit code 1, the message names that path, no file changes
