## Purpose
A request that names a project on this computer is worked in that project's own repository, with its rules, so that edits land under its git and nothing is left in a copy.

## ADDED Requirements

### Requirement: Work in the named project's repository
Item 1 of section 0 of the global rules SHALL hold that a request naming a project on this computer is worked in that project's repository, which then takes the place of the current folder for items 1-3: its rules are read there, it is edited and run from there, and its sources are not copied into the session folder; a current folder already in a worktree or clone of it stays; a session that cannot write there SHALL name the access it needs and copy nothing.

#### Scenario: A fix asked from an empty folder
- **WHEN** an agent with the global rules runs in an empty session folder and is asked to fix a file of a fixture project that lies under `~/Code`
- **THEN** the edit is in the fixture project, and the session folder holds no copy of its sources

#### Scenario: The project's own rules
- **WHEN** the fixture project's `AGENTS.md` asks for commit messages starting with `greeter:`
- **THEN** the agent's commit in the fixture project starts with `greeter:`

#### Scenario: Edits committed in the project
- **WHEN** the same agent reports the fix of the fixture project as done
- **THEN** `git -C <fixture project> log` has a new commit with the edit and `git -C <fixture project> status --porcelain` prints nothing

### Requirement: Project lookup
The project SHALL be a git repository at any depth under the projects folder the owner's rules name (by default `~/Code`), worktrees skipped, whose folder name equals or starts with the project name the request uses, both case-folded with spaces, `-` and `_` taken as one; an equal name wins over a prefix, and among several the latest commit wins, and the report names the others; with no match the work stays in the current folder and the report says so.

#### Scenario: Two matching folders
- **WHEN** `~/Code` holds `x/zz-greeter-bot` and `zz-greeter-bot-old` and the request names "the zz greeter bot"
- **THEN** the edit is in `x/zz-greeter-bot`, `zz-greeter-bot-old` is unchanged, and the report names `zz-greeter-bot-old`

### Requirement: Experiment copy carried back
Item 1 of section 0 of the global rules SHALL hold that a copy of a named project for an experiment lives only in a temporary worktree of section 9 (`${TMPDIR:-/tmp}/wt-<name>`; the built-in worktree copies the current repository, not the named one), never in the session folder, and that its edits are committed in the project before the report, the worktree removed.

#### Scenario: An experiment worktree
- **WHEN** an agent tries an edit of the fixture project in a copy before applying it
- **THEN** the copy is a `git worktree` under `${TMPDIR:-/tmp}/wt-`, the edit lands as a commit of the project, and `git worktree list` of the project no longer shows the copy
