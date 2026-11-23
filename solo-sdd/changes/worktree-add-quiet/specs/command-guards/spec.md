## MODIFIED Requirements

### Requirement: Worktree add by shell words
`guard` SHALL, as a guard against a misplaced worktree, not a security boundary, read each command by its words after heredoc and quote removal: a git command with `worktree add`, a variable or an alias as subcommand passes only as `git worktree add [-q | --quiet] [-b <name> | -B <name> | --detach | -f] <path> [<commit>]`, no `git -C`, `-c` or wrapper, a path literal or after `~`, `$HOME`, `$TMPDIR` or `${TMPDIR:-/tmp}`, under a temporary root; other forms SHALL be refused naming the plain form.

#### Scenario: A quoted subcommand
- **WHEN** the agent runs `git worktree "add" ~/wt`, `git "worktree" add ~/wt` or `git worktree ad\d ~/wt`
- **THEN** the command is refused, the reason names the plain form

#### Scenario: A variable subcommand
- **WHEN** the agent runs `W=worktree; git $W add ~/wt`
- **THEN** the command is refused

#### Scenario: A heredoc decoy
- **WHEN** a `cat` heredoc holds `git worktree add /tmp/a` and the line then runs `git -C ~ worktree add wt`
- **THEN** the command is refused

#### Scenario: A clustered option or git -C
- **WHEN** the agent runs `git worktree add -fb x /tmp/wt` or `git -C x worktree add /tmp/wt`
- **THEN** the command is refused, the reason names the plain form

#### Scenario: A tmp folder inside the project or a comment
- **WHEN** the agent runs `git worktree add ~/code/proj/tmp/wt` or `git worktree add ../wt # /tmp/`
- **THEN** the command is refused

#### Scenario: The plain form
- **WHEN** the agent runs `git worktree add "${TMPDIR:-/tmp}/wt-x"` or `git worktree add -b feat /tmp/wt-y main`
- **THEN** the command passes

#### Scenario: Text is not a command
- **WHEN** the agent runs `git commit -m "docs: explain git worktree add"` or `echo 'git worktree add /tmp/x'`
- **THEN** the command passes

#### Scenario: The quiet option
- **WHEN** the agent runs `git worktree add -q "$TMPDIR/wt-x" -b x main`, `git worktree add -q -b x "$TMPDIR/wt-x" main` or `git worktree add --quiet /tmp/wt-q`
- **THEN** the command passes

#### Scenario: The quiet option with a variable path
- **WHEN** the agent runs `git worktree add -q "$W" x` or `git worktree add -qb x /tmp/wt`
- **THEN** the command is refused, the reason names the plain form with `[-q | --quiet]`
