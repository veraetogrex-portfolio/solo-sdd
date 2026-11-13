# shared-blocks Specification

## Purpose
Keeps the copies of code blocks that single-file scripts share equal to one source file, rewritten by one script instead of by hand.

## Requirements

### Requirement: Block copies from one source
`scripts/sync_blocks.py` SHALL copy the text between `# <name>:begin` and `# <name>:end` from its source into every other `.py` file under `solo_sdd/` and `global/` with those markers. Sources: `settings` `solo_sdd/settings.py`, `keywords` `solo_sdd/keywords.py`, `doc-reader` `solo_sdd/process_format.py`, `errors` `solo_sdd/doctor.py`, `shell` and `process-root` `global/work_hooks.py`. With `--check` it SHALL write nothing, print each differing copy with its block and exit 1 if any.

#### Scenario: An edit in the source
- **WHEN** the settings block of `solo_sdd/settings.py` gets a new key and the script runs
- **THEN** the four other copies hold the same text, nothing outside the markers changed

#### Scenario: A stale copy
- **WHEN** `global/sdd_pr.py` has an older settings block and `--check` runs
- **THEN** exit 1, the output names `global/sdd_pr.py` and `settings`, no file changed

#### Scenario: Idempotent
- **WHEN** the script runs twice
- **THEN** the second run changes no file

### Requirement: Broken markers refused
When a scanned file has a `begin` marker without its `end`, an `end` without its `begin`, the same block twice, or a block name with no source, `scripts/sync_blocks.py` SHALL write no file, with or without `--check`, print the file and the block name and exit 1.

#### Scenario: A missing end marker
- **WHEN** `global/sdd_pr.py` has `# settings:begin` and no `# settings:end`, and the script runs
- **THEN** exit 1, the output names `global/sdd_pr.py` and `settings`, no file changed

### Requirement: Tests use the block check
The tests that compare block copies SHALL run `scripts/sync_blocks.py --check` and fail on its exit code 1.

#### Scenario: A copy left behind
- **WHEN** a commit edits the shell block only in `global/process-guard.py`
- **THEN** the test run fails naming `global/process-guard.py` and `shell`
