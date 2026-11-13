# command-guards Specification

## Purpose
The Bash command checks in the `process-guard` and `guard` hooks tell what the shell will run from text the command only writes or searches for, so a ban fires on actions, not on words in code.

## Requirements

### Requirement: Heredoc text is not a command
The hooks `global/process-guard.py` and `guard` (the Bash secret and model checks in `global/work_hooks.py`) SHALL NOT look for forbidden words in a heredoc body (`<<WORD`, `<<'WORD'`, `<<"WORD"`, `<<-WORD`) if the command taking the heredoc and all commands after it in the same pipeline (`|`) are on the list of the requirement Heredoc text readers. Each heredoc is decided separately. For any other receiver the body is checked as commands. The rest of the command is checked as before.

#### Scenario: Source code into a file
- **WHEN** the command `cat > check.ts <<'EOF'` with a body that has `process.kill(pid)` and `shutdown()`
- **THEN** `process-guard` and `guard` let the command through

#### Scenario: A script into a shell
- **WHEN** the command `bash <<'EOF'` with the body `pkill node`
- **THEN** `process-guard` refuses the command

#### Scenario: Text into a shell pipeline
- **WHEN** the command `cat <<'EOF' | sh`, `setsid bash <<'EOF'` or `cat <<'EOF' \` with `| bash` on the next line, with the body `kill 1234`
- **THEN** `process-guard` refuses the command

#### Scenario: A model rules bypass in a heredoc
- **WHEN** the command `cat >> ~/.zshrc <<'EOF'` with the body `export SOLO_SDD_EXPENSIVE_OK=1`
- **THEN** `guard` refuses the command, as before

#### Scenario: A substitution in the text
- **WHEN** the command `cat <<EOF` with the body `$(pkill node)` or `grep "$(pkill node)" f`
- **THEN** `process-guard` refuses the command

#### Scenario: The body and the tail
- **WHEN** after the heredoc the same command has `&& kill 1234`
- **THEN** `process-guard` refuses the command

#### Scenario: Several heredocs on one line
- **WHEN** one line has several heredocs with different receivers
- **THEN** the decision is made for each heredoc separately

#### Scenario: A receiver behind a wrapper or an unknown program
- **WHEN** the heredoc is taken by a shell, a shell behind a wrapper (`setsid bash`, `sudo -u x bash`) or an unknown program
- **THEN** the body is checked as commands

#### Scenario: A line continued with a backslash
- **WHEN** the line with the heredoc is continued with `\` at the end
- **THEN** it is the same command: the heredoc body starts after the continued line

#### Scenario: A command substitution in a body or a pattern
- **WHEN** a heredoc body with an unquoted marker, or a pattern or script from the requirement Search pattern is not a command, has a command substitution (`$(`, a backquote, `<(`, `>(`)
- **THEN** they are checked as commands: the shell runs them

#### Scenario: A process substitution at the receiver
- **WHEN** the heredoc receiver or a command of its pipeline holds `<(…)` or `>(…)`
- **THEN** the body is passed to a process and is checked

#### Scenario: An escaped heredoc
- **WHEN** the command has `\<<X`
- **THEN** it is not a heredoc: the shell reads `<X` as a file and runs the next lines, and they are checked as commands

#### Scenario: The bypass transfer check sees the body
- **WHEN** moving `SOLO_SDD_EXPENSIVE_OK` into the environment is checked (capability `model-guard`, Agent cannot enable override)
- **THEN** the check gets the whole command, with the heredoc body

### Requirement: Search pattern is not a command
The hooks SHALL NOT count as a forbidden word or a secret read the search pattern of `grep`, `egrep`, `rg`, `git grep`, `ag` and a `sed` script. The pattern is the values of `-e`/`--regexp`, and without them the first argument that does not start with `-` and does not stand right after an option with a value. A `sed` script is the values of `-e`/`--expression`, and without them the first such argument. The other arguments (paths and option values) are checked as before.

#### Scenario: Searching for a word in code
- **WHEN** the command `grep -rn "shutdown" packages/mcp/src` or `grep -nE 'zshrc|PATH|launchctl' install.sh | head`
- **THEN** `process-guard` lets it through

#### Scenario: Searching for an environment access
- **WHEN** the command `grep -n "process.env" apps/desktop/src/main`
- **THEN** `guard` lets it through

#### Scenario: Replacing text in code
- **WHEN** the command `sed -i '' 's|process.kill(-child.pid, sig);|child.kill(sig);|' process.ts` or `sed -i '' 's/a/process.env["X"]/' f.ts`
- **THEN** `process-guard` and `guard` let it through

#### Scenario: Searching in a secrets file
- **WHEN** the command `grep API_KEY .env`, `grep -e API_KEY .env` or `sed -n 1p .env`
- **THEN** `guard` refuses it, as before

#### Scenario: Options with a value
- **WHEN** an option with a value stands before the argument: `-A`, `-B`, `-C`, `-m`, `-g`, `-t`, `-f`, `--include`, `--exclude`, `--glob`, `--type`
- **THEN** this argument is the option value, not a pattern

#### Scenario: The backup suffix of sed -i
- **WHEN** right after `-i` there is an empty argument (`sed -i ''` on macOS)
- **THEN** it is the backup suffix, not a script

#### Scenario: Search output into an executor
- **WHEN** the search output goes through a pipeline not into a text reader (`grep x f | sh`)
- **THEN** the pattern is not cut and is checked

#### Scenario: A sed script reads or writes a file
- **WHEN** a `sed` script has the file read or write commands `r`, `R`, `w`, `W`
- **THEN** the script is not cut and is checked

#### Scenario: Separators inside quotes
- **WHEN** a quoted pattern holds `;`, `&&`, `||`, `|`, `&` or a newline, for example `'a|b'`
- **THEN** it is part of the pattern: commands are split into parts by these signs only outside quotes

### Requirement: Codex launch is a program
The Codex model check in `guard` SHALL count as a Codex run a separate command word `codex` (with or without a path) followed by `exec` or `e`, wherever it stands: behind any wrapper, after `xargs`, in `find -exec`; the texts of `$(…)`, `<(…)`, backquotes, `eval` and a shell's `-c` string (including `-lc`) are parsed the same way.

#### Scenario: Codex help text in a script
- **WHEN** the command `node -e 'const out="Usage: codex exec [FLAGS] [TEXT]";' f.txt` in a test stand
- **THEN** `guard` lets it through

#### Scenario: A Codex run through a shell
- **WHEN** the command `bash -c 'codex exec -m gpt-6-astra hi'`, `cd w && codex exec -m gpt-6-astra hi`, `setsid codex exec -m gpt-6-astra hi` or `cat <(codex exec -m gpt-6-astra hi)`
- **THEN** `guard` refuses it, as before

#### Scenario: Options between codex and exec
- **WHEN** the command `codex -m x exec …`
- **THEN** it is a Codex run: options are allowed between `codex` and `exec`

#### Scenario: Words in another program's string
- **WHEN** the words `codex exec` stand inside a quoted string passed to another program (`node -e '…'`, `git commit -m "…"`)
- **THEN** they do not count as a run

### Requirement: Claude Code built-in worktrees
`guard` SHALL let through the built-in Claude Code worktrees: the `claude` command with `--worktree`, `--worktree=<name>` or `-w`, the `EnterWorktree` tool with any path or name and `isolation: "worktree"` of `Agent`. The built-in Codex worktrees (`codex` with `--worktree`) and `git worktree add` with a path outside the temporary folder SHALL still be refused.

#### Scenario: A session in its own worktree
- **WHEN** the agent runs `claude --worktree feature-auth` or `claude -w`
- **THEN** the command passes

#### Scenario: A subagent in its own worktree
- **WHEN** the main session launches `Agent` with `isolation: "worktree"`
- **THEN** the call passes

#### Scenario: Codex and git as before
- **WHEN** the agent runs `codex exec --worktree 'implement x'` or `git worktree add ../copy`
- **THEN** the command is refused, as before

### Requirement: Heredoc text readers
The programs that read text rather than run it through a shell in the requirement Heredoc text is not a command SHALL be: `cat`, `tee`, `head`, `tail`, `wc`, `sort`, `uniq`, `grep`, `egrep`, `rg`, `jq`, `cut`, `tr`, `nl`, `column`, `fold`, `fmt`, `paste`, `rev`, `tac`, `comm`, `diff`, `less`, `more`, `base64`, `od`, `xxd`, `shasum`, `md5`, `python`, `python3`, `node`.

#### Scenario: A reader from the list
- **WHEN** the command `tee notes.md <<'EOF' | sort` with the body `pkill node`
- **THEN** `process-guard` lets the command through: `tee` and `sort` are on the list

#### Scenario: A receiver not on the list
- **WHEN** the command `awk -f - <<'EOF'` with the body `pkill node`
- **THEN** `process-guard` refuses the command: `awk` is not on the list

### Requirement: Messages and paths are not commands
`process-guard` SHALL NOT refuse a forbidden name that occurs only in the value of `-m` or `--message` of `git commit` or `git tag`, or of `-t`, `--title`, `-b` or `--body` of `gh pr` or `gh issue`, or only followed by `.` or `/` in a word (`docs/kill.md`, `src/kill/x.py`); a word ending with the name is a program. The same name run as a command, by its basename (`/bin/kill`), inside `bash -c`, `sh -c` or a substitution, SHALL still be refused.

#### Scenario: A commit message
- **WHEN** the agent runs `git commit -m "fix: graceful shutdown of the worker"` or `gh pr create --title "Add kill switch"`
- **THEN** the command passes

#### Scenario: A file path
- **WHEN** the agent runs `cat docs/kill.md`
- **THEN** the command passes

#### Scenario: A command in a shell string
- **WHEN** the agent runs `bash -c "kill 1"` or `git commit -m "$(pkill node)"`
- **THEN** the command is refused

#### Scenario: A command by its path
- **WHEN** the agent runs `/bin/kill 1` or `/usr/bin/pkill node`
- **THEN** the command is refused

#### Scenario: A parameter expansion earlier on the line
- **WHEN** the agent runs `T="${TMPDIR:-/tmp}"; git commit -m "graceful shutdown"` or `echo ${HOME}; git commit -m "graceful shutdown"`
- **THEN** the command passes

### Requirement: Shell forms the text cut cannot read
The hooks SHALL cut no commit message and no search pattern on a line that holds `$'`, `=(`, a word starting with `#`, or a `${` that is not a plain parameter expansion, and SHALL check every word of that line; this comes before Messages and paths are not commands and Search pattern is not a command. A plain parameter expansion (`${`, only letters, digits and the signs `_ # : - = + ? % / . @ * ! , ^ ~`, `}`) SHALL NOT stop the cut.

#### Scenario: A plain expansion before a search
- **WHEN** the agent runs `T="${TMPDIR:-/tmp}"; grep -n "kill" docs/x.md`
- **THEN** `process-guard` lets it through

#### Scenario: A plain expansion before a message in a process tree
- **WHEN** the agent runs `T="${TMPDIR:-/tmp}"; git commit -m "a; gh pr merge 5"` in a project with a `solo-sdd/` tree
- **THEN** `guard` lets it through; `T=${X:-"a b"}; git commit -m "a; gh pr merge 5"` is refused

#### Scenario: A plain expansion is not plain for the secret guard
- **WHEN** the agent runs `T="${TMPDIR:-/tmp}"; grep -n "process.env" apps/desktop/src/main`
- **THEN** `guard` refuses it, as before: Secret file reads in Bash counts a `.env` name anywhere in a command holding `${`

#### Scenario: A brace command substitution
- **WHEN** the agent runs `X=${ kill 1; }; git commit -m "done"`
- **THEN** the command is refused

#### Scenario: An expansion the cut cannot read
- **WHEN** the agent runs `echo ${X:-"a b"}; git commit -m "graceful shutdown"`, `echo ${X:-\}}; git commit -m "graceful shutdown"` or `T=${X; git commit -m "graceful shutdown"`
- **THEN** the command is refused: a quote, a backslash or a missing `}` can move quote boundaries, so the line is checked uncut, as before

#### Scenario: A zsh process substitution
- **WHEN** the agent runs `git commit -m =(kill 1)`, `T="${TMPDIR:-/tmp}"; git commit -m =(kill 1)` or `grep =(kill 1) x`
- **THEN** `process-guard` refuses each: zsh runs the command inside `=(…)`, so the line is checked uncut; `git commit -m =(gh pr merge 5)` in a project with a `solo-sdd/` tree is refused by `guard`

#### Scenario: A known false refusal of an array assignment
- **WHEN** the agent runs `A=(x y); git commit -m "graceful shutdown"`
- **THEN** the command is refused: `=(` anywhere on the line stops the cut, an array assignment included, and a test pins it

### Requirement: Worktree add by shell words
`guard` SHALL, as a guard against an accidental worktree placement, not a security boundary, read each command by its words after heredoc and quote removal: a git command with `worktree add`, a variable or an alias as subcommand passes only as `git worktree add [-b <name> | -B <name> | --detach | -f] <path> [<commit>]`, no `git -C`, `-c` or wrapper, a path literal or after `~`, `$HOME`, `$TMPDIR` or `${TMPDIR:-/tmp}`, under a temporary root; other forms SHALL be refused naming the plain form.

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

### Requirement: Worktree path line state
`guard` SHALL refuse a plain `git worktree add` whose path an earlier command of the same line can move: a `$TMPDIR` or `${TMPDIR:-/tmp}` prefix after an assignment or `export` of `TMPDIR`, any path after an `ln`, a relative path after a `cd`, `pushd` or `popd`.

#### Scenario: TMPDIR changed on the line
- **WHEN** the agent runs `TMPDIR=$HOME/Code; git worktree add "$TMPDIR/wt"` or `export TMPDIR=~/Code && git worktree add "${TMPDIR:-/tmp}/wt"`
- **THEN** the command is refused

#### Scenario: A link made on the line
- **WHEN** the agent runs `ln -s ~/Code /tmp/lnk && git worktree add /tmp/lnk/wt`
- **THEN** the command is refused

#### Scenario: A cd before a relative path
- **WHEN** the agent runs `cd ~/Code && git worktree add wt` from a working folder under `/private/tmp`
- **THEN** the command is refused

### Requirement: Worktree guard known limits
`guard` SHALL keep its known bypass classes outside the check and its known false refusals, each pinned by a test, so that changing either is a decision: an expansion after `worktree` where git is not read as the program, `xargs git worktree $A`, an escape behind a quote desync and a config alias pass; adjacent `worktree add` text next to `#`, `$'`, `=(` or a non-plain `${`, a path with `()<>;&|` and `git worktree $SUB` are refused.

#### Scenario: Known passes
- **WHEN** the agent runs `G=git; $G worktree $A /tmp/x`, `xargs git worktree $A /tmp/x`, `git config alias.wt worktree && git wt add ~/wt`, `bash -c "git worktree \$A /tmp/x"`, `GIT worktree $A /tmp/x`, `2>/dev/null git worktree $A /tmp/x`, `env -u X git worktree $A /tmp/x`, `f() { git worktree $1 /tmp/x; }; f add` or `case x in x) git worktree $A /tmp/x;; esac`
- **THEN** the command passes: these forms are outside the guard

#### Scenario: Known refusals
- **WHEN** the agent runs `git commit -m "git worktree add (#12)"`, `git worktree add '/tmp/wt (copy)'` or `git worktree $SUB`
- **THEN** the command is refused, the reason names the plain form

#### Scenario: An array assignment before a worktree add
- **WHEN** the agent runs `ARR=(a b); git worktree add /tmp/wt-x` or `A=(1); git commit -m "see git worktree add /tmp/x"`
- **THEN** the command is refused, the reason names `=(…)` and the plain form
