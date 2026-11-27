## MODIFIED Requirements

### Requirement: Forced push refused
`guard` SHALL refuse a Bash command that by its plain forms runs `git push` with a force: `--force`, `-f` alone or in a cluster before a value letter (`-o`), `--force-with-lease`, `--force-if-includes`, a prefix of one of them, or a `+` refspec, in any project, naming the rule and a new commit. A message, a search pattern and a heredoc body for a text program are text, except on a line read with quotes ignored. The forms of Known bypasses of the history guard pass.

#### Scenario: The forced forms
- **WHEN** the agent runs `git push --force`, `git push -f origin x`, `git push -fu origin x`, `git push --force-with-lease`, `git push --force-if-includes --force-with-lease`, `git push --force-w`, `git push origin +main`, `git push origin -- +main`, `git -C ../repo push -f`, `/usr/bin/git push -f`, `sudo git push -f`, `env GIT_TRACE=1 git push -f` or `command git push -f`, also outside a git repository
- **THEN** the command is refused, the reason names the rule and a new commit

#### Scenario: Plain pushes
- **WHEN** the agent runs `git push origin main`, `git push -u origin x`, `git push --delete origin x`, `git push -o ci.skip origin x` or `git push -of origin x` (`f` is the value of `-o`)
- **THEN** the command passes

#### Scenario: Other programs and subcommands
- **WHEN** the agent runs `python3 sync.py push --force`, `git worktree remove --force /tmp/wt` or `git branch -f x main`
- **THEN** the command passes

#### Scenario: Text about a forced push
- **WHEN** the agent runs `git commit -m "never git push --force"` or `rg -- "push --force" docs`
- **THEN** the command passes

#### Scenario: A hidden run
- **WHEN** the agent runs `bash -c "git push -f"`, `eval git push --force` or `echo $(git push -f)`
- **THEN** the command is refused

#### Scenario: Broken input
- **WHEN** the agent runs `git push -f "origin` (an unclosed quote), `git push -f $(echo x`, `cat <<EOF; git push -f` with no end marker, a command of 200,000 characters ending in `git push -f`, 200,000 characters of backslash-newline lines before `; git push -f`, or 5,000 nested `$(…)` before `; git push -f`
- **THEN** the command is refused within the hook's 10 seconds, and `guard` raises no exception

#### Scenario: An assignment with a spaced substitution
- **WHEN** the agent runs `TS=$(date +%s) git push -f`, `` TS=`date +%s` git push -f ``, `TS=$(date +%s) sudo git push -f`, `TS=$(date +%s) command git push -f`, `TS=$(date +%s) /usr/bin/git push -f`, `TS=$(date +%s) git -C ../r push -f`, `TS=$(date +%s) git push --force-with-lease`, `TS=$(date +%s) git push origin +main`, `TS=$(date +%s) bash -c 'git push -f'` or `TS=$(date +%s) git reset --hard`
- **THEN** the command is refused, the reason names the rule and a new commit

#### Scenario: Broken input in an assignment
- **WHEN** the agent runs `TS=$(date +%s git push -f` (an unclosed substitution in the assignment), `` TS=`date +%s git push -f `` (an unclosed backquote), `TS="$(date +%s) git push -f` (an unclosed quote), 5,000 nested `$(…)` in the assignment, or an assignment `TS=$(echo ` + 200,000 characters + `)` before ` git push -f`
- **THEN** the command is refused within the hook's 10 seconds, and `guard` raises no exception

#### Scenario: A plain command after a spaced substitution
- **WHEN** the agent runs `TS=$(date +%s) git push origin main` or `TS=$(date +%s) git commit -m "x"`
- **THEN** the command passes
