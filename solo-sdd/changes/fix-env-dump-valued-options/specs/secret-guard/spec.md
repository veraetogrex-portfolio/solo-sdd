## MODIFIED Requirements

### Requirement: Environment dumps refused
As a guard against accidental dumps, not a boundary, `guard` SHALL refuse a Bash command that runs `env` or `printenv` without arguments, `set` without arguments, `export -p` or `declare -p`, alone or in a pipe, and a command that is not plain and holds such a word outside a quoted argument of `grep` or `rg` free of `$(` and a backquote, and outside an `env` at a command position with its options, values, assignments and a program that is no dump word.

#### Scenario: A shell dump
- **WHEN** the agent runs `set | grep -i api` or `export -p`
- **THEN** the command is refused

#### Scenario: A dump word in a search pattern
- **WHEN** the agent runs `grep -n "secret\|printenv\|env |echo \$" skills/debug-profile/SKILL.md` or `grep -n "foo\|env\[" global/sdd_eval.py`
- **THEN** the command passes

#### Scenario: env runs a program next to a substitution
- **WHEN** the agent runs `[ -n "$(git status --short)" ] && echo yes; (cd /tmp && env -i HOME=$HOME PATH=/usr/bin:/bin python3 report.py < /dev/null | tail -4)`, `echo "$(date)"; env X=1 python3 -V`, `echo "$(date)"; env -u HOME python3 -V`, `echo "$(date)"; env -C /tmp python3 -V` or `echo "$(date)"; env LC_ALL=C grep "printenv" f`
- **THEN** the command passes

#### Scenario: Dumps still refused
- **WHEN** the agent runs `env`, `env | grep TOKEN`, `printenv`, `grep x "$(env)"`, `echo "$(date)"; env -i HOME=$HOME printenv`, `echo "$(date)"; env -u X printenv`, `echo "$(date)"; env X=1 xargs printenv` or `echo "$(date)"; env -C /tmp printenv`
- **THEN** each command is refused

#### Scenario: Other programs' scripts are not text
- **WHEN** the agent runs `echo "$(date)"; sed 's/.*/env/e' f` or `echo "$(date)"; awk 'BEGIN{"env" | getline x; print x}' /dev/null`
- **THEN** each command is refused

#### Scenario: A wrapper option with a value
- **WHEN** the agent runs `env -u X printenv`, `env -C /tmp printenv`, `env -P /usr/bin printenv`, `/usr/bin/env -u X printenv`, `timeout 5 env -u X printenv`, `sudo -u root printenv`, `sudo -u root env`, `sudo -u root printenv GITHUB_TOKEN`, `env -u X sh -c env`, `sudo -u root sh -c printenv`, `caffeinate -t 5 printenv`, `exec -a NAME printenv` or `npx -p x printenv`
- **THEN** each command is refused, and `env -u HOME python3 -V`, `env -C /tmp ls`, `env -u X sh -c ls`, `sudo -u root ls`, `caffeinate -t 5 ls`, `npx -p x eslint .` and `env -u X printenv HOME` pass

### Requirement: Known bypasses of the Bash guard
`docs/hooks.md` SHALL name as outside the Bash guard: brace expansion, `sh -c` with the file as a positional argument, process substitution with a quoted `)`, a heredoc marker line with an open quote, `${X:-env}`, BSD `sed r` without a space, an interpreter's script that runs or reads the environment and, in a plain command, a dump word another program runs from its argument (`xargs`, sed `e`, `env -S`); the boundary SHALL be `Read(**/.env)` in `permissions.deny` and secrets kept only in `.env`.

#### Scenario: A known bypass
- **WHEN** the agent runs `cat .e{n,}v` or `sh -c 'cat "$1"' _ .env`
- **THEN** the guard lets it through and `docs/hooks.md` lists the form as a known bypass

#### Scenario: An interpreter prints the environment
- **WHEN** the agent runs `awk 'BEGIN{system("env")}' /dev/null`, `python3 -c 'import os; print(os.environ)'`, `xargs printenv`, `sed 's/.*/env/e' f` or `env -S env`
- **THEN** the guard lets each through and `docs/hooks.md` lists an interpreter's script that runs or reads the environment and a dump word run by another program from its arguments as known bypasses
