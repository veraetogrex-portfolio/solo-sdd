## MODIFIED Requirements

### Requirement: Built-in worktree folder ignored
`solo-sdd init` (after writing the tree) and `project-init` (after its process tree step) SHALL run `solo-sdd ignore --write` (Ignore command), which holds `.claude/worktrees/` while `git.ignore` names it, as by default: with no `.gitignore` rule outside the block hiding it the line goes into the solo-sdd block (no file: created); other lines do not change. A refusal of the command SHALL make `init` exit 1 with its reason, the tree kept.

#### Scenario: No line
- **WHEN** the project's `.gitignore` has no rule that hides `.claude/worktrees/`
- **THEN** after `project-init` the line `.claude/worktrees/` exists, the other lines are unchanged, `git check-ignore .claude/worktrees/a` finds the rule

#### Scenario: A repeated run
- **WHEN** `project-init` runs a second time in the same project
- **THEN** the line `.claude/worktrees/` occurs in `.gitignore` once

#### Scenario: The rule already exists as another line
- **WHEN** `.gitignore` has the line `.claude/`
- **THEN** `.gitignore` gets no `.claude/worktrees/` line after `project-init`

#### Scenario: A broken block in init
- **WHEN** `.gitignore` has `# solo-sdd:begin` without `# solo-sdd:end`, and `solo-sdd init --yes` runs
- **THEN** exit 1 names the `.gitignore` line, `solo-sdd/` is created, `.gitignore` keeps its bytes

### Requirement: Process artifacts in git
In a project where `project-init` creates `.gitignore`, it SHALL NOT ignore `solo-sdd/`, `AGENTS.md` and `CLAUDE.md` and SHALL commit them in one commit naming only these paths and `.gitignore`. If `.gitignore` already exists and none of the paths is hidden, the skill SHALL commit the same three paths. If this run changed the solo-sdd block of an existing `.gitignore`, it SHALL go into the artifact commit, or, if they are not committed, into its own commit.

#### Scenario: A new project
- **WHEN** `project-init` runs in a folder without `.gitignore`
- **THEN** `git ls-files` shows `AGENTS.md`, `CLAUDE.md` and `solo-sdd/project.md`, the last commit has no other files except `.gitignore`

#### Scenario: The project hides the specs
- **WHEN** the existing `.gitignore` has the line `solo-sdd/`
- **THEN** in `.gitignore` at most the solo-sdd block changed, the artifacts are not committed, the report names `solo-sdd/`, the line and the transfer cost

#### Scenario: An existing `.gitignore` does not hide the artifacts
- **WHEN** `.gitignore` already exists, none of the three paths is hidden by it, the tree has another uncommitted edit
- **THEN** the last commit holds only the files of these three paths and `.gitignore` if its solo-sdd block changed; there are no other changes of `.gitignore`, the other edit stayed uncommitted

### Requirement: Hidden process artifacts
If `.gitignore` already exists and `git check-ignore` names one of the paths `solo-sdd/`, `AGENTS.md` or `CLAUDE.md`, the `project-init` skill SHALL change nothing in `.gitignore` except the solo-sdd block by the requirement Built-in worktree folder ignored, not commit the artifacts, and write into the report the path, the `.gitignore` line that hides it, and that such artifacts reach a worktree only through `sdd-worktree.py`.

#### Scenario: Only CLAUDE.md is hidden
- **WHEN** the existing `.gitignore` has the line `CLAUDE.md`, and no solo-sdd block
- **THEN** only the solo-sdd block is appended to `.gitignore` and committed in a separate commit of `.gitignore` alone, the artifacts are not committed, the report names `CLAUDE.md`, the line `CLAUDE.md` and the transfer only through `sdd-worktree.py`
