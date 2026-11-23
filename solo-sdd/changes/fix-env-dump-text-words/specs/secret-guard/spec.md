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
