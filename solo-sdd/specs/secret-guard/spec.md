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
As a guard against accidental dumps, not a boundary, `guard` SHALL refuse a Bash command that runs `env` or `printenv` without arguments, `set` without arguments, `export -p` or `declare -p`, alone or in a pipe, and a command that is not plain and holds such a word outside a quoted argument of `grep` or `rg` free of `$(` and a backquote, and outside an `env` at a command position with its options, values, assignments, a literal nested `env` and a program that is no dump word.

#### Scenario: A shell dump
- **WHEN** the agent runs `set | grep -i api` or `export -p`
- **THEN** the command is refused

#### Scenario: A dump word in a search pattern
- **WHEN** the agent runs `grep -n "secret\|printenv\|env |echo \$" skills/debug-profile/SKILL.md` or `grep -n "foo\|env\[" global/sdd_eval.py`
- **THEN** the command passes

#### Scenario: env runs a program next to a substitution
- **WHEN** the agent runs `[ -n "$(git status --short)" ] && echo yes; (cd /tmp && env -i HOME=$HOME PATH=/usr/bin:/bin python3 report.py < /dev/null | tail -4)`, `echo "$(date)"; env X=1 python3 -V`, `echo "$(date)"; env -u HOME python3 -V`, `echo "$(date)"; env -C /tmp python3 -V`, `echo "$(date)"; env LC_ALL=C grep "printenv" f` or `echo "$(date)"; env -u HOME grep "printenv" f`
- **THEN** the command passes

#### Scenario: Dumps still refused
- **WHEN** the agent runs `env`, `env | grep TOKEN`, `printenv`, `grep x "$(env)"`, `echo "$(date)"; env -i HOME=$HOME printenv`, `echo "$(date)"; env -u X printenv`, `echo "$(date)"; env X=1 xargs printenv`, `echo "$(date)"; env -C /tmp printenv`, `echo "$(date)"; env X=1 e""nv`, `echo "$(date)"; env p""rintenv`, `echo "$(date)"; env -u HOME /usr/bin/env`, `echo "$(date)"; env -u HOME "env"`, `echo "$(date)"; env -S "X=1 printenv"`, `echo "$(date)"; env -u printenv`, `echo "$(date)"; grep -o "printenv" f | sh`, `echo "$(date)"; grep x f | xargs "printenv"`, `echo "$(date)"; grep "${HOME}env" f`, `echo "$(date)"; env Y="$(env -u X printenv)" sh -c 'echo $Y'`, `echo "$(date)"; rg --pre "printenv" x f`, `echo "$(date)"; rg "--pre=printenv" x f`, `echo "$(date)"; rg --hostname-bin "printenv" x f`, `echo "$(date)"; env A-B=1`, `echo "$(date)"; env -i 'A B=1'`, `echo "$(date)"; { grep -o "printenv" f; } | sh`, `echo "$(date)"; (grep -o "printenv" f) | sh`, `echo "$(date)"; grep -o "printenv" f | tee >(sh)`, `echo "$(date)"; grep -o "printenv" f | python3 -`, `echo "$(date)"; sudo -u grep "env"`, `echo "$(date)"; env X=1 /usr/bin/e[n]v`, `echo "$(date)"; env A.B=1 >/dev/null`, `echo "$(date)"; env A-B=1 2>&1 | head`, `echo "$(date)"; env A.B=1 > /tmp/x`, `echo "$(date)"; env -i 'A B=1' 2>&1`, `echo "$(date)"; grep -o "printenv" f | sudo -u cat sh`, `echo "$(date)"; grep -o "printenv" f | env -u tee sh`, `echo "$(date)"; grep -o "printenv" f | exec -a cat sh`, `echo "$(date)"; grep -o "printenv" f | >cat sh`, `echo "$(date)"; exec -a grep "env"`, `echo "$(date)"; time -o grep "env"`, `echo "$(date)"; caffeinate -t grep "env"`, `echo "$(date)"; env A.B=1 >& 2`, `echo "$(date)"; env A.B=1 2>& 1`, `echo "$(date)"; env A.B=1 >& /tmp/x`, `echo "$(date)"; env A.B=1 <& 0`, `echo "$(date)"; env A.B=1 {fd}>/tmp/x`, `echo "$(date)"; env A.B=1 {fd}>&1`, `echo "$(date)"; env >! /dev/stdout`, `echo "$(date)"; env A.B=1 >! /tmp/x`, `echo "$(date)"; env A.B=1 >>! /dev/stdout`, `echo "$(date)"; env A.B=1 >&! /tmp/x`, `echo "$(date)"; env A.B=1 &>! /tmp/x`, `echo "$(date)"; >! grep "printenv"`, `echo "$(date)"; >| grep "printenv"`, `echo "$(date)"; A=1 &>| grep "printenv"`, `echo "$(date)"; 2>| rg "printenv"`, `echo "$(date)"; >&| grep "printenv"`, `echo "$(date)"; grep -o "printenv" f \>|sh`, `echo "$(date)"; grep -o "printenv" f \>| sh`, `echo "$(date)"; grep -o "printenv" f x\>|sh`, `echo "$(date)"; grep -o "printenv" f \>|& sh`, `echo "$(date)"; rg -o "printenv" f \>|sh`, `echo "$(date)"; env LC_ALL=C grep -o "printenv" f \>|sh`, `echo "$(date)"; grep -o x f \>& "printenv"` or `echo "$(date)"; grep -o x f \<& "printenv"`
- **THEN** each command is refused: a program word is a dump word when `DUMP_WORDS` finds one in it with its quotes removed, a word with `=` is an assignment of `env`, a redirection (its fd, `{name}` fd, `>&`/`<&` operator and target) is no word, a redirection before the program word stops the cut of its command, an escaped `\>` or `\<` is no redirection, an option before the program stops the cut, an `env` option outside its table or a glob keeps the `env` counted, and a pipe into a program that is not a text reader (an interpreter included) or a `>(…)` anywhere keeps every search counted

#### Scenario: Other programs' scripts are not text
- **WHEN** the agent runs `echo "$(date)"; sed 's/.*/env/e' f` or `echo "$(date)"; awk 'BEGIN{"env" | getline x; print x}' /dev/null`
- **THEN** each command is refused

#### Scenario: Shell forms the exemption cannot read
- **WHEN** the agent runs `echo ${X:-"a b"}; grep "x env" f`, `echo "$(date)"; grep "env x`, `echo "$(date)"; grep "a\\" ; env ; "x"`, `echo "$(date)"; grep x f # it's`, a newline, `printenv; echo 'y'`, or `echo "$(true "; grep "; env; true "x")"`
- **THEN** each command is refused: a `#`, a form of `UNCUT`, a heredoc or `case` anywhere in the command, an open quote or a trailing backslash leaves the whole command counted, and the inside of `$(…)`, `${…}` and a backquote is read with its own quotes and never cut; `echo "$(date)"; grep "x` passes, as it holds no dump word

#### Scenario: A wrapper option with a value
- **WHEN** the agent runs `env -u X printenv`, `env -C /tmp printenv`, `env -P /usr/bin printenv`, `/usr/bin/env -u X printenv`, `timeout 5 env -u X printenv`, `sudo -u root printenv`, `sudo -u root env`, `sudo -u root printenv GITHUB_TOKEN`, `env -u X sh -c env`, `sudo -u root sh -c printenv`, `caffeinate -t 5 printenv`, `caffeinate -w 1 printenv`, `exec -a NAME printenv`, `npx -p x printenv`, `npx --package x printenv`, `time -o /tmp/x printenv`, `/usr/bin/time -f %e printenv`, `time --output /tmp/x printenv` or `/usr/bin/time --format %e printenv`
- **THEN** each command is refused, and `env -u HOME python3 -V`, `env -C /tmp ls`, `env -u X sh -c ls`, `sudo -u root ls`, `caffeinate -t 5 ls`, `npx -p x eslint .`, `time -o /tmp/x ls`, `time --output /tmp/x ls` and `env -u X printenv HOME` pass

#### Scenario: A dump nested past the parsed depth
- **WHEN** the agent runs `eval eval eval eval env` or `eval eval eval eval printenv`
- **THEN** each command is refused: a text that `eval` or a shell's `-c` string hands on past three levels counts by any dump word in it; `eval eval eval eval ls` and `eval eval eval env X=1 python3 -V` pass, as the third level's program word is still read

#### Scenario: env runs env
- **WHEN** the agent runs `env env`, `env -i env`, `env -u X env`, `env FOO=1 env`, `env env -i`, `/usr/bin/env env`, `env /usr/bin/env`, `sudo env env`, `timeout 5 env env`, `env "env"`, `env -- env`, `env -uX env`, `env --unset=X env`, `printf x | env env`, `env -S env`, `echo "$(date)"; env "$(xargs printenv)"/env ls`, `echo "$(date)"; env $X/env ls` or `echo "$(date)"; env /u*/bin/env ls`
- **THEN** each command is refused with the reason "The command prints the whole environment or a secret", and `env env ls`, `env -i env HOME=/x true`, `env env printenv HOME`, `echo "$(date)"; env env ls` and `echo "$(date)"; env e""nv ls` pass: a nested `env` is read on as `env` only as a literal word, never with a `$`, a backquote or a glob

#### Scenario: eval in a pipe into a shell
- **WHEN** the agent runs `eval echo env | sh`, `eval echo printenv | bash`, `eval 'echo env' | sh`, `eval echo env | tee | sh`, `eval 'echo env; true' | sh`, `eval eval eval eval echo env | sh`, `echo env | eval sh`, `echo env | eval 'true; sh'`, `echo env | eval 'cat | sh'`, `printf env | eval eval sh`, `echo env | eval 'eval true; sh'`, `echo env | eval eval eval eval sh`, `echo env | eval cat | sh`, `echo env | eval tee | sh`, `eval echo env | eval sh` or `echo env | eval cat | eval cat | eval cat | eval cat | sh`
- **THEN** each command is refused with the reason "The command prints the whole environment or a secret": what a pipe into `eval` carries is echoed into the first segment head of its text that reads input: a shell that reads its commands from stdin, `tee`, a bare `cat`, or an `eval` whose text has such a head, an `eval` past three levels counting as one; an `eval` source, so fed, prints what each segment of its text (split at `;`, `&&`, `||`, `&` and a newline) not piped on prints, and past three `eval` levels the dump words of the pipeline up to it; `eval echo hi | sh`, `echo ls | eval sh`, `echo ok | eval cat`, `echo env | eval true` and `eval "echo 'env" | sh` (an open quote: `eval` runs nothing) pass

### Requirement: Known bypasses of the Bash guard
`docs/hooks.md` SHALL name as outside the Bash guard: brace expansion, `sh -c` with the file as a positional argument, process substitution with a quoted `)`, a heredoc marker line with an open quote, `${X:-env}`, BSD `sed r` unspaced and, in a plain command, an interpreter's script that runs or reads the environment or a dump word another program runs from its argument (`xargs`, sed `e`, a spaced `env -S`); the boundary is `Read(**/.env)` in `permissions.deny` and secrets kept only in `.env`.

#### Scenario: A known bypass
- **WHEN** the agent runs `cat .e{n,}v` or `sh -c 'cat "$1"' _ .env`
- **THEN** the guard lets it through and `docs/hooks.md` lists the form as a known bypass

#### Scenario: An interpreter prints the environment
- **WHEN** the agent runs `awk 'BEGIN{system("env")}' /dev/null`, `python3 -c 'import os; print(os.environ)'`, `xargs printenv`, `sed 's/.*/env/e' f` or `env -S 'A=1 env'`
- **THEN** the guard lets each through and `docs/hooks.md` lists an interpreter's script that runs or reads the environment and a dump word run by another program from its arguments as known bypasses

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

### Requirement: Secret checks fail closed
When `guard_env_write`, `guard_env_read` or `guard_secrets_bash` raises, or the preparation of its input in `cmd_guard` raises (a path or command text built for it), `guard` SHALL answer `deny` with a reason naming the check and `~/.claude/hook-state/errors.log`, and SHALL write the error there as before. An exception in any other check SHALL keep letting the call through.

#### Scenario: A raising Bash secret check
- **WHEN** `guard_secrets_bash` raises while the agent runs `cat .env.local`
- **THEN** the answer is `deny`, its reason names `guard_secrets_bash` and `errors.log`, and `errors.log` holds the error

#### Scenario: A raising read check
- **WHEN** `guard_env_read` raises on a `Read` of `README.md`
- **THEN** the answer is `deny` naming `guard_env_read`

#### Scenario: A raising Write check
- **WHEN** `guard_env_write` raises on a `Write` of `notes.md`
- **THEN** the answer is `deny` naming `guard_env_write`

#### Scenario: Preparation raises
- **WHEN** `command_text` raises while `guard` prepares a Bash command for `guard_secrets_bash`
- **THEN** the answer is `deny` naming `guard_secrets_bash`

#### Scenario: Another check raises
- **WHEN** `guard_models_agent` raises on an `Agent` call
- **THEN** the call passes and `errors.log` holds the error

### Requirement: Unreadable guard input refused
`guard` SHALL answer `deny` naming `guard input` and `~/.claude/hook-state/errors.log`, and write the error there, when stdin is not a JSON object, or a call of Bash, Read, Grep, Write, Edit, MultiEdit or NotebookEdit has a `tool_input` that is not an object or a `cwd` that is not a string. A present `command`, `file_path` or `notebook_path` that is not a string SHALL deny naming its secret check instead. Other tools pass as before.

#### Scenario: Stdin is not a JSON object
- **WHEN** `guard` gets `[1]`, an empty stdin or text that is not JSON
- **THEN** the answer is `deny` naming `guard input`, and `errors.log` holds the error

#### Scenario: A field of the wrong type
- **WHEN** `guard` gets a `Read` with `cwd` `5`, `0` or `[]`, a Read, Bash or Write call whose `tool_input` is `["README.md"]`, `0` or `[]`, a Bash call with `command` `5`, `0`, `[]` or `false`, a `Write` with `file_path` `5` or `0`, a `Read` with `file_path` `5` or `["a/.env"]`, or a `NotebookEdit` with `notebook_path` `["a.ipynb"]`
- **THEN** the answer is `deny` naming `guard input` for the `cwd` and `tool_input` cases, `guard_secrets_bash` for `command` and `guard_env_write` for the Write `file_path` and `notebook_path`, and `guard_env_read` for the Read `file_path`

#### Scenario: Absent fields and other tools
- **WHEN** `guard` gets a `Read` with `cwd` null, a Bash call with `command` null, a `Write` with `tool_input` null, or an `AskUserQuestion` with `tool_input` `0` and `cwd` `5`
- **THEN** no answer comes

#### Scenario: Hostile command text
- **WHEN** `guard` gets a Bash command with unbalanced quotes, an unterminated heredoc, nested `$(` and backquotes (1,000 levels of `$(` at most), or 100,000 characters of `\"` pairs or of `a |` inside one quoted `grep` pattern, none naming a secret
- **THEN** no answer comes, `errors.log` stays empty, and each call returns within 5 seconds
