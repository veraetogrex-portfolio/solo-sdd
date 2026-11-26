## MODIFIED Requirements

### Requirement: Archive run behind runners and options
`guard` SHALL recognise `solo-sdd archive <id>` (also `openspec`, `python -m solo_sdd`) for the CLAIM refusal and Review before archive: after a runner (`uv run`, `uvx`, `npx`, `pipx run`, `npm exec`), behind the values of options of the runner, of the wrappers `sudo`, `env`, `caffeinate`, `exec`, `npx` and `time` (also in a short cluster such as `-Hu` and in a subshell) and of Python (`-W`, `-X`), with a joined `-msolo_sdd`, and in a `-c` string after `--`.

#### Scenario: A runner option value named like the program
- **WHEN** the session edited `src/app.py`, ran no `Review:` agent and runs `uvx --from solo-sdd solo-sdd archive add-words`
- **THEN** the command is refused, the reason names `src/app.py`

#### Scenario: A runner that starts Python
- **WHEN** the same session runs `uv run python -m solo_sdd archive add-words`
- **THEN** the command is refused

#### Scenario: Valued options
- **WHEN** the same session runs `python3 -W ignore -m solo_sdd archive add-words`, `python3 -msolo_sdd archive add-words`, `sudo -u root solo-sdd archive add-words` or `env -u X solo-sdd archive add-words`
- **THEN** each is refused

#### Scenario: Valued options of other wrappers
- **WHEN** the same session runs `caffeinate -t 5 solo-sdd archive add-words`, `caffeinate -w 1 …`, `exec -a NAME …`, `npx -p x …`, `time -o /tmp/x …`, `/usr/bin/time -f %e …`, `(sudo -u root solo-sdd archive add-words)`, `(env -u X …)`, `sudo -Hu root …` or `env -iu X …`
- **THEN** each is refused, the reason names `src/app.py`; against a change with a foreign CLAIM each is refused as taken by another agent

#### Scenario: An option value is not the program
- **WHEN** the same session runs `npx -p solo-sdd archive add-words`, `npx --package solo-sdd archive add-words` or `sudo -Hu solo-sdd archive add-words`
- **THEN** each passes: the wrapper's option takes `solo-sdd` as its value, and the program is `archive`; `npx -p solo-sdd solo-sdd archive add-words` is refused, and a runner's own option value stays tried as the program (`uvx --from solo-sdd archive add-words` is refused)

#### Scenario: GNU time's long options
- **WHEN** the same session runs `time --output /tmp/x solo-sdd archive add-words`, `/usr/bin/time --format %e solo-sdd archive add-words` or `time --output=/tmp/x solo-sdd archive add-words`
- **THEN** each is refused, the reason names `src/app.py`; against a change with a foreign CLAIM each is refused as taken by another agent

#### Scenario: End of options before the -c string
- **WHEN** the same session runs `bash -c -- 'solo-sdd archive add-words'`
- **THEN** the command is refused

#### Scenario: Words that stay text
- **WHEN** the same session runs `echo solo-sdd archive add-words` or `uvx --from solo-sdd solo-sdd validate --all`
- **THEN** the command passes

## ADDED Requirements

### Requirement: Archive run in a command string of an option
`guard` SHALL recognise an archive run in the string an option value hands on as a command, split by shell quoting and parsed again like a shell's `-c` string, for the CLAIM refusal and Review before archive: `env -S`/`--split-string` with the words after the string appended, also joined and at the end of a short cluster, and `npx -c`/`--call`, `--call` also joined with `=`.

#### Scenario: env splits the string
- **WHEN** the session edited `src/app.py`, ran no `Review:` agent and runs `env -S 'solo-sdd archive add-words'`, `env --split-string 'solo-sdd archive add-words'`, `env -iS 'solo-sdd archive add-words'`, `env -S 'solo-sdd archive' add-words` or `uv run env -S 'solo-sdd archive add-words'`
- **THEN** each is refused, the reason names `src/app.py`; against a change with a foreign CLAIM each is refused as taken by another agent

#### Scenario: A joined env string
- **WHEN** the same session runs `env -S'solo-sdd archive add-words'` or `env --split-string='solo-sdd archive add-words'`
- **THEN** the archive checks read the run of `add-words`, and each command is refused with the env guard's reason "The command prints the whole environment or a secret": that check runs first and reads a joined `-S` as an option of an `env` with no program

#### Scenario: npx runs the string
- **WHEN** the same session runs `npx -c 'solo-sdd archive add-words'`, `npx --call 'solo-sdd archive add-words'`, `npx --call='solo-sdd archive add-words'` or `sudo -u root npx -c 'bash -c "solo-sdd archive add-words"'`
- **THEN** each is refused, the reason names `src/app.py`; against a change with a foreign CLAIM each is refused as taken by another agent

#### Scenario: A string that runs no archive
- **WHEN** the same session runs `env -S 'solo-sdd validate --all'`, `npx -c 'echo solo-sdd archive add-words'`, `env -u S 'solo-sdd archive add-words'`, `npx -c'solo-sdd archive add-words'` or `echo env -S 'solo-sdd archive add-words'`
- **THEN** each passes: `env -u` takes `S` as its value, so the string is the program word, npm reads no joined `-c…`, and an argument of `echo` is text

#### Scenario: Broken and deep strings
- **WHEN** the archive checks read `env -S 'solo-sdd archive add-words` (an open quote), `env -S`, `npx -c`, `npx --call=`, `eval eval eval env -S 'solo-sdd archive add-words'` or `env -` followed by 20,000 `i` letters and `S 'solo-sdd archive add-words'`
- **THEN** the first five give no archive run and no internal error (past three `eval` levels the parse stops, as `eval eval eval eval solo-sdd archive add-words` does today), and the long cluster gives the run of `add-words` in under a second
