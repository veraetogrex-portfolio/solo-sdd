# secret-guard Specification

## Purpose
Keeps the agent from printing secrets: what `guard` refuses about `.env` files and secret variables, and what `install --hooks` writes to settings.

## Requirements

### Requirement: Secret file tools refused
`guard` SHALL refuse a `Read` tool call whose path is a `.env` file and a `Grep` tool call whose `path` is a `.env` file or whose `glob` matches one. A `.env` file is a file named `.env`, `<name>.env` or `.env.<suffix>`, except the suffixes `example`, `sample`, `template` and `dist`. A `Grep` over a folder without such a `glob` SHALL pass.

#### Scenario: The Read tool
- **WHEN** the agent calls `Read` with `/p/.env` or `/p/.env.local`, or `Grep` with path `.env` or glob `.env*`
- **THEN** the call is refused

#### Scenario: A template file
- **WHEN** the agent calls `Read` with `/p/.env.example`
- **THEN** the call passes

### Requirement: Secret file reads in Bash
As an accident guard, not a boundary, `guard` SHALL refuse a Bash command that gives a `.env` file path to a program, redirects input from it, runs `source` or `.` on it, or copies or moves it. `ls`, `test`, `[`, `stat`, `touch`, `chmod`, `git check-ignore`, `grep`/`rg` with `-c`, `-q` or `-l` and an output redirect into it SHALL pass, only in a plain command: one holding `#`, `$'`, `${`, `$(`, a backquote or a backslash SHALL be refused when it names a `.env` file anywhere.

#### Scenario: Indirect reads in Bash
- **WHEN** the agent runs `python3 -c "print(open('.env').read())"`, `cp .env /tmp/e`, `source .env && echo ok`, `git diff .env` or `while read l; do echo $l; done < .env`
- **THEN** each command is refused

#### Scenario: A command that is not plain
- **WHEN** the agent runs `echo ${X:- #}; cat .env`, `echo hi # see .env` or `echo ${X:-"}" #}; env`
- **THEN** each command is refused

#### Scenario: Allowed uses
- **WHEN** the agent runs `test -f .env`, `ls -la .env`, `grep -c '^API_KEY=.' .env`, `echo 'API_KEY=' >> .env` or `cat .env.example`
- **THEN** each command passes

### Requirement: Environment dumps refused
As a guard against accidental dumps, not a boundary, `guard` SHALL refuse a Bash command that runs `env` or `printenv` without arguments, `set` without arguments, `export -p` or `declare -p`, alone or in a pipe, and a command that is not plain and holds such a word.

#### Scenario: A shell dump
- **WHEN** the agent runs `set | grep -i api` or `export -p`
- **THEN** the command is refused

### Requirement: Known bypasses of the Bash guard
`docs/hooks.md` SHALL name as outside the Bash guard: brace expansion, `sh -c` with the file as a positional argument, process substitution with a quoted `)`, a heredoc marker line with an open quote, `${X:-env}` and BSD `sed r` without a space; the boundary SHALL be `Read(**/.env)` in `permissions.deny` and secrets kept only in `.env`.

#### Scenario: A known bypass
- **WHEN** the agent runs `cat .e{n,}v` or `sh -c 'cat "$1"' _ .env`
- **THEN** the guard lets it through and `docs/hooks.md` lists the form as a known bypass

### Requirement: Secret variable names
A variable SHALL count as secret when one part of its name, split at `_`, digits and a lower-to-upper case change and compared in any case, is `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `WEBHOOK` or `CREDENTIAL`, alone or with a trailing `S`. `guard` SHALL refuse `echo`, `printf` and `printenv` of a secret variable and SHALL pass them for any other variable.

#### Scenario: A word inside a name
- **WHEN** the agent runs `echo $MONKEY_NAME` or `echo $KEYBOARD_LAYOUT`
- **THEN** the command passes

#### Scenario: A secret part
- **WHEN** the agent runs `echo "$OPENAI_API_KEY"`, `echo $db_password`, `echo $apiKey` or `printenv GITHUB_TOKENS`
- **THEN** the command is refused

### Requirement: Deny rules for secret files
`solo-sdd install --hooks` SHALL add to `permissions.deny` of `~/.claude/settings.json` the entry `Read(**/.env)` when absent and record it in `_hooks` only when it added it; `uninstall` SHALL remove only an entry recorded so.

#### Scenario: A round trip
- **WHEN** `install --hooks` and then `uninstall` run on settings that already deny `Read(./secrets/**)`
- **THEN** after install `Read(**/.env)` is there once, after uninstall only `Read(./secrets/**)` is left

#### Scenario: An entry the owner wrote
- **WHEN** the settings already deny `Read(**/.env)` and `install --hooks` and then `uninstall` run
- **THEN** the entry stays after uninstall

### Requirement: Sandbox read deny for secret files
The sandbox read deny for `.env` SHALL be the `Read(**/.env)` entry of `permissions.deny` from Deny rules for secret files. `install --hooks` SHALL write no `sandbox` key and end with a `sandbox read deny:` line: with `sandbox.enabled: true` in `~/.claude/settings.json`, `expected active` on macOS, `not active` on Linux, `unknown` elsewhere; else `off, it needs the sandbox`. `doctor` SHALL print it as a `sandbox read` row, `warn` when the deny does not apply with the sandbox on.

#### Scenario: Sandbox on
- **WHEN** the settings have the sandbox on and `install --hooks` then `uninstall` run on macOS
- **THEN** after install the output says the read deny is expected active and a sandboxed `cat .env` in a Claude Code session fails to read the file, after uninstall the settings are as before

#### Scenario: Sandbox off
- **WHEN** the settings have no sandbox and `install --hooks` runs
- **THEN** no sandbox key is written and the output says the read deny needs the sandbox
