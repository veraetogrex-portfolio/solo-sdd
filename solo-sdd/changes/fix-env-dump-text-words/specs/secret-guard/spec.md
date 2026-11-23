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
- **WHEN** the agent runs `[ -n "$(git status --short)" ] && echo yes; (cd /tmp && env -i HOME=$HOME PATH=/usr/bin:/bin python3 report.py < /dev/null | tail -4)`, `echo "$(date)"; env X=1 python3 -V`, `echo "$(date)"; env -u HOME python3 -V`, `echo "$(date)"; env -C /tmp python3 -V`, `echo "$(date)"; env LC_ALL=C grep "printenv" f` or `echo "$(date)"; env -u HOME grep "printenv" f`
- **THEN** the command passes

#### Scenario: Dumps still refused
- **WHEN** the agent runs `env`, `env | grep TOKEN`, `printenv`, `grep x "$(env)"`, `echo "$(date)"; env -i HOME=$HOME printenv`, `echo "$(date)"; env -u X printenv`, `echo "$(date)"; env X=1 xargs printenv`, `echo "$(date)"; env -C /tmp printenv`, `echo "$(date)"; env X=1 e""nv`, `echo "$(date)"; env p""rintenv`, `echo "$(date)"; env -u HOME /usr/bin/env`, `echo "$(date)"; env -u HOME "env"`, `echo "$(date)"; env -S "X=1 printenv"`, `echo "$(date)"; env -u printenv`, `echo "$(date)"; grep -o "printenv" f | sh`, `echo "$(date)"; grep x f | xargs "printenv"`, `echo "$(date)"; grep "${HOME}env" f`, `echo "$(date)"; env Y="$(env -u X printenv)" sh -c 'echo $Y'`, `echo "$(date)"; rg --pre "printenv" x f`, `echo "$(date)"; rg "--pre=printenv" x f`, `echo "$(date)"; rg --hostname-bin "printenv" x f`, `echo "$(date)"; env A-B=1`, `echo "$(date)"; env -i 'A B=1'`, `echo "$(date)"; { grep -o "printenv" f; } | sh`, `echo "$(date)"; (grep -o "printenv" f) | sh`, `echo "$(date)"; grep -o "printenv" f | tee >(sh)`, `echo "$(date)"; grep -o "printenv" f | python3 -`, `echo "$(date)"; sudo -u grep "env"`, `echo "$(date)"; env X=1 /usr/bin/e[n]v`, `echo "$(date)"; env A.B=1 >/dev/null`, `echo "$(date)"; env A-B=1 2>&1 | head`, `echo "$(date)"; env A.B=1 > /tmp/x`, `echo "$(date)"; env -i 'A B=1' 2>&1`, `echo "$(date)"; grep -o "printenv" f | sudo -u cat sh`, `echo "$(date)"; grep -o "printenv" f | env -u tee sh`, `echo "$(date)"; grep -o "printenv" f | exec -a cat sh`, `echo "$(date)"; grep -o "printenv" f | >cat sh`, `echo "$(date)"; exec -a grep "env"`, `echo "$(date)"; time -o grep "env"` or `echo "$(date)"; caffeinate -t grep "env"`
- **THEN** each command is refused: a program word is a dump word when `DUMP_WORDS` finds one in it with its quotes removed, a word with `=` is an assignment of `env`, a redirection is no word, an option before the program stops the cut, an `env` option outside its table or a glob keeps the `env` counted, and a pipe into a program that is not a text reader (an interpreter included) or a `>(…)` anywhere keeps every search counted

#### Scenario: Other programs' scripts are not text
- **WHEN** the agent runs `echo "$(date)"; sed 's/.*/env/e' f` or `echo "$(date)"; awk 'BEGIN{"env" | getline x; print x}' /dev/null`
- **THEN** each command is refused

#### Scenario: Shell forms the exemption cannot read
- **WHEN** the agent runs `echo ${X:-"a b"}; grep "x env" f`, `echo "$(date)"; grep "env x`, `echo "$(date)"; grep "a\\" ; env ; "x"`, `echo "$(date)"; grep x f # it's`, a newline, `printenv; echo 'y'`, or `echo "$(true "; grep "; env; true "x")"`
- **THEN** each command is refused: a `#`, a form of `UNCUT`, a heredoc or `case` anywhere in the command, an open quote or a trailing backslash leaves the whole command counted, and the inside of `$(…)`, `${…}` and a backquote is read with its own quotes and never cut; `echo "$(date)"; grep "x` passes, as it holds no dump word
