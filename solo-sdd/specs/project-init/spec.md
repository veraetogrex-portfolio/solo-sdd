# project-init Specification

## Purpose
The `project-init` skill prepares a project for work by the algorithm: it writes `AGENTS.md` with the sections the solo-sdd skills and scripts read.

## Requirements

### Requirement: Test command under dispatcher
If the project's `AGENTS.md` has a "Working copy" section, `project-init` SHALL write the test command in the "Commands" section with the thread limit `max(1, ⌊cores / N⌋)`, where N is the item "Orchestrators:" (default 2): for vitest and jest `--maxWorkers`, for pytest-xdist `-n`. If there is no section or the test runner cannot limit threads, the command is written without a flag.

#### Scenario: Vitest under the dispatcher
- **WHEN** the project has vitest, the computer has 8 cores, "Working copy" with "Orchestrators: 2"
- **THEN** "Commands" has the test command with `--maxWorkers=4`

#### Scenario: A project without the dispatcher
- **WHEN** there is no "Working copy" section
- **THEN** the test command has no thread limit flag

#### Scenario: Without the "Orchestrators:" item
- **WHEN** the project has vitest, the computer has 8 cores, "Working copy" without the item "Orchestrators:"
- **THEN** "Commands" has the test command with `--maxWorkers=4`

### Requirement: Process artifacts in git
In a project where `project-init` creates `.gitignore`, it SHALL NOT ignore `solo-sdd/`, `AGENTS.md` and `CLAUDE.md` and SHALL commit them in one commit naming only these paths and `.gitignore`. If `.gitignore` already exists and none of the paths is hidden, the skill SHALL commit the same three paths. If this run appended `.claude/worktrees/` to an existing `.gitignore`, `.gitignore` SHALL go into the artifact commit, or, if they are not committed, into its own commit.

#### Scenario: A new project
- **WHEN** `project-init` runs in a folder without `.gitignore`
- **THEN** `git ls-files` shows `AGENTS.md`, `CLAUDE.md` and `solo-sdd/project.md`, the last commit has no other files except `.gitignore`

#### Scenario: The project hides the specs
- **WHEN** the existing `.gitignore` has the line `solo-sdd/`
- **THEN** in `.gitignore` at most the appended line `.claude/worktrees/` changed, the artifacts are not committed, the report names `solo-sdd/`, the line and the transfer cost

#### Scenario: An existing `.gitignore` does not hide the artifacts
- **WHEN** `.gitignore` already exists, none of the three paths is hidden by it, the tree has another uncommitted edit
- **THEN** the last commit holds only the files of these three paths and `.gitignore` if the line `.claude/worktrees/` was appended to it; there are no other changes of `.gitignore`, the other edit stayed uncommitted

### Requirement: Built-in worktree folder ignored
`project-init` SHALL make git ignore the project's `.claude/worktrees/` folder: if `git check-ignore -q .claude/worktrees/x` finds no rule, the skill appends the line `.claude/worktrees/` to the end of `.gitignore` (no file: creates it); the other lines do not change. If a rule already works, by the same line or another (for example, `.claude/`), `.gitignore` does not change.

#### Scenario: No line
- **WHEN** the project's `.gitignore` has no rule that hides `.claude/worktrees/`
- **THEN** after `project-init` the line `.claude/worktrees/` exists, the other lines are unchanged, `git check-ignore .claude/worktrees/a` finds the rule

#### Scenario: A repeated run
- **WHEN** `project-init` runs a second time in the same project
- **THEN** the line `.claude/worktrees/` occurs in `.gitignore` once

#### Scenario: The rule already exists as another line
- **WHEN** `.gitignore` has the line `.claude/`
- **THEN** `.gitignore` is not changed after `project-init`

### Requirement: Hidden process artifacts
If `.gitignore` already exists and `git check-ignore` names one of the paths `solo-sdd/`, `AGENTS.md` or `CLAUDE.md`, the `project-init` skill SHALL change nothing in `.gitignore` except the line `.claude/worktrees/` by the requirement Built-in worktree folder ignored, not commit the artifacts, and write into the report the path, the `.gitignore` line that hides it, and that such artifacts reach a worktree only through `sdd-worktree.py`.

#### Scenario: Only CLAUDE.md is hidden
- **WHEN** the existing `.gitignore` has the line `CLAUDE.md`, and no line `.claude/worktrees/`
- **THEN** only `.claude/worktrees/` is appended to `.gitignore` and committed in a separate commit of `.gitignore` alone, the artifacts are not committed, the report names `CLAUDE.md`, the line `CLAUDE.md` and the transfer only through `sdd-worktree.py`

### Requirement: Codebase map
When `/project-init` runs in a repository whose `HEAD` has files outside `docs/`, `solo-sdd/` and the files it commits itself (`AGENTS.md`, `CLAUDE.md`, `.gitignore`), it SHALL create `docs/codebase/STACK.md` (stack, dependencies, external services), `ARCHITECTURE.md` (layers, data flow, entry points, folder structure), `CONVENTIONS.md` (naming, error handling, tests) and `CONCERNS.md` (debt, security, bottlenecks, risks). A repository without such commits SHALL get no map.

#### Scenario: Existing project
- **WHEN** `/project-init` runs in a repository with application code in its history
- **THEN** the four files exist under `docs/codebase/` and none of them is empty

#### Scenario: New project
- **WHEN** `/project-init` runs in an empty repository or one without commits
- **THEN** `docs/codebase/` is not created

### Requirement: Map statements with paths
Every statement in a map file SHALL be a list item naming, in backticks, at least one path that exists in the repository at the stamped commit. A statement the subagent cannot tie to a path SHALL NOT be written. A map file SHALL NOT quote values from `.env` or other secrets.

#### Scenario: Claim without a place
- **WHEN** a subagent would write "errors are logged centrally" and finds no file that does it
- **THEN** the statement is absent from the map

#### Scenario: Secret in the code
- **WHEN** a concern is a key committed in `config.js`
- **THEN** `CONCERNS.md` names the file and the kind of secret, not its value

#### Scenario: Check script
- **WHEN** `tests/stands/map-stand/check.py <repo>` runs on a fresh map
- **THEN** it prints no statement without an existing path and exits 0

### Requirement: Map stamp and re-run
Each map file SHALL start with the line `Commit: <full hash> <date>` of `HEAD` at writing. A re-run of `/project-init` SHALL keep an existing map; `/project-init map` SHALL rewrite all four files with new stamps and change nothing else.

#### Scenario: Re-run keeps the map
- **WHEN** `/project-init` runs again in a project with `docs/codebase/`
- **THEN** the four files and their stamps are unchanged

#### Scenario: Refresh
- **WHEN** `/project-init map` runs after new commits
- **THEN** each stamp names the new `HEAD` and no file outside `docs/codebase/` changes

### Requirement: Map written by subagents
The four map files SHALL be written by four parallel subagents on the cheapest model, one file each, each returning only its path and line count. The lead agent SHALL check that the four files exist and are not empty, and SHALL NOT read their full text into its context to do so.

#### Scenario: Lead context
- **WHEN** the map is written
- **THEN** the lead's transcript holds four replies with a path and a line count and no map text besides the `CONCERNS.md` items read for the report

#### Scenario: Subagent fails
- **WHEN** a map file is missing or empty after its subagent returned
- **THEN** that subagent runs once more; still missing or empty — the report names the file as not written and the other three stay

### Requirement: Concerns as candidates
The `/project-init` report SHALL list each item of `CONCERNS.md` as a candidate for `/spec-plan`, one line each. `/project-init` SHALL NOT create a change from them.

#### Scenario: Three concerns
- **WHEN** `CONCERNS.md` holds three items
- **THEN** the report lists three candidate lines and `solo-sdd/changes/` gets no new folder
