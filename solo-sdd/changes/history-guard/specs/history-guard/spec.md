## Purpose

The `guard` hook refuses the two git commands the global rules forbid, a forced push and a hard reset, by the words the shell will run, so the rule holds when an agent forgets it, while text that only mentions them passes.

## ADDED Requirements

### Requirement: Forced push refused
`guard` SHALL refuse a Bash command that runs `git push` with an option git reads as a force: `--force`, `-f` alone or in a cluster before any letter that takes a value (`-o`), `--force-with-lease`, `--force-if-includes` or their unambiguous prefixes, or a refspec starting with `+`, from any caller, the reason naming the rule and a new commit. A message, a search pattern and a heredoc body for a text program are not commands. It guards against an accident, not an attack.

#### Scenario: The forced forms
- **WHEN** the agent runs `git push --force`, `git push -f origin x`, `git push -fu origin x`, `git push --force-with-lease`, `git push --force-if-includes --force-with-lease`, `git push --force-w`, `git push origin +main` or `git -C ../repo push -f`
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
- **WHEN** the agent runs `git push -f "origin` (an unclosed quote), `git push -f $(echo x`, `cat <<EOF` with no end marker before `git push -f`, or a command of 200,000 characters ending in `git push -f`
- **THEN** the command is refused within the hook's 10 seconds, and `guard` raises no exception

### Requirement: Hard reset refused
`guard` SHALL refuse a Bash command that runs `git reset` with `--hard`, or an unambiguous prefix git reads as it (`--ha`, `--har`), among its options before any `--`, from any caller, the reason naming the rule and `git stash` or `git restore <path>` as the safe way, read by the words of the requirement Forced push refused. Nothing but this guard stands between an agent and a hard reset.

#### Scenario: The hard forms
- **WHEN** the agent runs `git reset --hard`, `git reset --hard HEAD~1`, `git reset origin/main --hard` or `git reset --har HEAD`
- **THEN** the command is refused, the reason names `git stash`

#### Scenario: Other resets
- **WHEN** the agent runs `git reset`, `git reset --soft HEAD~1`, `git reset -- file.py` or `git reset -- --hard` (a path named `--hard`)
- **THEN** the command passes

### Requirement: Known bypasses of the history guard
Every form the requirement Known bypasses of the merge guard lists (`xargs`, `find -exec`, `sudo -u`, `env -u`, a shell function, `bash -c` or `eval` after `A=(…)`, substitutions deeper than 3, a `)` or `(` that moves a substitution end, a backslash-newline) SHALL pass as outside it, as SHALL a git alias and a `python3` or `node` heredoc body, each pinned by a test. Branch protection is the boundary for a push.

#### Scenario: A known bypass closed
- **WHEN** a change makes `guard` refuse one of these forms
- **THEN** the known-limit test fails until the form moves to the refused tests and `docs/hooks.md`

#### Scenario: A known false refusal
- **WHEN** the agent runs `A=(1 2); git commit -m "a; git push -f later"`, a form whose quotes the reader ignores
- **THEN** it is refused, as the merge guard refuses the same form, and the test pins it

#### Scenario: History forms of the bypasses
- **WHEN** the agent runs `echo x | xargs git push -f`, `sudo -u x git push -f`, `env -u X git push -f`, `f(){ git reset --hard; }; f`, `A=(1 2) bash -c 'git push -f'` or `python3 <<'EOF'` with a body running `git push --force`
- **THEN** each command passes, pinned by the known-limit test
