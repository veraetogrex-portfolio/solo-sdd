## ADDED Requirements

### Requirement: Ignore list setting
The key `git.ignore` (paths, default `.claude/worktrees/, .env, .env.*, !.env.example`) SHALL list what the project keeps out of git; an item starting with `!` re-includes the path after it, as in `.gitignore`. `config set git.ignore`, `config unset git.ignore` and the settings screen SHALL print `run: solo-sdd ignore --write`.

#### Scenario: Keep the archive private
- **WHEN** `config set git.ignore ".claude/worktrees/, .env, solo-sdd/changes/archive/"` runs
- **THEN** code 0 and the hint line `run: solo-sdd ignore --write`

#### Scenario: The example file stays in git
- **WHEN** the project has `.env.example`, `git.ignore` has its default, and `solo-sdd ignore --write` runs
- **THEN** `git check-ignore -q .env.example` exits 1 and `git check-ignore -q .env.local` exits 0

### Requirement: Process paths stay tracked
A `git.ignore` value SHALL be refused with exit 1 and the file unchanged (by `config set`, the settings screen, and as a broken line when the file is read) when one of its items, by git's matching, hides `AGENTS.md`, `CLAUDE.md`, `solo-sdd/` or a path under it other than `solo-sdd/changes/archive/`, or starts with `#`; the message names the item and the path it hides.

#### Scenario: Hiding the specs
- **WHEN** `config set git.ignore solo-sdd/` runs
- **THEN** exit 1 names `solo-sdd/`, the file is unchanged

#### Scenario: A glob that hides the rules
- **WHEN** `config set git.ignore "*.md"` runs
- **THEN** exit 1 names `*.md` and `AGENTS.md`, the file is unchanged

### Requirement: Ignore command
`solo-sdd ignore` SHALL print each `!` item of `git.ignore` and each other item no rule of the repository's `.gitignore` files outside its block hides (not `.git/info/exclude` or global excludes); `--write` SHALL put them between `# solo-sdd:begin` and `# solo-sdd:end` of the root `.gitignore` (no file or block: created; an empty list removes the block), other bytes kept. A tracked path of a hiding item SHALL be named with a shell-quoted `git rm --cached -r -- <path>` and stay tracked.

#### Scenario: A repeated write
- **WHEN** `solo-sdd ignore --write` runs twice
- **THEN** the second run prints `no change`, and every listed line occurs once

#### Scenario: A rule already hides it
- **WHEN** `.gitignore` has `.claude/` outside the block
- **THEN** the block has no `.claude/worktrees/` line

#### Scenario: A global rule does not count
- **WHEN** the global excludes file hides `.env` and the project's `.gitignore` does not
- **THEN** after `solo-sdd ignore --write` the block has `.env`

#### Scenario: A tracked file becomes ignored
- **WHEN** `git.ignore` names `docs/waiting.md` and git tracks it
- **THEN** the output names `git rm --cached -r -- docs/waiting.md`, `git ls-files docs/waiting.md` still lists it

### Requirement: Ignore command refusals
`solo-sdd ignore` SHALL exit 1 with every file unchanged when `.gitignore` has a begin marker without its end, an end marker without a begin, or two blocks (naming `.gitignore:<line>`), and outside a git repository (naming `not a git repository`). Without `solo-sdd/config` it SHALL use the defaults.

#### Scenario: An unclosed block
- **WHEN** line 3 of `.gitignore` is `# solo-sdd:begin` and no `# solo-sdd:end` follows
- **THEN** `solo-sdd ignore --write` exits 1 naming `.gitignore:3`, and `.gitignore` keeps its bytes
