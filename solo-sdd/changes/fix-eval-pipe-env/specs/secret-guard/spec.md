## MODIFIED Requirements

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
- **WHEN** the agent runs `env -u X printenv`, `env -C /tmp printenv`, `env -P /usr/bin printenv`, `/usr/bin/env -u X printenv`, `timeout 5 env -u X printenv`, `sudo -u root printenv`, `sudo -u root env`, `sudo -u root printenv GITHUB_TOKEN`, `env -u X sh -c env`, `sudo -u root sh -c printenv`, `caffeinate -t 5 printenv`, `caffeinate -w 1 printenv`, `exec -a NAME printenv`, `npx -p x printenv`, `npx --package x printenv`, `time -o /tmp/x printenv` or `/usr/bin/time -f %e printenv`
- **THEN** each command is refused, and `env -u HOME python3 -V`, `env -C /tmp ls`, `env -u X sh -c ls`, `sudo -u root ls`, `caffeinate -t 5 ls`, `npx -p x eslint .`, `time -o /tmp/x ls` and `env -u X printenv HOME` pass

#### Scenario: A dump nested past the parsed depth
- **WHEN** the agent runs `eval eval eval eval env` or `eval eval eval eval printenv`
- **THEN** each command is refused: a text that `eval` or a shell's `-c` string hands on past three levels counts by any dump word in it; `eval eval eval eval ls` and `eval eval eval env X=1 python3 -V` pass, as the third level's program word is still read

#### Scenario: env runs env
- **WHEN** the agent runs `env env`, `env -i env`, `env -u X env`, `env FOO=1 env`, `env env -i`, `/usr/bin/env env`, `env /usr/bin/env`, `sudo env env`, `timeout 5 env env`, `env "env"`, `env -- env`, `env -uX env`, `env --unset=X env`, `printf x | env env`, `env -S env`, `echo "$(date)"; env "$(xargs printenv)"/env ls`, `echo "$(date)"; env $X/env ls` or `echo "$(date)"; env /u*/bin/env ls`
- **THEN** each command is refused with the reason "The command prints the whole environment or a secret", and `env env ls`, `env -i env HOME=/x true`, `env env printenv HOME`, `echo "$(date)"; env env ls` and `echo "$(date)"; env e""nv ls` pass: a nested `env` is read on as `env` only as a literal word, never with a `$`, a backquote or a glob

#### Scenario: eval in a pipe into a shell
- **WHEN** the agent runs `eval echo env | sh`, `eval echo printenv | bash`, `eval 'echo env' | sh`, `eval echo env | tee | sh`, `eval 'echo env; true' | sh`, `eval eval eval eval echo env | sh`, `echo env | eval sh`, `echo env | eval 'true; sh'`, `echo env | eval 'cat | sh'`, `printf env | eval eval sh`, `echo env | eval 'eval true; sh'`, `echo env | eval eval eval eval sh`, `echo env | eval cat | sh`, `echo env | eval tee | sh`, `eval echo env | eval sh` or `echo env | eval cat | eval cat | eval cat | eval cat | sh`
- **THEN** each command is refused with the reason "The command prints the whole environment or a secret": what a pipe into `eval` carries is echoed into the first segment head of its text that reads input: a shell that reads its commands from stdin, `tee`, a bare `cat`, or an `eval` whose text has such a head, an `eval` past three levels counting as one; an `eval` source, so fed, prints what each segment of its text (split at `;`, `&&`, `||`, `&` and a newline) not piped on prints, and past three `eval` levels the dump words of the pipeline before it; `eval echo hi | sh`, `echo ls | eval sh`, `echo ok | eval cat`, `echo env | eval true` and `eval "echo 'env" | sh` (an open quote: `eval` runs nothing) pass
