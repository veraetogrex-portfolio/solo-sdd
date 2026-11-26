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

#### Scenario: End of options before the -c string
- **WHEN** the same session runs `bash -c -- 'solo-sdd archive add-words'`
- **THEN** the command is refused

#### Scenario: Words that stay text
- **WHEN** the same session runs `echo solo-sdd archive add-words` or `uvx --from solo-sdd solo-sdd validate --all`
- **THEN** the command passes
