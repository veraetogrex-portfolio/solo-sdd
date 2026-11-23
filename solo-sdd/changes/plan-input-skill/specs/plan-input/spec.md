## Purpose
The owner's decisions from a review, a research or a discussion reach `/spec-plan` as one self-contained input file per target repository, checked against that repository, with the steps that start it in the right folder.

## ADDED Requirements

### Requirement: Only decided items in the input
`plan-input` SHALL write one Markdown input per target repository in which an item goes into a letter section (`A`, `B`, ...) only with the owner's decision quoted with its date, holding `Facts`, `Where`, `What` and `Check`; an item without a decision SHALL go under `Not decided`, one line each.

#### Scenario: An undecided item
- **WHEN** the skill runs on a review with two clean items the owner decided and one the owner left open
- **THEN** the input has letter sections for the two decided items with the quoted decisions and dates, and the open item is one line under `Not decided`

### Requirement: One section per item
Every item SHALL stand under exactly one section, the first that applies in the order `Already done`, `Already planned`, `Not checked`, `Not decided`, a letter section.

#### Scenario: Done with its file gone
- **WHEN** a decided item names a file that a commit of the target repository deleted while closing the item
- **THEN** the item is under `Already done` only, not under `Not checked`

### Requirement: Only letter sections planned
The input SHALL say, in a line before its first letter section, that only the letter sections are planned and that `Already done`, `Already planned`, `Not checked` and `Not decided` are for the owner; the skill's reply SHALL count the items of each of those sections.

#### Scenario: The plan line
- **WHEN** the skill writes an input that has a `Not decided` item
- **THEN** a line before section `A` says only the letter sections are planned, and the reply counts one item not decided

### Requirement: Nothing to plan
When no item gets a letter section, `plan-input` SHALL write no input, and its reply SHALL say there is nothing to plan and give the count of each other section.

#### Scenario: Every item out
- **WHEN** every item of the review is done, planned, not checked or not decided
- **THEN** no input file is written and the reply says nothing to plan with the counts

### Requirement: Items checked against the repository
Before writing, `plan-input` SHALL check every decided item against the target repository: an item a commit of `git log` closes SHALL go under `Already done` with its short hash, an item an open change of `solo-sdd list --json` covers (its proposal or tasks name the item's file and edit) under `Already planned` with the change id.

#### Scenario: An item already done
- **WHEN** one decided item is closed by a commit of the target repository
- **THEN** that item is under `Already done` with the commit's short hash and has no letter section

#### Scenario: An item already planned
- **WHEN** one decided item is named by an open change of the target repository
- **THEN** that item is under `Already planned` with the change id and has no letter section

### Requirement: Failed check named
An item that names no file, whose named file does not exist in the target repository, or whose quoted line `grep -n` does not find there, SHALL go under `Not checked` with the reason (no file named, the missing path or the line not found).

#### Scenario: A missing file
- **WHEN** a decided item names a file the target repository does not have
- **THEN** that item is under `Not checked` with the missing path and has no letter section

### Requirement: Input kept outside the target
`plan-input` SHALL save the input next to the material it came from when that folder is outside the target repository, else in the folder the owner names, else in `~/Documents/plan-input/`, never inside the target; its name SHALL be `<YYYY-MM-DD> input for spec-plan - <stem of the material's file name>.md`, and a taken name SHALL get `-2`, `-3`, never overwriting a file.

#### Scenario: Material inside the target
- **WHEN** the review lies under the target repository's `docs/` and the owner names a folder for inputs
- **THEN** the input is saved in that folder and nothing is written under the target repository

#### Scenario: A repeat run
- **WHEN** the skill runs twice on the same review on the same day
- **THEN** the second input has the first one's name with the suffix `-2`, and the first file is unchanged

### Requirement: Launch lines
When an input is written, the file and the reply SHALL open with three launch lines: the absolute path of the target repository to open, `/spec-plan "<absolute input path>"`, and `/spec-dispatch` once the plan is committed.

#### Scenario: The launch lines
- **WHEN** the skill writes the input for a target repository from a review outside it
- **THEN** the file lies next to the review, and its first lines and the reply name the target's absolute path, `/spec-plan` with the file's absolute path and `/spec-dispatch`

### Requirement: Target without a process tree
When the target is not a git repository or has no `solo-sdd/` tree, `plan-input` SHALL write no input and SHALL say why and name the target's path.

#### Scenario: No solo-sdd tree
- **WHEN** the skill runs for a target that is a git repository without `solo-sdd/`
- **THEN** no input file is written and the reply says the target has no `solo-sdd/` tree and names its path

#### Scenario: Not a git repository
- **WHEN** the skill runs for a target folder that is not a git repository
- **THEN** no input file is written and the reply says the target is not a git repository and names its path

### Requirement: Skill deployed and listed
`targets.json` SHALL deploy `plan-input` to Claude Code, Codex and the other agents; section 14 of `global/AGENTS.md`, the README and `docs/layout.md` SHALL list it with the manual commands, and `docs/skills-audit.md` SHALL hold its section.

#### Scenario: After the layout
- **WHEN** `python3 sync.py push --replace-foreign` runs on the merged change and then `python3 sync.py status`
- **THEN** `status` shows no `outdated`, `missing`, `first` or `drift` line for `plan-input` in `~/.claude/skills`, `~/.codex/skills` and `~/.agents/skills`
