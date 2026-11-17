## ADDED Requirements

### Requirement: Project rules in config
`project.stage` (`demo`, `prod`; empty: decided by the task), `artifacts.language` (2 or 3 lowercase ASCII letters; `en`), `lessons.write` (`on`, `off`; `on`) and `lessons.max-lines` (20) SHALL be read by the global rules, `project-init` and `spec-plan`; 20 lines in other requirements name the last default. `spec-plan` SHALL write the artifacts' prose in `artifacts.language`. The global rules SHALL let an agent change the four keys only on the owner's words.

#### Scenario: A bad language code
- **WHEN** `config set artifacts.language "Russian language"` runs
- **THEN** exit 1 names 2 or 3 lowercase letters, the file is unchanged

#### Scenario: Artifacts in Russian
- **WHEN** the file has `artifacts.language: ru`
- **THEN** the laid-out `spec-plan` text writes the prose of the artifacts in that language, and keeps their headings, `SHALL`, `WHEN`, `THEN`, keys and paths in English, as `validate` reads them

#### Scenario: Lessons switched off
- **WHEN** the file has `lessons.write: off`
- **THEN** the laid-out global rules send a lesson to the report as `Lesson (not written): <sentence>` for this setting

### Requirement: Project lines as the old source
Without a file value `project.stage` and `artifacts.language` SHALL take the `Mode:` and `Language:` lines of `solo-sdd/project.md`, a final dot dropped, source `project.md`; a line value outside the allowed ones SHALL be left out, and `config get`, `list` and `describe` SHALL name it on stderr. A file value SHALL win over the line, and the global rules SHALL say so; `config set` SHALL leave `project.md` unchanged.

#### Scenario: The old line
- **WHEN** there is no file value and `solo-sdd/project.md` has `Mode: demo`
- **THEN** `config get project.stage` prints `demo` with `source: project.md`

#### Scenario: The file wins
- **WHEN** `solo-sdd/project.md` has `Mode: demo`, and `config set project.stage prod` runs
- **THEN** `config get project.stage` prints `prod` with `source: file`, `project.md` keeps its bytes

#### Scenario: A line value outside the list
- **WHEN** there is no file value and `solo-sdd/project.md` has `Mode: staging`
- **THEN** `config get project.stage` prints an empty line with `source: default`, and stderr names `Mode: staging`

## MODIFIED Requirements

### Requirement: Config command
`solo-sdd config list` SHALL print every key, its value in effect and its source (`file`, `AGENTS.md`, `project.md`, `mode`, `default`). `get <key>` SHALL print the value on stdout and `source: <source>` on stderr. `set <key> <value>` and `unset <key>` SHALL change only that line and keep comments and order. A wrong key or value SHALL be refused with exit 1 and the allowed keys or values.

#### Scenario: Set keeps the rest
- **WHEN** the file has a comment line and two keys, and `config set dispatch.limit 3` runs
- **THEN** only the `dispatch.limit` line changes; the comment and the other key keep their bytes

#### Scenario: A wrong value
- **WHEN** `config set delivery.mode cloud` runs
- **THEN** exit 1, the message lists `local, pr`, the file is unchanged

#### Scenario: Get names the source
- **WHEN** there is no `solo-sdd/config`, and `AGENTS.md` has `## Delivery` with `- Mode: pr`
- **THEN** `config get delivery.mode` prints `pr` on stdout and `source: AGENTS.md` on stderr
