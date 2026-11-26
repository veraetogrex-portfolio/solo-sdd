## MODIFIED Requirements

### Requirement: Input kept outside the target
When an input is written, `plan-input` SHALL save it in the folder the owner names, else next to the material's file when that folder is outside the target, else in `~/Documents/plan-input/` (created when missing), never inside the target, named `<YYYY-MM-DD> input for spec-plan - <stem>.md` (the material file's stem, or `chat` with no file); a taken name SHALL get `-2`, `-3` before `.md`, never overwriting or reusing a file.

#### Scenario: Material inside the target
- **WHEN** the review lies under the target repository's `docs/` and the owner names a folder for inputs
- **THEN** the input is saved in that folder and nothing is written under the target repository

#### Scenario: Material with no file
- **WHEN** the owner's decisions are given in the chat, no file within reach holds them, the owner names no folder and the target passes the process-tree check
- **THEN** the input is saved as `<date> input for spec-plan - chat.md` in `~/Documents/plan-input/`

#### Scenario: A pasted review found on disk
- **WHEN** the review is pasted in the chat, a file within reach outside the target holds it, and the owner names no folder
- **THEN** the input is saved next to that file with that file's stem, as for a review given by its path

#### Scenario: A repeat run
- **WHEN** the skill runs twice on the same review on the same day
- **THEN** the second input has the first one's name with the suffix `-2`, and the first file is unchanged

#### Scenario: An earlier input found
- **WHEN** the save folder already holds the input of the same review file from earlier the same day and the owner asks again
- **THEN** a new file with the suffix `-2` is written, the earlier file is neither checked nor changed, and the reply names the new file

### Requirement: Launch lines
When an input is written, the reply SHALL open with three launch lines, its first line being launch line 1, and the file SHALL hold them under its title: the absolute path of the target repository to open, `/spec-plan "<absolute input path>"`, and `/spec-dispatch` once the plan is committed.

#### Scenario: The launch lines
- **WHEN** the skill writes the input for a target repository from a review outside it and the owner names no folder
- **THEN** the file lies next to the review, its lines under the title and the reply's first non-empty lines name the target's absolute path, `/spec-plan` with the file's absolute path and `/spec-dispatch`

#### Scenario: Launch lines before the path
- **WHEN** the skill writes an input into a folder the owner names
- **THEN** the reply's first non-empty line is launch line 1 with the target's absolute path, and any other line naming the input file's path comes after the three launch lines

### Requirement: Target without a process tree
When the target is not a git repository or has no `solo-sdd/` tree, `plan-input` SHALL stop before any item check, write no input, and say why and name the target's path, with no section counts.

#### Scenario: No solo-sdd tree
- **WHEN** the skill runs for a target that is a git repository without `solo-sdd/`
- **THEN** no input file is written and the reply says the target has no `solo-sdd/` tree and names its path

#### Scenario: Not a git repository
- **WHEN** the skill runs for a target folder that is not a git repository
- **THEN** no input file is written and the reply says the target is not a git repository and names its path

#### Scenario: Nothing created for a target outside git
- **WHEN** the skill runs for a target folder that is not a git repository and holds no `docs/` folder
- **THEN** no file or folder is created under the target or anywhere else in the stand, and the reply gives the git reason
