# repo-language Specification

## Purpose
The contract words of solo-sdd are English: the AGENTS.md headings and items that scripts read, the lines they print for skills and tests and the role tags; a project with the old Russian words is told how to migrate instead of being ignored silently, and the reply language is checked only when the owner asks for it.

## Requirements

### Requirement: English keyword set
Scripts that read a project's `AGENTS.md` SHALL recognise only the English headings and items listed in scenario «Mapping». Lines that scripts print for skills or tests SHALL use the English words of the same list.

#### Scenario: Mapping
- **WHEN** a script reads or prints a keyword
- **THEN** it uses only: sections `## Working copy`, `## Delivery`, `## Commands`; items `Paths:`, `Prepare:`, `After refresh:`, `Shared:`, `Orchestrators:`, `Orchestrator: solo`, `Mode:`, `Merge:`, `PR title:`, `Deploy:`, `Owner only:`, `Loopback: needed`; the commands table row `Tests`; plan lines `limit:`, `loopback:`, `launch:`, `waiting:`, `together:`; role tags `Review:`, `Implement:`, `Lookup:`; the report field `Needs from you` read by `sdd-eval.py`

#### Scenario: English section is read
- **WHEN** `AGENTS.md` has `## Working copy` with `- Orchestrators: 3`
- **THEN** `sdd-dispatch-plan.py` prints `limit: 3` on its first line

#### Scenario: Plan output words
- **WHEN** a change waits because of the limit
- **THEN** the plan prints a `waiting:` line with the reason `limit`, and no Cyrillic letter

### Requirement: Old keywords are named, not ignored silently
When a script or `solo-sdd doctor` finds a pre-English heading or item from the migration table in `AGENTS.md`, it SHALL print one line naming the file and the command `solo-sdd migrate-agents`. The old item SHALL NOT take effect.

#### Scenario: Old project
- **WHEN** `AGENTS.md` has the pre-English Working copy heading with the pre-English orchestrator limit item set to 3
- **THEN** the plan uses the default limit 2 and prints a line with the path of `AGENTS.md` and `solo-sdd migrate-agents`

#### Scenario: Old owner-only item
- **WHEN** `AGENTS.md` of the main folder has the pre-English owner-only item and a branch is merged by `sdd-pr.py` or `sdd-dispatch.py land-local`
- **THEN** its paths are not read, and the merge waits for the owner (code 8) with `AGENTS.md (pre-English «Owner only:» item: run solo-sdd migrate-agents)`

#### Scenario: Doctor
- **WHEN** `solo-sdd doctor` runs in such a project
- **THEN** a `warn agents:` line names the old keywords found by their English names and the migrate command

### Requirement: AGENTS.md migration
`solo-sdd migrate-agents [folder]` SHALL print a unified diff that renames the pre-English headings and items of the migration table in `<folder>/AGENTS.md` to English and SHALL change the file only with `--write`. Other text SHALL stay byte for byte. A second run SHALL report no changes.

#### Scenario: Dry run and write
- **WHEN** the owner runs `solo-sdd migrate-agents .` and then `solo-sdd migrate-agents . --write`
- **THEN** the first run prints the diff and leaves the file; the second rewrites only the mapped headings and items

#### Scenario: Idempotent
- **WHEN** `migrate-agents --write` runs on an already migrated file
- **THEN** it prints that nothing changed and the file is unchanged

#### Scenario: Table without Cyrillic in the repository
- **WHEN** the migration table is read in the source
- **THEN** its old keywords are `\u` escapes, and the source file contains no Cyrillic letter

### Requirement: Reply language check
The Stop hook SHALL check the language of the final reply only when `SOLO_SDD_REPLY_LANG` is `ru` or `en`: `ru` rejects a reply with a Cyrillic share under 0.3, `en` rejects a reply with a Latin share under 0.7, both over at least 80 letters outside code. Unset or any other value SHALL mean no check.

#### Scenario: Not set
- **WHEN** `SOLO_SDD_REPLY_LANG` is unset and the reply is in English
- **THEN** the hook does not block the stop

#### Scenario: Owner wants Russian replies
- **WHEN** `SOLO_SDD_REPLY_LANG=ru` and the reply is in English
- **THEN** the hook asks to rewrite the reply in Russian, as before this change

### Requirement: No Cyrillic in the repository
No tracked file SHALL contain a Cyrillic letter (U+0400–U+04FF), with no exceptions. `tests/test_repo_language.py` SHALL fail and name every file and line that does. Data that tests Unicode handling SHALL use non-Cyrillic non-ASCII text.

#### Scenario: New Russian line
- **WHEN** a commit adds a Russian sentence to `skills/spec-next/SKILL.md`
- **THEN** `tests/test_repo_language.py` fails and names the file and line

#### Scenario: Archive and vendor are covered
- **WHEN** a file under `solo-sdd/changes/archive/` or `vendor/` holds a Cyrillic letter
- **THEN** the test fails the same way

#### Scenario: Escapes are not letters
- **WHEN** the migration table of `english-keywords` holds the old keywords as `\u` escapes
- **THEN** the test passes
