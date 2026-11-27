## MODIFIED Requirements

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

#### Scenario: A long token answered in time
- **WHEN** the agent runs `echo ` followed by 50,000 `$(` with no space, `$a` repeated 100,000 times followed by `; cat .env`, or `git add ` followed by 50,000 `$(`
- **THEN** the secret check (`guard_secrets_bash`) decides each within 2 seconds and the hook's run answers within 8 seconds, never by its 10-second timeout and never naming `errors.log`: the first passes, the second is refused with the `.env` read reason, the third passes

#### Scenario: Names kept by the faster search
- **WHEN** the agent runs `cat x=.env`, `cat (.env)`, `cat $.env`, `cat ${X}/.env`, `cat a/b/.env.local` or `cat .env.example`, each also behind `echo ${X}; ` (not plain), and `git add .ENV` and `git add .env/`
- **THEN** each gets the verdict it gets on main: the `cat` forms refused except `.env.example`, which passes, in both forms; the two `git add` forms as on main
